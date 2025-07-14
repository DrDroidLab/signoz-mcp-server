from flask import Flask, request, jsonify, make_response
import logging
import os
import json
import yaml
from processor.signoz_processor import SignozApiProcessor

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Load configuration from YAML file
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        raise Exception(f"Configuration file not found at {config_path}")
    except yaml.YAMLError as e:
        raise Exception(f"Error parsing YAML configuration: {e}")

# Initialize configuration
config = load_config()
signoz_config = config.get('signoz', {})

# Initialize Signoz processor
signoz_processor = SignozApiProcessor(
    signoz_host=signoz_config.get('host'),
    signoz_api_key=signoz_config.get('api_key'),
    ssl_verify=signoz_config.get('ssl_verify', 'true')
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

# Test connection function
def test_signoz_connection():
    """Test connection to Signoz API"""
    try:
        result = signoz_processor.test_connection()
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

# Function mapping
FUNCTION_MAPPING = {
    "test_connection": test_signoz_connection
}

# Track initialization state
initialized = False

@app.route('/mcp', methods=['POST', 'GET'])
def mcp_endpoint():
    global initialized

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

    request_id = data.get("id")
    method = data.get("method")
    params = data.get("params", {})

    # Handle JSON-RPC notifications (no id field or method starts with 'notifications/')
    if method and method.startswith('notifications/'):
        # Log and return 200 OK with empty result
        logger.info(f"Received notification: {method}")
        return jsonify({}), 200

    # Handle initialization
    if method == "initialize":
        client_protocol_version = params.get("protocolVersion")
        
        # Validate protocol version
        if client_protocol_version != PROTOCOL_VERSION:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": f"Unsupported protocol version: {client_protocol_version}. Server supports: {PROTOCOL_VERSION}"
                },
                "id": request_id
            }), 400
        
        initialized = True
        
        return jsonify({
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": SERVER_CAPABILITIES,
                "serverInfo": SERVER_INFO
            },
            "id": request_id
        })

    # Check if server is initialized for other methods
    if not initialized and method != "initialize":
        return jsonify({
            "jsonrpc": "2.0",
            "error": {
                "code": -32002,
                "message": "Server not initialized. Call initialize first."
            },
            "id": request_id
        }), 400

    # Handle tools/list
    if method == "tools/list":
        return jsonify({
            "jsonrpc": "2.0",
            "result": {"tools": TOOLS_LIST},
            "id": request_id
        })

    # Handle tools/call
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})

        if not tool_name:
            return jsonify({
                "jsonrpc": "2.0", 
                "error": {
                    "code": -32602, 
                    "message": "Invalid params: 'name' is required for tool execution"
                }, 
                "id": request_id
            }), 400

        if tool_name not in FUNCTION_MAPPING:
            return jsonify({
                "jsonrpc": "2.0", 
                "error": {
                    "code": -32601, 
                    "message": f"Tool not found: {tool_name}"
                }, 
                "id": request_id
            }), 404

        try:
            func = FUNCTION_MAPPING[tool_name]
            result = func(**arguments)
            
            # Format result according to MCP spec
            return jsonify({
                "jsonrpc": "2.0",
                "result": result,
                "id": request_id
            })
        except Exception as e:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32000,
                    "message": f"Error executing tool: {str(e)}"
                },
                "id": request_id
            }), 500

    # Unknown method
    return jsonify({
        "jsonrpc": "2.0",
        "error": {
            "code": -32601,
            "message": f"Method not found: {method}"
        },
        "id": request_id
    }), 404

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = config.get('server', {}).get('port', 5002)
    debug = config.get('server', {}).get('debug', True)
    app.run(host='0.0.0.0', port=port, debug=debug) 