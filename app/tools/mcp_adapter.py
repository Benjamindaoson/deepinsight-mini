"""Optional local stdio JSON-RPC adapter over the exact native registry.

Run: .venv/Scripts/python.exe -m app.tools.mcp_adapter
Read-only permissions by default. No network listener or second business layer.
"""

import json
import sys
from app.database import Store
from .registry import registry, execute


def handle(store, request):
    identity = request.get("id")
    method = request.get("method")
    if identity is None:
        return None
    if method == "initialize":
        result = dict(
            protocolVersion="2025-06-18",
            capabilities=dict(tools={}),
            serverInfo=dict(name="deepinsight-mini-tools", version="0.2.0"),
        )
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = dict(
            tools=[
                dict(
                    name=t.name,
                    description=t.description,
                    inputSchema=t.input_schema.model_json_schema(),
                    outputSchema=t.output_schema.model_json_schema(),
                )
                for t in registry().values()
            ]
        )
    elif method == "tools/call":
        params = request.get("params") or {}
        output = execute(store, params.get("name"), params.get("arguments", {})).model_dump()
        result = dict(
            content=[dict(type="text", text=json.dumps(output))],
            structuredContent=output,
            isError=output["status"] == "ERROR",
        )
    else:
        return dict(jsonrpc="2.0", id=identity, error=dict(code=-32601, message="Method not found"))
    return dict(jsonrpc="2.0", id=identity, result=result)


def main():
    store = Store()
    for line in sys.stdin:
        try:
            if len(line.encode()) > 65536:
                raise ValueError("Request too large")
            result = handle(store, json.loads(line))
        except (ValueError, TypeError, AttributeError):
            result = dict(jsonrpc="2.0", id=None, error=dict(code=-32700, message="Invalid request"))
        if result is not None:
            print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
