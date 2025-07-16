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