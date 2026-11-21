"""MCP server over stdio (JSON-RPC 2.0) for muse-cmc-agent.

Standard library only. Speaks the MCP handshake every MCP client
expects:

  initialize       -> protocolVersion / capabilities / serverInfo
  notifications/initialized, ping -> no response / empty result
  tools/list       -> the 9 tools in cmc_agent.tools.TOOLS
  tools/call       -> runs one tool against the live CMC API and
                      returns the formatted text + the raw JSON

Run:  python3 -m cmc_agent.server
(or via the MCP config snippet in README.md)
"""

import json
import sys

from .client import CMCError
from .tools import TOOLS, call_tool, new_client

PROTOCOL_VERSION = "2024-11-05"
SERVER_INFO = {"name": "muse-cmc-agent", "version": "0.1.0"}


def _result(request_id, result):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error(request_id, code, message):
    return {"jsonrpc": "2.0", "id": request_id,
            "error": {"code": code, "message": message}}


def handle(request, client):
    method = request.get("method", "")
    request_id = request.get("id")
    params = request.get("params") or {}

    if method == "initialize":
        return _result(request_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        })
    if method == "ping":
        return _result(request_id, {})
    if method == "tools/list":
        return _result(request_id, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments") or {}
        try:
            data, text = call_tool(client, name, args)
        except CMCError as exc:
            return _result(request_id, {
                "content": [{"type": "text",
                             "text": f"Error calling {name}: {exc}"}],
                "isError": True,
            })
        except Exception as exc:  # never crash the server on one call
            return _result(request_id, {
                "content": [{"type": "text",
                             "text": f"Error calling {name}: {exc}"}],
                "isError": True,
            })
        return _result(request_id, {
            "content": [
                {"type": "text", "text": text},
                {"type": "text",
                 "text": "Raw CMC response:\n"
                         + json.dumps(data, indent=2)[:8000]},
            ],
            "isError": False,
        })
    if request_id is None:
        return None  # notification we do not answer (e.g. initialized)
    return _error(request_id, -32601, f"Method not found: {method}")


def main():
    client = new_client()
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            sys.stdout.write(json.dumps(
                _error(None, -32700, "Parse error")) + "\n")
            sys.stdout.flush()
            continue
        response = handle(request, client)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
