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
    },
    {
        "name": "fetch_dashboards",
        "description": "Fetch all available dashboards from Signoz.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "fetch_dashboard_details",
        "description": "Fetch detailed information about a specific dashboard by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dashboard_id": {
                    "type": "string",
                    "description": "The ID of the dashboard to fetch details for"
                }
            },
            "required": ["dashboard_id"]
        }
    },
    {
        "name": "query_metrics",
        "description": "Query metrics from Signoz with specified time range and query parameters.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_time": {
                    "type": "number",
                    "description": "Start time in Unix timestamp (seconds or milliseconds)"
                },
                "end_time": {
                    "type": "number",
                    "description": "End time in Unix timestamp (seconds or milliseconds)"
                },
                "query": {
                    "type": "string",
                    "description": "The metrics query to execute"
                },
                "step": {
                    "type": "string",
                    "description": "Optional step interval for the query (e.g., '1m', '5m', '1h')"
                },
                "aggregation": {
                    "type": "string",
                    "description": "Optional aggregation function (e.g., 'avg', 'sum', 'min', 'max')"
                }
            },
            "required": ["start_time", "end_time", "query"]
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

# Fetch dashboards function
def fetch_signoz_dashboards():
    """Fetch all available dashboards from Signoz"""
    try:
        result = signoz_processor.fetch_dashboards()
        if result:
            return {
                "status": "success",
                "message": "Successfully fetched dashboards",
                "data": result
            }
        else:
            return {
                "status": "failed",
                "message": "Failed to fetch dashboards"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch dashboards: {str(e)}"
        }

# Fetch dashboard details function
def fetch_signoz_dashboard_details(dashboard_id):
    """Fetch detailed information about a specific dashboard"""
    try:
        result = signoz_processor.fetch_dashboard_details(dashboard_id)
        if result:
            return {
                "status": "success",
                "message": f"Successfully fetched dashboard details for ID: {dashboard_id}",
                "data": result
            }
        else:
            return {
                "status": "failed",
                "message": f"Failed to fetch dashboard details for ID: {dashboard_id}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch dashboard details: {str(e)}"
        }

# Query metrics function
def query_signoz_metrics(start_time, end_time, query, step=None, aggregation=None):
    """Query metrics from Signoz with specified parameters"""
    try:
        result = signoz_processor.query_metrics(start_time, end_time, query, step, aggregation)
        if result:
            return {
                "status": "success",
                "message": "Successfully queried metrics",
                "data": result,
                "query_params": {
                    "start_time": start_time,
                    "end_time": end_time,
                    "query": query,
                    "step": step,
                    "aggregation": aggregation
                }
            }
        else:
            return {
                "status": "failed",
                "message": "Failed to query metrics"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to query metrics: {str(e)}"
        }

# Function mapping
FUNCTION_MAPPING = {
    "test_connection": test_signoz_connection,
    "fetch_dashboards": fetch_signoz_dashboards,
    "fetch_dashboard_details": fetch_signoz_dashboard_details,
    "query_metrics": query_signoz_metrics
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
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                },
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