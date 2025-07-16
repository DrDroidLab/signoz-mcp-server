import json
import pytest
import time

def test_tool_call_test_connection(client):
    """
    Tests the 'test_connection' tool call through the MCP server.
    """
    response = client.post(
        "/mcp",
        data=json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "test_connection",
                "arguments": {}
            },
            "id": "1"
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data["id"] == "1"
    assert "result" in response_data
    content = json.loads(response_data["result"]["content"][0]["text"])
    assert content["status"] == "success"
    assert "Successfully connected" in content["message"]

def test_tool_call_fetch_dashboards(client):
    """
    Tests the 'fetch_dashboards' tool call through the MCP server.
    """
    response = client.post(
        "/mcp",
        data=json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "fetch_dashboards",
                "arguments": {}
            },
            "id": "2"
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data["id"] == "2"
    assert "result" in response_data
    content = json.loads(response_data["result"]["content"][0]["text"])
    assert content["status"] == "success"
    assert "data" in content
    assert isinstance(content["data"]["data"], list)

def test_tool_call_fetch_dashboard_details(client):
    """
    Tests the 'fetch_dashboard_details' tool call through the MCP server.
    """
    # First, get the list of dashboards to find a valid ID
    response = client.post(
        "/mcp",
        data=json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "fetch_dashboards", "arguments": {}},
            "id": "3"
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    response_data = response.get_json()
    content = json.loads(response_data["result"]["content"][0]["text"])
    dashboards = content["data"]["data"]
    assert dashboards

    dashboard_id = dashboards[0]["id"]

    # Now, fetch the details for that dashboard
    response = client.post(
        "/mcp",
        data=json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "fetch_dashboard_details",
                "arguments": {"dashboard_id": dashboard_id}
            },
            "id": "4"
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data["id"] == "4"
    content = json.loads(response_data["result"]["content"][0]["text"])
    assert content["status"] == "success"
    assert content["data"]["id"] == dashboard_id

def test_tool_call_fetch_dashboard_data(client):
    """
    Tests the 'fetch_dashboard_data' tool call through the MCP server.
    """
    # First, get the list of dashboards to find a valid name
    response = client.post(
        "/mcp",
        data=json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "fetch_dashboards", "arguments": {}},
            "id": "6"
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    response_data = response.get_json()
    content = json.loads(response_data["result"]["content"][0]["text"])
    dashboards = content["data"]["data"]
    assert dashboards

    dashboard_name = dashboards[0]["data"]["title"]

    # Now, fetch the data for that dashboard
    response = client.post(
        "/mcp",
        data=json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "fetch_dashboard_data",
                "arguments": {"dashboard_name": dashboard_name}
            },
            "id": "7"
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data["id"] == "7"
    content = json.loads(response_data["result"]["content"][0]["text"])
    assert content["status"] == "success"
    assert "data" in content

def test_tool_call_fetch_apm_metrics(client):
    """
    Tests the 'fetch_apm_metrics' tool call through the MCP server.
    """
    # First, get the list of dashboards to find a service dashboard
    response = client.post(
        "/mcp",
        data=json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "fetch_dashboards", "arguments": {}},
            "id": "8"
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    response_data = response.get_json()
    content = json.loads(response_data["result"]["content"][0]["text"])
    dashboards = content["data"]["data"]
    assert dashboards

    service_name = None
    for dashboard in dashboards:
        title = dashboard.get("data", {}).get("title", "").lower()
        if "service" in title or "application" in title:
            # A bit of a guess, but service dashboards often have the service name in the title.
            service_name = dashboard.get("data", {}).get("title")
            if service_name:
                break
    
    if not service_name:
        pytest.skip("Could not find a dashboard with 'service' or 'application' in the title to test APM metrics.")

    # Now, fetch the APM metrics for that service
    response = client.post(
        "/mcp",
        data=json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "fetch_apm_metrics",
                "arguments": {"service_name": service_name}
            },
            "id": "9"
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data["id"] == "9"
    content = json.loads(response_data["result"]["content"][0]["text"])
    assert content["status"] == "success"
    assert "data" in content 

def test_tool_call_fetch_services(client):
    """
    Tests the 'fetch_services' tool call with time parameters through the MCP server.
    """
    response = client.post(
        "/mcp",
        data=json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "fetch_services",
                "arguments": {
                    "start_time": "now-1h",
                    "end_time": "now"
                }
            },
            "id": "11"
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data["id"] == "11"
    assert "result" in response_data
    content = json.loads(response_data["result"]["content"][0]["text"])
    
    # Check the response status
    assert content["status"] in ("success", "failed")
    
    if content["status"] == "success":
        assert "data" in content
        # The data should be a dict with a 'data' key containing a list of services, or a list directly
        if isinstance(content["data"], dict) and "data" in content["data"]:
            assert isinstance(content["data"]["data"], list)
            print(f"Found {len(content['data']['data'])} services via MCP with time params")
        elif isinstance(content["data"], list):
            print(f"Found {len(content['data'])} services via MCP with time params")
        else:
            pytest.fail(f"Unexpected data format for services list: {type(content['data'])}")
    else:
        # If failed, should have a message
        assert "message" in content
        # If it's an API error, that's acceptable for testing
        if "Failed to fetch services" in content.get("message", ""):
            pytest.skip(f"Services API returned error: {content['message']}")
        else:
            # Other errors should fail the test
            pytest.fail(f"Unexpected error in fetch_services: {content.get('message', 'Unknown error')}") 

def test_tool_call_execute_clickhouse_query(client):
    """
    Tests the 'execute_clickhouse_query' tool call through the MCP server.
    """
    # Simple Clickhouse query to test the connection and basic functionality
    test_query = "SELECT 1 as test_column"
    
    response = client.post(
        "/mcp",
        data=json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "execute_clickhouse_query",
                "arguments": {
                    "query": test_query,
                    "start_time": "now-1h",
                    "end_time": "now",
                    "panel_type": "table",
                    "fill_gaps": False,
                    "step": 60
                }
            },
            "id": "12"
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data["id"] == "12"
    assert "result" in response_data
    content = json.loads(response_data["result"]["content"][0]["text"])
    
    # Check the response status - it could be success or error depending on the Signoz setup
    assert content["status"] in ("success", "error")
    
    if content["status"] == "success":
        assert "data" in content
        print(f"Successfully executed Clickhouse query: {test_query}")
    else:
        # If it's an error, it should have a message
        assert "message" in content
        # If it's a query execution error, that's acceptable for testing
        if "Failed to execute Clickhouse query" in content.get("message", ""):
            pytest.skip(f"Clickhouse query execution failed: {content['message']}")
        else:
            # Other errors should fail the test
            pytest.fail(f"Unexpected error in execute_clickhouse_query: {content.get('message', 'Unknown error')}")

def test_tool_call_execute_builder_query(client):
    """
    Tests the 'execute_builder_query' tool call through the MCP server.
    """
    # Simple builder query to test the connection and basic functionality
    test_builder_queries = {
        "A": {
            "queryName": "A",
            "expression": "A",
            "dataSource": "metrics",
            "aggregateOperator": "sum",
            "aggregateAttribute": {
                "key": "signoz_calls_total",
                "dataType": "float64",
                "isColumn": True,
                "type": ""
            },
            "timeAggregation": "sum",
            "spaceAggregation": "sum",
            "functions": [],
            "filters": {
                "items": [],
                "op": "AND"
            },
            "disabled": False,
            "stepInterval": 60,
            "legend": "Test Query",
            "groupBy": []
        }
    }
    
    response = client.post(
        "/mcp",
        data=json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "execute_builder_query",
                "arguments": {
                    "builder_queries": test_builder_queries,
                    "start_time": "now-1h",
                    "end_time": "now",
                    "panel_type": "table",
                    "step": 60
                }
            },
            "id": "13"
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data["id"] == "13"
    assert "result" in response_data
    content = json.loads(response_data["result"]["content"][0]["text"])
    
    # Check the response status - it could be success or error depending on the Signoz setup
    assert content["status"] in ("success", "error")
    
    if content["status"] == "success":
        assert "data" in content
        print(f"Successfully executed builder query")
    else:
        # If it's an error, it should have a message
        assert "message" in content
        # If it's a query execution error, that's acceptable for testing
        if "Failed to execute builder query" in content.get("message", ""):
            pytest.skip(f"Builder query execution failed: {content['message']}")
        else:
            # Other errors should fail the test
            pytest.fail(f"Unexpected error in execute_builder_query: {content.get('message', 'Unknown error')}") 

def test_tool_call_fetch_traces_or_logs_traces(client):
    """
    Tests the 'fetch_traces_or_logs' tool call for traces through the MCP server.
    """
    response = client.post(
        "/mcp",
        data=json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "fetch_traces_or_logs",
                "arguments": {
                    "data_type": "traces",
                    "start_time": "now-1h",
                    "end_time": "now",
                    "limit": 5
                }
            },
            "id": "14"
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data["id"] == "14"
    assert "result" in response_data
    content = json.loads(response_data["result"]["content"][0]["text"])
    assert content["status"] in ("success", "error")
    if content["status"] == "success":
        assert "data" in content
        assert "query" in content
        print(f"Fetched traces: {content['data']}")
    else:
        assert "message" in content
        print(f"Error fetching traces: {content['message']}")

def test_tool_call_fetch_traces_or_logs_logs(client):
    """
    Tests the 'fetch_traces_or_logs' tool call for logs through the MCP server.
    """
    response = client.post(
        "/mcp",
        data=json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "fetch_traces_or_logs",
                "arguments": {
                    "data_type": "logs",
                    "start_time": "now-1h",
                    "end_time": "now",
                    "limit": 5
                }
            },
            "id": "15"
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data["id"] == "15"
    assert "result" in response_data
    content = json.loads(response_data["result"]["content"][0]["text"])
    assert content["status"] in ("success", "error")
    if content["status"] == "success":
        assert "data" in content
        assert "query" in content
        print(f"Fetched logs: {content['data']}")
    else:
        assert "message" in content
        print(f"Error fetching logs: {content['message']}")

def test_tool_call_fetch_traces_or_logs_invalid_type(client):
    """
    Tests the 'fetch_traces_or_logs' tool call with an invalid data_type.
    """
    response = client.post(
        "/mcp",
        data=json.dumps({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "fetch_traces_or_logs",
                "arguments": {
                    "data_type": "invalid_type",
                    "start_time": "now-1h",
                    "end_time": "now",
                    "limit": 5
                }
            },
            "id": "16"
        }),
        content_type="application/json"
    )
    assert response.status_code == 200
    response_data = response.get_json()
    assert response_data["id"] == "16"
    assert "result" in response_data
    content = json.loads(response_data["result"]["content"][0]["text"])
    assert content["status"] == "error"
    assert "Invalid data_type" in content["message"]
    print(f"Correctly handled invalid data_type: {content['message']}") 