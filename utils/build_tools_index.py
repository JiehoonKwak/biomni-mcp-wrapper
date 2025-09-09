#!/usr/bin/env python
"""Aggregate all tool descriptions into a single JSON file (tools_index.json).

Minimal usage:
  python utils/build_tools_index.py

Output structure:
{
  "generated_at": "ISO8601",
  "tools": {
      "tool_name": {
          "module": "genomics",
          "description": "...",
          "required_parameters": [...],
          "optional_parameters": [...]
      },
      ...
  }
}
"""
from __future__ import annotations
import ast, json, pathlib, datetime

DESC_DIR = pathlib.Path("tool_description")
OUTPUT = pathlib.Path("tools_index.json")


def extract(py_file: pathlib.Path):
    text = py_file.read_text()
    module = ast.parse(text, filename=str(py_file))
    for node in module.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "description" for t in node.targets):
                return ast.literal_eval(node.value)
    return []


def main():
    tools = {}
    for py_file in sorted(DESC_DIR.glob("*.py")):
        module_name = py_file.stem
        entries = extract(py_file)
        for entry in entries:
            name = entry.get("name")
            if not name:
                continue
            tools[name] = {
                "module": module_name,
                "description": entry.get("description"),
                "required_parameters": entry.get("required_parameters", []) or [],
                "optional_parameters": entry.get("optional_parameters", []) or [],
            }
    payload = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "tool_count": len(tools),
        "tools": tools,
        "schema_version": 1,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {OUTPUT} with {len(tools)} tools.")


if __name__ == "__main__":
    main()
