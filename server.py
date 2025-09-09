#!/usr/bin/env python3
"""
Biomni MCP Server - Direct Tool Exposure

Exposes selected Biomni tools directly to Claude Code without agent wrapper.
Claude Code acts as the brain, Biomni provides the computational tools.
"""

import os
import sys
import importlib
import json
from typing import Any, Dict, List
from dotenv import load_dotenv

# Use the biomni_e1 environment directly  
sys.path.insert(0, '/Users/jiehoonk/micromamba/envs/biomni_e1/lib/python3.11/site-packages')

try:
    from mcp.server.fastmcp import FastMCP
    from biomni.utils import read_module2api
    print("✓ Successfully imported FastMCP and Biomni utils")
except ImportError as e:
    print(f"✗ Error importing dependencies: {e}")
    print("Make sure the biomni_e1 environment is properly set up")
    sys.exit(1)

# Load configuration
load_dotenv()

def load_tools_config():
    """Load tool selection from configuration file."""
    config_file = os.getenv("BIOMNI_TOOLS_CONFIG", "tools_config.json")
    
    print(f"🔍 Loading tool configuration from: {config_file}")
    
    # Check if config file exists
    if not os.path.exists(config_file):
        print(f"⚠️  Configuration file {config_file} not found")
        print(f"   Using minimal default configuration")
        return {
            "biomni.tool.support_tools": [
                "run_python_repl",
                "read_function_source_code"
            ]
        }
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            selected_tools = config.get('selected_tools', {})
            config_info = config.get('config_info', {})
            
            # Print detailed configuration summary
            total_tools = sum(len(tools) for tools in selected_tools.values())
            print(f"📋 Successfully loaded configuration:")
            print(f"   • File: {config_file}")
            print(f"   • Modules configured: {len(selected_tools)}")
            print(f"   • Total tools selected: {total_tools}")
            
            if config_info:
                print(f"   • Config info: {config_info.get('description', 'N/A')}")
                print(f"   • Last updated: {config_info.get('last_updated', 'N/A')}")
                if 'success_rate' in config_info:
                    print(f"   • Expected success rate: {config_info['success_rate']}")
            
            # Show module breakdown
            print(f"   • Module breakdown:")
            for module_name, tool_list in list(selected_tools.items())[:5]:  # Show first 5
                print(f"     - {module_name}: {len(tool_list)} tools")
            if len(selected_tools) > 5:
                remaining = len(selected_tools) - 5
                print(f"     - ... and {remaining} more modules")
            
            return selected_tools
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error in {config_file}:")
        print(f"   Line {e.lineno}, Column {e.colno}: {e.msg}")
        print(f"   Using minimal default configuration")
        return {
            "biomni.tool.support_tools": [
                "run_python_repl",
                "read_function_source_code"
            ]
        }
    except Exception as e:
        print(f"❌ Error loading configuration file {config_file}: {e}")
        import traceback
        print(f"   Detailed error: {traceback.format_exc()[:200]}...")
        print(f"   Using minimal default configuration")
        return {
            "biomni.tool.support_tools": [
                "run_python_repl",
                "read_function_source_code"
            ]
        }

# Load tool selection from configuration file
SELECTED_TOOLS = load_tools_config()

# Data path for tools that need it
BIOMNI_DATA_PATH = os.getenv("BIOMNI_DATA_PATH", "/Users/jiehoonk/DevHub/datascience/Biomni/data")

# Initialize MCP server
mcp = FastMCP("Biomni Tools")

def create_dynamic_mcp_tool(tool_name: str, tool_func: Any, tool_info: Dict):
    """Create a dynamic function with proper FastMCP signature and parameter handling."""
    
    import inspect
    from typing import Annotated
    
    # Build dynamic function parameters from Biomni tool metadata
    required_params = tool_info.get('required_parameters', [])
    optional_params = tool_info.get('optional_parameters', [])
    
    # Create parameter definitions for the dynamic function
    param_definitions = []
    param_names = []
    default_values = {}
    type_annotations = {}
    
    # Process required parameters
    for param in required_params:
        param_name = param['name']
        param_type = param['type']
        param_desc = param.get('description', '')
        
        param_names.append(param_name)
        
        # Map Biomni types to Python types with annotations
        if param_type == 'str':
            type_annotations[param_name] = Annotated[str, param_desc] if param_desc else str
        elif param_type == 'int':
            type_annotations[param_name] = Annotated[int, param_desc] if param_desc else int
        elif param_type == 'float':
            type_annotations[param_name] = Annotated[float, param_desc] if param_desc else float
        elif param_type == 'bool':
            type_annotations[param_name] = Annotated[bool, param_desc] if param_desc else bool
        else:
            # Default to string for complex types
            type_annotations[param_name] = Annotated[str, param_desc] if param_desc else str
        
        param_definitions.append(param_name)
    
    # Process optional parameters
    for param in optional_params:
        param_name = param['name']
        param_type = param['type']
        param_desc = param.get('description', '')
        param_default = param.get('default')
        
        param_names.append(param_name)
        default_values[param_name] = param_default
        
        # Map types with optional syntax
        if param_type == 'str':
            base_type = Annotated[str, param_desc] if param_desc else str
            type_annotations[param_name] = base_type | None if param_default is None else base_type
        elif param_type == 'int':
            base_type = Annotated[int, param_desc] if param_desc else int
            type_annotations[param_name] = base_type | None if param_default is None else base_type
        elif param_type == 'float':
            base_type = Annotated[float, param_desc] if param_desc else float
            type_annotations[param_name] = base_type | None if param_default is None else base_type
        elif param_type == 'bool':
            base_type = Annotated[bool, param_desc] if param_desc else bool
            type_annotations[param_name] = base_type
        else:
            base_type = Annotated[str, param_desc] if param_desc else str
            type_annotations[param_name] = base_type | None if param_default is None else base_type
        
        # Create parameter definition with default
        if param_default is not None:
            param_definitions.append(f"{param_name}={repr(param_default)}")
        else:
            param_definitions.append(f"{param_name}=None")
    
    # Create the dynamic function code
    func_code = f'''def {tool_name}({', '.join(param_definitions)}):
    """{tool_info.get('description', f'Execute {tool_name}')}"""
    return _execute_tool({repr(tool_name)}, locals())
'''
    
    # Create execution function
    def _execute_tool(name: str, params: dict):
        try:
            # Get the original function signature
            original_sig = inspect.signature(tool_func)
            
            # Prepare parameters for the original function
            call_params = {}
            
            # Add required/optional parameters that are not None
            for param_name in param_names:
                if param_name in params and params[param_name] is not None:
                    call_params[param_name] = params[param_name]
            
            # Add data_path if the original function expects it
            if 'data_path' in original_sig.parameters and 'data_path' not in call_params:
                call_params['data_path'] = f"{BIOMNI_DATA_PATH}/biomni_data/data_lake"
            
            # Execute the original tool function
            result = tool_func(**call_params)
            
            # Format result for MCP
            if isinstance(result, str):
                return result
            elif isinstance(result, (dict, list)):
                import json
                return json.dumps(result, indent=2, ensure_ascii=False)
            else:
                return str(result)
                
        except Exception as e:
            import traceback
            error_msg = f"❌ Error executing {name}: {str(e)}"
            print(f"Tool execution error: {error_msg}")
            print(f"Traceback: {traceback.format_exc()}")
            return error_msg
    
    # Execute the dynamic function creation
    namespace = {'_execute_tool': _execute_tool}
    exec(func_code, namespace)
    
    # Get the created function and add type annotations
    dynamic_func = namespace[tool_name]
    dynamic_func.__annotations__ = type_annotations
    dynamic_func.__annotations__['return'] = str  # All tools return strings
    
    return dynamic_func

def register_selected_tools():
    """Register selected Biomni tools with the MCP server."""
    
    # Get all available tools from Biomni
    try:
        module2api = read_module2api()
        print(f"📚 Found {len(module2api)} available modules in Biomni")
        print(f"   Available modules: {list(module2api.keys())[:5]}{'...' if len(module2api) > 5 else ''}")
    except Exception as e:
        print(f"❌ Failed to read module2api: {e}")
        import traceback
        print(f"   Detailed error: {traceback.format_exc()}")
        return
    
    registered_count = 0
    failed_count = 0
    module_stats = {}
    
    print(f"\n🔄 Processing {len(SELECTED_TOOLS)} configured modules...")
    
    # Register tools from selected modules
    for module_name, selected_tool_names in SELECTED_TOOLS.items():
        print(f"\n📦 Processing module: {module_name}")
        print(f"   Selected tools: {len(selected_tool_names)} ({selected_tool_names[:3]}{'...' if len(selected_tool_names) > 3 else ''})")
        
        if module_name not in module2api:
            print(f"⚠️  Module {module_name} not found in Biomni module registry")
            module_stats[module_name] = {'found': False, 'registered': 0, 'failed': 0}
            continue
        
        module_tools = module2api[module_name]
        available_tool_names = [t['name'] for t in module_tools]
        print(f"   Available tools in module: {len(available_tool_names)}")
        
        module_registered = 0
        module_failed = 0
        
        for tool_info in module_tools:
            tool_name = tool_info['name']
            
            # Skip tools not in our selection
            if tool_name not in selected_tool_names:
                continue
                
            try:
                print(f"   🔄 Registering {tool_name}...", end=" ")
                
                # Import the module and get the function
                module = importlib.import_module(module_name)
                tool_func = getattr(module, tool_name)
                
                # Validate function signature
                import inspect
                sig = inspect.signature(tool_func)
                print(f"[params: {len(sig.parameters)}]", end=" ")
                
                # Create dynamic MCP tool function
                mcp_tool_func = create_dynamic_mcp_tool(tool_name, tool_func, tool_info)
                
                # Register with MCP server 
                mcp.tool(name=tool_name)(mcp_tool_func)
                
                print(f"✅")
                registered_count += 1
                module_registered += 1
                
            except ImportError as e:
                print(f"❌ Import failed: {e}")
                failed_count += 1
                module_failed += 1
            except AttributeError as e:
                print(f"❌ Function not found: {e}")
                failed_count += 1
                module_failed += 1
            except Exception as e:
                print(f"❌ Registration failed: {e}")
                print(f"   Error details: {type(e).__name__}")
                failed_count += 1
                module_failed += 1
        
        module_stats[module_name] = {
            'found': True,
            'registered': module_registered, 
            'failed': module_failed,
            'selected': len(selected_tool_names),
            'available': len(available_tool_names)
        }
    
    print(f"\n📊 Final Registration Summary:")
    print(f"  • Total Registered: {registered_count} tools")
    print(f"  • Total Failed: {failed_count} tools")
    print(f"  • Success Rate: {registered_count/(registered_count+failed_count)*100:.1f}%" if (registered_count+failed_count) > 0 else "  • Success Rate: N/A")
    
    print(f"\n📈 Module Breakdown:")
    for module_name, stats in module_stats.items():
        if stats['found']:
            print(f"  • {module_name}: {stats['registered']}/{stats['selected']} registered, {stats['failed']} failed")
        else:
            print(f"  • {module_name}: NOT FOUND in Biomni registry")

def main():
    """Main entry point for the Biomni MCP server."""
    
    print("=" * 60)
    print("🧬 Biomni MCP Server - Direct Tool Exposure")
    print("=" * 60)
    print(f"📁 Data path: {BIOMNI_DATA_PATH}")
    print(f"🎯 Architecture: Claude Code (brain) → MCP → Biomni Tools")
    print(f"🛠️  Selected modules: {len(SELECTED_TOOLS)}")
    print("=" * 60)
    
    # Register selected tools
    print("🔄 Registering selected tools...")
    register_selected_tools()
    
    try:
        print("\n🚀 Starting MCP server with stdio transport...")
        print("   Claude Code can now use individual Biomni tools directly!")
        print("   Press Ctrl+C to stop")
        print("")
        
        # Run the server
        mcp.run(transport="stdio")
        
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        if "--debug" in sys.argv:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()