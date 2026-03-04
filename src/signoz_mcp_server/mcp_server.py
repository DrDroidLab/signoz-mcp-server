import datetime
import json
import logging
import os
import sys

import yaml
from flask import Flask, current_app, jsonify, make_response, request

from signoz_mcp_server.processor.signoz_processor import SignozApiProcessor
from signoz_mcp_server.stdio_server import run_stdio_server

app = Flask(__name__)
logger = logging.getLogger(__name__)


# Load configuration from environment variables, then YAML as fallback
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    config = {}
    # Try to load YAML config as fallback
    try:
        with open(config_path) as file:
            config = yaml.safe_load(file)
    except FileNotFoundError:
        config = {}
    except yaml.YAMLError as e:
        raise Exception(f"Error parsing YAML configuration: {e}") from e

    # Environment variable overrides
    signoz_host = os.environ.get("SIGNOZ_HOST") or (config.get("signoz", {}).get("host") if config.get("signoz") else None)
    signoz_api_key = os.environ.get("SIGNOZ_API_KEY") or (config.get("signoz", {}).get("api_key") if config.get("signoz") else None)
    signoz_ssl_verify = os.environ.get("SIGNOZ_SSL_VERIFY") or (
        config.get("signoz", {}).get("ssl_verify", "true") if config.get("signoz") else "true"
    )
    server_port = int(os.environ.get("MCP_SERVER_PORT") or (config.get("server", {}).get("port", 8000) if config.get("server") else 8000))
    server_debug = os.environ.get("MCP_SERVER_DEBUG")
    if server_debug is not None:
        server_debug = server_debug.lower() in ["1", "true", "yes"]
    else:
        server_debug = config.get("server", {}).get("debug", True) if config.get("server") else True

    return {
        "signoz": {"host": signoz_host, "api_key": signoz_api_key, "ssl_verify": signoz_ssl_verify},
        "server": {"port": server_port, "debug": server_debug},
    }


# Initialize configuration and processor at app startup
with app.app_context():
    config = load_config()
    app.config["SIGNOZ_CONFIG"] = config.get("signoz", {})
    app.config["SERVER_CONFIG"] = config.get("server", {})
    app.config["signoz_processor"] = SignozApiProcessor(
        signoz_host=app.config["SIGNOZ_CONFIG"].get("host"),
        signoz_api_key=app.config["SIGNOZ_CONFIG"].get("api_key"),
        ssl_verify=app.config["SIGNOZ_CONFIG"].get("ssl_verify", "true"),
    )

# Server info
SERVER_INFO = {"name": "signoz-mcp-server", "version": "1.0.0"}

# Server capabilities
SERVER_CAPABILITIES = {"tools": {}}

# Protocol version
PROTOCOL_VERSION = "2025-06-18"


def get_current_time_iso():
    date_time = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return date_time


# Available tools
TOOLS_LIST = [
    {
        "name": "test_connection",
        "description": "Test connection to Signoz API to verify configuration and connectivity.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "fetch_dashboards",
        "description": "Fetch all available dashboards from Signoz.",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "fetch_dashboard_details",
        "description": "Fetch detailed information about a specific dashboard by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {"dashboard_id": {"type": "string", "description": "The ID of the dashboard to fetch details for"}},
            "required": ["dashboard_id"],
        },
    },
    {
        "name": "fetch_dashboard_data",
        "description": f"Fetch all panel data for a given Signoz dashboard by name and time range. Current datetime is {get_current_time_iso()}",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dashboard_name": {"type": "string", "description": "The name of the dashboard to fetch data for"},
                "start_time": {
                    "type": "string",
                    "description": (
                        "Start time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z') or duration string (e.g., '2h', '90m')"
                    ),
                },
                "end_time": {
                    "type": "string",
                    "description": (
                        "End time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z') or duration string (e.g., '2h', '90m')"
                    ),
                },
                "step": {"type": "number", "description": "Step interval for the query (seconds, optional)"},
                "variables_json": {"type": "string", "description": "Optional variable overrides as a JSON object"},
                "duration": {"type": "string", "description": "Duration string for the time window (e.g., '2h', '90m')"},
            },
            "required": ["dashboard_name"],
        },
    },
    {
        "name": "fetch_apm_metrics",
        "description": (
            f"Fetch standard APM metrics (request rate, error rate, latency, apdex, etc.) for a given service and time range. "
            f"Current datetime is {get_current_time_iso()}"
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_name": {"type": "string", "description": "The name of the service to fetch APM metrics for"},
                "start_time": {
                    "type": "string",
                    "description": (
                        "Start time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z') or duration string (e.g., '2h', '90m')"
                    ),
                },
                "end_time": {
                    "type": "string",
                    "description": (
                        "End time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z') or duration string (e.g., '2h', '90m')"
                    ),
                },
                "window": {
                    "type": "string",
                    "description": "Query window (e.g., '1m', '5m'). Default: '1m'",
                    "default": "1m",
                },
                "duration": {"type": "string", "description": ("Duration string for the time window (e.g., '2h', '90m')")},
            },
            "required": ["service_name"],
        },
    },
    {
        "name": "fetch_services",
        "description": "Fetch all instrumented services from SigNoz.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_time": {
                    "type": "string",
                    "description": (
                        "Start time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z') or duration string (e.g., '2h', '90m')"
                    ),
                },
                "end_time": {
                    "type": "string",
                    "description": (
                        "End time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z') or duration string (e.g., '2h', '90m')"
                    ),
                },
                "duration": {
                    "type": "string",
                    "description": "Duration string for the time window (e.g., '2h', '90m'). Defaults to last 24 hours if not provided.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "execute_clickhouse_query",
        "description": "Execute a Clickhouse SQL query via the Signoz API.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The Clickhouse SQL query to execute."},
                "start_time": {
                    "type": "string",
                    "description": (
                        "Start time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z') or duration string (e.g., '2h', '90m')"
                    ),
                },
                "end_time": {
                    "type": "string",
                    "description": (
                        "End time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z') or duration string (e.g., '2h', '90m')"
                    ),
                },
                "duration": {"type": "string", "description": "Duration string for the time window (e.g., '2h', '90m')"},
                "panel_type": {"type": "string", "description": "Panel type (e.g., 'table', 'graph').", "default": "table"},
                "fill_gaps": {"type": "boolean", "description": "Whether to fill gaps in the data.", "default": False},
                "step": {"type": "number", "description": "Step interval in seconds.", "default": 60},
            },
            "required": ["query"],
        },
    },
    {
        "name": "execute_builder_query",
        "description": (
            "Execute a Signoz builder query via the Signoz API. The 'builder_queries' parameter must be a dictionary with keys like 'A', 'B', etc., "
            "each mapping to a full builder query object as expected by the SigNoz API. "
            'Example: {"A": {"queryName": "A", "expression": "A", "dataSource": "metrics", '
            '"aggregateOperator": "rate", "aggregateAttribute": {"key": "signoz_calls_total", '
            '"dataType": "float64", "isColumn": true, "type": ""}, "timeAggregation": "rate", '
            '"spaceAggregation": "sum", "functions": [], "filters": {"items": [], "op": "AND"}, '
            '"disabled": false, "stepInterval": 60, "legend": "Calls Rate", "groupBy": [{"key": '
            '"service.name", "dataType": "string", "isColumn": false, "type": "resource"}] }}. '
            "Each builder query object should include all required fields for a SigNoz builder query."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "builder_queries": {
                    "type": "object",
                    "description": (
                        "Dictionary of builder queries. Each key (e.g., 'A', 'B') must map to a full builder query object. "
                        "Each builder query object should include: queryName, expression, dataSource, aggregateOperator, "
                        "aggregateAttribute, timeAggregation, spaceAggregation, functions, filters, disabled, stepInterval, "
                        "legend, groupBy, etc. IMPORTANT: groupBy must be an array of AttributeKey objects, not strings. "
                        'Example for groupBy: [{"key": "service.name", "dataType": "string", '
                        '"isColumn": false, "type": "resource"}]. '
                        'Example builder_queries: {"A": {"queryName": "A", "expression": "A", '
                        '"dataSource": "metrics", "aggregateOperator": "rate", "aggregateAttribute": '
                        '{"key": "signoz_calls_total", "dataType": "float64", "isColumn": true, '
                        '"type": ""}, "timeAggregation": "rate", "spaceAggregation": "sum", '
                        '"functions": [], "filters": {"items": [], "op": "AND"}, "disabled": false, '
                        '"stepInterval": 60, "legend": "Calls Rate", "groupBy": [{"key": "service.name", '
                        '"dataType": "string", "isColumn": false, "type": "resource"}] }}'
                    ),
                },
                "start_time": {
                    "type": "string",
                    "description": (
                        "Start time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z') or duration string (e.g., '2h', '90m')"
                    ),
                },
                "end_time": {
                    "type": "string",
                    "description": (
                        "End time in RFC3339 or relative string (e.g., 'now-2h', '2023-01-01T00:00:00Z') or duration string (e.g., '2h', '90m')"
                    ),
                },
                "duration": {"type": "string", "description": "Duration string for the time window (e.g., '2h', '90m')"},
                "panel_type": {"type": "string", "description": "Panel type (e.g., 'table', 'graph').", "default": "table"},
                "step": {"type": "number", "description": "Step interval in seconds.", "default": 60},
            },
            "required": ["builder_queries"],
        },
    },
    {
        "name": "fetch_traces_or_logs",
        "description": (
            "Fetch traces or logs from SigNoz using ClickHouse SQL. "
            "Specify data_type ('traces' or 'logs'). "
            "Supports time range, service_name, and limit."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "data_type": {"type": "string", "description": "'traces' or 'logs' (required)"},
                "start_time": {"type": "string", "description": "Start time (RFC3339, 'now-2h', etc.)"},
                "end_time": {"type": "string", "description": "End time (RFC3339, 'now', etc.)"},
                "duration": {"type": "string", "description": "Duration string (e.g., '2h', '90m')"},
                "service_name": {"type": "string", "description": "Filter by service name (optional)"},
                "limit": {"type": "number", "description": "Max number of records to return (default 100)"},
            },
            "required": ["data_type"],
        },
    },
]


def test_signoz_connection():
    """Test connection to Signoz API"""
    try:
        processor = current_app.config["signoz_processor"]
        signoz_config = current_app.config["SIGNOZ_CONFIG"]
        result = processor.test_connection()
        if result:
            return {
                "status": "success",
                "message": "Successfully connected to Signoz API",
                "host": signoz_config.get("host"),
                "ssl_verify": signoz_config.get("ssl_verify", "true"),
            }
        else:
            return {"status": "failed", "message": "Failed to connect to Signoz API"}
    except Exception as e:
        return {"status": "error", "message": f"Connection test failed: {e!s}"}


# Fetch dashboards function
def fetch_signoz_dashboards():
    """Fetch all available dashboards from Signoz"""
    try:
        signoz_processor = current_app.config["signoz_processor"]
        result = signoz_processor.fetch_dashboards()
        if result:
            return {"status": "success", "message": "Successfully fetched dashboards", "data": result}
        else:
            return {"status": "failed", "message": "Failed to fetch dashboards"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch dashboards: {e!s}"}


# Fetch dashboard details function
def fetch_signoz_dashboard_details(dashboard_id):
    """Fetch detailed information about a specific dashboard"""
    try:
        signoz_processor = current_app.config["signoz_processor"]
        result = signoz_processor.fetch_dashboard_details(dashboard_id)
        if result:
            return {"status": "success", "message": f"Successfully fetched dashboard details for ID: {dashboard_id}", "data": result}
        else:
            return {"status": "failed", "message": f"Failed to fetch dashboard details for ID: {dashboard_id}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch dashboard details: {e!s}"}


def fetch_signoz_dashboard_data(dashboard_name, start_time=None, end_time=None, step=None, variables_json=None, duration=None):
    """Fetch all panel data for a given Signoz dashboard by name and time range.
    Accepts start_time and end_time as RFC3339 or relative strings, or a duration string.
    If start_time and end_time are not provided, defaults to last 3 hours."""
    try:
        signoz_processor = current_app.config["signoz_processor"]
        result = signoz_processor.fetch_dashboard_data(
            dashboard_name=dashboard_name, start_time=start_time, end_time=end_time, step=step, variables_json=variables_json, duration=duration
        )
        if result.get("status") == "success":
            return {"status": "success", "message": f"Successfully fetched dashboard data for: {dashboard_name}", "data": result}
        else:
            return {"status": "failed", "message": result.get("message", "Failed to fetch dashboard data"), "data": result}
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch dashboard data: {e!s}"}


def fetch_signoz_apm_metrics(service_name, start_time=None, end_time=None, window="1m", duration=None):
    """Fetch standard APM metrics for a given service and time range. Accepts start_time and end_time as RFC3339 or relative strings
    (e.g., 'now-2h'), or a duration string (e.g., '2h', '90m'). Defaults to last 3 hours if not provided.
    """
    try:
        signoz_processor = current_app.config["signoz_processor"]
        result = signoz_processor.fetch_apm_metrics(service_name, start_time, end_time, window, duration=duration)
        return {
            "status": "success",
            "message": f"Fetched APM metrics for service: {service_name}",
            "data": result,
            "query_params": {"service_name": service_name, "start_time": start_time, "end_time": end_time, "window": window, "duration": duration},
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch APM metrics: {e!s}"}


def fetch_signoz_services(start_time=None, end_time=None, duration=None):
    """Fetch all instrumented services from SigNoz"""
    try:
        signoz_processor = current_app.config["signoz_processor"]
        result = signoz_processor.fetch_services(start_time, end_time, duration)
        if result and (isinstance(result, dict) and result.get("status") == "error"):
            return {"status": "failed", "message": result.get("message", "Failed to fetch services"), "details": result.get("details")}
        return {"status": "success", "message": "Successfully fetched services", "data": result}
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch services: {e!s}"}


def execute_signoz_clickhouse_query(query, start_time=None, end_time=None, duration=None, panel_type="table", fill_gaps=False, step=60):
    """Execute a Clickhouse SQL query via the Signoz API."""
    try:
        signoz_processor = current_app.config["signoz_processor"]
        # Use the same time range logic as other tools
        start_dt, end_dt = signoz_processor._get_time_range(start_time, end_time, duration, default_hours=3)
        time_geq = start_dt.timestamp()
        time_lt = end_dt.timestamp()
        result = signoz_processor.execute_clickhouse_query_tool(
            query=query,
            time_geq=time_geq,
            time_lt=time_lt,
            panel_type=panel_type,
            fill_gaps=fill_gaps,
            step=step,
        )
        return {"status": "success", "message": "Successfully executed Clickhouse query", "data": result}
    except Exception as e:
        return {"status": "error", "message": f"Failed to execute Clickhouse query: {e!s}"}


def execute_signoz_builder_query(builder_queries, start_time=None, end_time=None, duration=None, panel_type="table", step=60):
    """Execute a Signoz builder query via the Signoz API."""
    try:
        signoz_processor = current_app.config["signoz_processor"]
        # Use the same time range logic as other tools
        start_dt, end_dt = signoz_processor._get_time_range(start_time, end_time, duration, default_hours=3)
        time_geq = start_dt.timestamp()
        time_lt = end_dt.timestamp()
        result = signoz_processor.execute_builder_query_tool(
            builder_queries=builder_queries,
            time_geq=time_geq,
            time_lt=time_lt,
            panel_type=panel_type,
            step=step,
        )
        return {"status": "success", "message": "Successfully executed builder query", "data": result}
    except Exception as e:
        return {"status": "error", "message": f"Failed to execute builder query: {e!s}"}


def fetch_signoz_traces_or_logs(data_type, start_time=None, end_time=None, duration=None, service_name=None, limit=100):
    """Fetch traces or logs from SigNoz using ClickHouse SQL."""
    try:
        signoz_processor = current_app.config["signoz_processor"]
        # Use the same time range logic as other tools
        start_dt, end_dt = signoz_processor._get_time_range(start_time, end_time, duration, default_hours=3)
        time_geq = int(start_dt.timestamp())
        time_lt = int(end_dt.timestamp())
        limit = int(limit) if limit else 100
        if data_type == "traces":
            table = "signoz_traces.distributed_signoz_index_v3"
            select_cols = "traceID, serviceName, name, durationNano, statusCode, timestamp"
            where_clauses = [f"timestamp >= toDateTime64({int(start_dt.timestamp())}, 9)", f"timestamp < toDateTime64({int(end_dt.timestamp())}, 9)"]
            if service_name:
                where_clauses.append(f"serviceName = '{service_name}'")
        elif data_type == "logs":
            table = "signoz_logs.distributed_logs"
            select_cols = "timestamp, body, severity_text, resource_attributes, trace_id, span_id"
            where_clauses = [f"timestamp >= toDateTime64({int(start_dt.timestamp())}, 9)", f"timestamp < toDateTime64({int(end_dt.timestamp())}, 9)"]
            if service_name:
                where_clauses.append(f"JSONExtractString(resource_attributes, 'service.name') = '{service_name}'")
        else:
            return {"status": "error", "message": f"Invalid data_type: {data_type}. Must be 'traces' or 'logs'."}
        where_sql = " AND ".join(where_clauses)
        query = f"SELECT {select_cols} FROM {table} WHERE {where_sql} LIMIT {limit}"
        result = signoz_processor.execute_clickhouse_query_tool(
            query=query,
            time_geq=time_geq,
            time_lt=time_lt,
            panel_type="table",
            fill_gaps=False,
            step=60
        )
        return {"status": "success", "message": f"Fetched {data_type}", "data": result, "query": query}
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch {data_type}: {e!s}"}


# Function mapping
FUNCTION_MAPPING = {
    "test_connection": test_signoz_connection,
    "fetch_dashboards": fetch_signoz_dashboards,
    "fetch_dashboard_details": fetch_signoz_dashboard_details,
    "fetch_dashboard_data": fetch_signoz_dashboard_data,
    "fetch_apm_metrics": fetch_signoz_apm_metrics,
    "fetch_services": fetch_signoz_services,
    "execute_clickhouse_query": execute_signoz_clickhouse_query,
    "execute_builder_query": execute_signoz_builder_query,
    "fetch_traces_or_logs": fetch_signoz_traces_or_logs,
}


def handle_jsonrpc_request(data):
    request_id = data.get("id")
    method = data.get("method")
    params = data.get("params", {})

    # Handle JSON-RPC notifications (no id field or method starts with 'notifications/')
    if method and method.startswith("notifications/"):
        logger.info(f"Received notification: {method}")
        return {"jsonrpc": "2.0", "result": {}, "id": request_id}

    # Handle initialization (stateless: just validate and return capabilities)
    if method == "initialize":
        client_protocol_version = params.get("protocolVersion")
        # Accept any protocol version that starts with '2025-'
        if not (isinstance(client_protocol_version, str) and client_protocol_version.startswith("2025-")):
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32602, "message": f"Unsupported protocol version: {client_protocol_version}. Server supports: {PROTOCOL_VERSION}"},
                "id": request_id,
            }
        return {
            "jsonrpc": "2.0",
            "result": {"protocolVersion": PROTOCOL_VERSION, "capabilities": SERVER_CAPABILITIES, "serverInfo": SERVER_INFO},
            "id": request_id,
        }

    # Handle tools/list
    if method == "tools/list":
        return {"jsonrpc": "2.0", "result": {"tools": TOOLS_LIST}, "id": request_id}

    # Handle tools/call
    if method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        if not tool_name:
            return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params: 'name' is required for tool execution"}, "id": request_id}
        if tool_name not in FUNCTION_MAPPING:
            return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Tool not found: {tool_name}"}, "id": request_id}
        try:
            func = FUNCTION_MAPPING[tool_name]
            result = func(**arguments)
            return {"jsonrpc": "2.0", "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}, "id": request_id}
        except Exception as e:
            return {"jsonrpc": "2.0", "error": {"code": -32000, "message": f"Error executing tool: {e!s}"}, "id": request_id}

    # Unknown method
    return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method not found: {method}"}, "id": request_id}


@app.route("/mcp", methods=["POST", "GET"])
def mcp_endpoint():
    if request.method == "GET":
        # Return a friendly message or 405 for GET requests
        return make_response(jsonify({"message": "This endpoint expects JSON-RPC POST requests. Use POST with application/json."}), 405)

    data = request.get_json()
    print(f"Received request: {data}")
    logger.info(f"Received request: {data}")

    if not data:
        return jsonify({"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None}), 400

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


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})


def main():
    transport = os.environ.get("MCP_TRANSPORT", "http")
    if ("-t" in sys.argv and "stdio" in sys.argv) or ("--transport" in sys.argv and "stdio" in sys.argv) or (transport == "stdio"):

        def stdio_handler(data):
            with app.app_context():
                return handle_jsonrpc_request(data)

        run_stdio_server(stdio_handler)
    else:
        port = app.config["SERVER_CONFIG"].get("port", 8000)
        debug = app.config["SERVER_CONFIG"].get("debug", True)
        app.run(host="0.0.0.0", port=port, debug=debug)


if __name__ == "__main__":
    main()
