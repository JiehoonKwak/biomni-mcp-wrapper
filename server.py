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
    
    # Check if config file exists
    if not os.path.exists(config_file):
        print(f"⚠️  Configuration file {config_file} not found, using minimal default")
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
            
            # Print configuration summary
            total_tools = sum(len(tools) for tools in selected_tools.values())
            print(f"📋 Loaded configuration from {config_file}")
            print(f"   Modules: {len(selected_tools)}")
            print(f"   Tools: {total_tools}")
            
            return selected_tools
            
    except Exception as e:
        print(f"❌ Error loading configuration file {config_file}: {e}")
        print("   Using minimal default configuration")
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

def create_tool_wrapper(tool_name: str, tool_func: Any, tool_info: Dict) -> Any:
    """Create an MCP tool wrapper for a Biomni function."""
    
    def tool_wrapper(*args, **kwargs) -> str:
        try:
            # Add data_path parameter if the function expects it
            import inspect
            sig = inspect.signature(tool_func)
            if 'data_path' in sig.parameters and 'data_path' not in kwargs:
                kwargs['data_path'] = f"{BIOMNI_DATA_PATH}/biomni_data/data_lake"
            
            # Execute the tool directly
            result = tool_func(*args, **kwargs)
            
            # Format result for MCP
            if isinstance(result, str):
                return result
            elif isinstance(result, (dict, list)):
                import json
                return json.dumps(result, indent=2, ensure_ascii=False)
            else:
                return str(result)
                
        except Exception as e:
            return f"❌ Error executing {tool_name}: {str(e)}"
    
    # Set function metadata for MCP
    tool_wrapper.__name__ = tool_name
    tool_wrapper.__doc__ = tool_info.get('description', f'Execute {tool_name}')
    
    return tool_wrapper

def register_selected_tools():
    """Register selected Biomni tools with the MCP server."""
    
    # Get all available tools from Biomni
    try:
        module2api = read_module2api()
        print(f"📚 Found {len(module2api)} available modules")
    except Exception as e:
        print(f"❌ Failed to read module2api: {e}")
        return
    
    registered_count = 0
    failed_count = 0
    
    # Register tools from selected modules
    for module_name, selected_tool_names in SELECTED_TOOLS.items():
        if module_name not in module2api:
            print(f"⚠️  Module {module_name} not found in Biomni")
            continue
            
        module_tools = module2api[module_name]
        
        for tool_info in module_tools:
            tool_name = tool_info['name']
            
            # Skip tools not in our selection
            if tool_name not in selected_tool_names:
                continue
                
            try:
                # Import the module and get the function
                module = importlib.import_module(module_name)
                tool_func = getattr(module, tool_name)
                
                # Create MCP tool wrapper
                wrapper = create_tool_wrapper(tool_name, tool_func, tool_info)
                
                # Register with MCP server
                mcp.tool()(wrapper)
                
                print(f"✅ Registered: {tool_name}")
                registered_count += 1
                
            except Exception as e:
                print(f"❌ Failed to register {tool_name}: {e}")
                failed_count += 1
    
    print(f"\n📊 Registration Summary:")
    print(f"  • Registered: {registered_count} tools")
    print(f"  • Failed: {failed_count} tools")

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