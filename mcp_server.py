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
    },
    {
        "name": "fetch_apm_metrics",
        "description": "Fetch standard APM metrics (request rate, error rate, latency, apdex, etc.) for a given service and time range.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "description": "The name of the service to fetch APM metrics for"
                },
                "start_time": {
                    "type": "number",
                    "description": "Start time in Unix timestamp (seconds or milliseconds)"
                },
                "end_time": {
                    "type": "number",
                    "description": "End time in Unix timestamp (seconds or milliseconds)"
                },
                "window": {
                    "type": "string",
                    "description": "Query window (e.g., '1m', '5m'). Default: '1m'",
                    "default": "1m"
                }
            },
            "required": ["service_name", "start_time", "end_time"]
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

# Fetch dashboards function
def fetch_signoz_dashboards():
    """Fetch all available dashboards from Signoz"""
    try:
        signoz_processor= current_app.config['signoz_processor']
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
        signoz_processor= current_app.config['signoz_processor']
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
        signoz_processor= current_app.config['signoz_processor']
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

def fetch_signoz_apm_metrics(service_name, start_time, end_time, window="1m"):
    """Fetch standard APM metrics for a given service and time range."""
    try:
        signoz_processor = current_app.config['signoz_processor']
        result = signoz_processor.fetch_apm_metrics(service_name, start_time, end_time, window)
        return {
            "status": "success",
            "message": f"Fetched APM metrics for service: {service_name}",
            "data": result,
            "query_params": {
                "service_name": service_name,
                "start_time": start_time,
                "end_time": end_time,
                "window": window
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to fetch APM metrics: {str(e)}"
        }

# Function mapping
FUNCTION_MAPPING = {
    "test_connection": test_signoz_connection,
    "fetch_dashboards": fetch_signoz_dashboards,
    "fetch_dashboard_details": fetch_signoz_dashboard_details,
    "query_metrics": query_signoz_metrics,
    "fetch_apm_metrics": fetch_signoz_apm_metrics
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