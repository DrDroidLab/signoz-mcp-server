import json
import sys


def run_stdio_server(handler):
    """
    Reads JSON-RPC requests from stdin, calls the handler, and writes responses to stdout.
    The handler should be a function that takes a dict and returns a dict (the response).
    """
    while True:
        line = sys.stdin.readline()
        if not line:
            break  # EOF
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            response = handler(data)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except Exception as e:
            sys.stdout.write(json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": str(e)},
                "id": None
            }) + "\n")
            sys.stdout.flush() 