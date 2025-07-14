from flask import Flask, request, jsonify, make_response, current_app
import logging
import os
import json
import yaml
from processor.signoz_processor import SignozApiProcessor
import sys
from stdio_server import run_stdio_server

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Load configuration from environment variables, then YAML as fallback
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    config = {}
    # Try to load YAML config as fallback
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        config = {}
    except yaml.YAMLError as e:
        raise Exception(f"Error parsing YAML configuration: {e}")

    # Environment variable overrides
    signoz_host = os.environ.get('SIGNOZ_HOST') or (config.get('signoz', {}).get('host') if config.get('signoz') else None)
    signoz_api_key = os.environ.get('SIGNOZ_API_KEY') or (config.get('signoz', {}).get('api_key') if config.get('signoz') else None)
    signoz_ssl_verify = os.environ.get('SIGNOZ_SSL_VERIFY') or (config.get('signoz', {}).get('ssl_verify', 'true') if config.get('signoz') else 'true')
    server_port = int(os.environ.get('MCP_SERVER_PORT') or (config.get('server', {}).get('port', 8000) if config.get('server') else 8000))
    server_debug = os.environ.get('MCP_SERVER_DEBUG')
    if server_debug is not None:
        server_debug = server_debug.lower() in ['1', 'true', 'yes']
    else:
        server_debug = config.get('server', {}).get('debug', True) if config.get('server') else True

    return {
        'signoz': {
            'host': signoz_host,
            'api_key': signoz_api_key,
            'ssl_verify': signoz_ssl_verify
        },
        'server': {
            'port': server_port,
            'debug': server_debug
        }
    }

# Initialize configuration and processor at app startup
with app.app_context():
    config = load_config()
    app.config['SIGNOZ_CONFIG'] = config.get('signoz', {})
    app.config['SERVER_CONFIG'] = config.get('server', {})
    app.config['signoz_processor'] = SignozApiProcessor(
        signoz_host=app.config['SIGNOZ_CONFIG'].get('host'),
        signoz_api_key=app.config['SIGNOZ_CONFIG'].get('api_key'),
        ssl_verify=app.config['SIGNOZ_CONFIG'].get('ssl_verify', 'true')
    )

# Server info
SERVER_INFO = {
    "name": "signoz-mcp-server",
    "version": "1.0.0"
}

# Server capabilities
SERVER_CAPABILITIES = {
    "tools": {}
}

# Protocol version
PROTOCOL_VERSION = "2025-06-18"

# Available tools
TOOLS_LIST = [
    {
        "name": "test_connection",
        "description": "Test connection to Signoz API to verify configuration and connectivity.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]

def test_signoz_connection():
    """Test connection to Signoz API"""
    try:
        processor = current_app.config['signoz_processor']
        signoz_config = current_app.config['SIGNOZ_CONFIG']
        result = processor.test_connection()
        if result:
            return {
                "status": "success",
                "message": "Successfully connected to Signoz API",
                "host": signoz_config.get('host'),
                "ssl_verify": signoz_config.get('ssl_verify', 'true')
            }
        else:
            return {
                "status": "failed",
                "message": "Failed to connect to Signoz API"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Connection test failed: {str(e)}"
        }

FUNCTION_MAPPING = {
    "test_connection": test_signoz_connection
}

def handle_jsonrpc_request(data):
    request_id = data.get("id")
    method = data.get("method")
    params = data.get("params", {})

    # Handle JSON-RPC notifications (no id field or method starts with 'notifications/')
    if method and method.startswith('notifications/'):
        logger.info(f"Received notification: {method}")
        return {"jsonrpc": "2.0", "result": {}, "id": request_id}

    # Handle initialization (stateless: just validate and return capabilities)
    if method == "initialize":
        client_protocol_version = params.get("protocolVersion")
        if client_protocol_version != PROTOCOL_VERSION:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": f"Unsupported protocol version: {client_protocol_version}. Server supports: {PROTOCOL_VERSION}"
                },
                "id": request_id
            }
        return {
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": SERVER_CAPABILITIES,
                "serverInfo": SERVER_INFO
            },
            "id": request_id
        }

    # Handle tools/list
    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "result": {"tools": TOOLS_LIST},
            "id": request_id
        }

    # Handle tools/call
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        if not tool_name:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": "Invalid params: 'name' is required for tool execution"
                },
                "id": request_id
            }
        if tool_name not in FUNCTION_MAPPING:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Tool not found: {tool_name}"
                },
                "id": request_id
            }
        try:
            func = FUNCTION_MAPPING[tool_name]
            result = func(**arguments)
            return {
                "jsonrpc": "2.0",
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                },
                "id": request_id
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": f"Error executing tool: {str(e)}"
                },
                "id": request_id
            }

    # Unknown method
    return {
        "jsonrpc": "2.0",
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        },
        "id": request_id
    }

@app.route('/mcp', methods=['POST', 'GET'])
def mcp_endpoint():
    if request.method == 'GET':
        # Return a friendly message or 405 for GET requests
        return make_response(jsonify({
            "message": "This endpoint expects JSON-RPC POST requests. Use POST with application/json."
        }), 405)

    data = request.get_json()
    print(f"Received request: {data}")
    logger.info(f"Received request: {data}")

    if not data:
        return jsonify({
            "jsonrpc": "2.0",
            "error": {"code": -32700, "message": "Parse error"},
            "id": None
        }), 400

    response = handle_jsonrpc_request(data)
    status_code = 200
    if "error" in response:
        # Map error codes to HTTP status codes
        code = response["error"].get("code", -32000)
        if code == -32700 or code == -32600 or code == -32602:
            status_code = 400
        elif code == -32601:
            status_code = 404
        else:
            status_code = 500
    return jsonify(response), status_code

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    if '-t' in sys.argv and 'stdio' in sys.argv:
        run_stdio_server(handle_jsonrpc_request)
    else:
        port = app.config['SERVER_CONFIG'].get('port', 8000)
        debug = app.config['SERVER_CONFIG'].get('debug', True)
        app.run(host='0.0.0.0', port=port, debug=debug) 