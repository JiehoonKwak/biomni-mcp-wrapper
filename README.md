# Biomni MCP Server "Wrapper"

Simple MCP server that exposes biomedical AI tools to Claude Code with configurable tool selection (for personal usage)

**Credits**: All rights and original work belong to [https://github.com/snap-stanford/Biomni](https://github.com/snap-stanford/Biomni). This is a personal wrapper for MCP integration.

## Quick Setup

```bash
# 1. Configure API key
cp .env.template .env

# 2. Test the server
./startup.sh

# 3. Add to Claude Code
claude mcp add biomni -- ./startup.sh
```

## Tool Configuration

Switch between configurations instantly:

```bash
export BIOMNI_TOOLS_CONFIG=tools_config_complete.json && ./startup.sh
```

## Adding Tools

Edit `tools_config.json` to add/remove tools:

```json
{
  "selected_tools": {
    "biomni.tool.pharmacology": [
      "run_diffdock_with_smiles",
      "predict_admet_properties"
    ]
  }
}
```

## Environment Setup

Create new environment from scratch:

```bash
# Using micromamba
micromamba env create -f environment.yml
```
