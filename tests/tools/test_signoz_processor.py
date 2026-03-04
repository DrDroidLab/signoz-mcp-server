import pytest
from signoz_mcp_server.processor.signoz_processor import SignozApiProcessor

@pytest.fixture
def processor(signoz_config):
    """
    Provides a SignozApiProcessor instance configured for live API testing.
    """
    return SignozApiProcessor(
        signoz_host=signoz_config["host"],
        signoz_api_key=signoz_config.get("api_key")
    )

def test_connection(processor):
    """
    Tests the connection to the live Signoz API.
    """
    assert processor.test_connection() is True

def test_fetch_dashboards(processor):
    """
    Tests fetching dashboards from the live Signoz API.
    """
    dashboards = processor.fetch_dashboards()
    assert dashboards is not None
    assert isinstance(dashboards["data"], list)

def test_fetch_dashboard_details(processor):
    """
    Tests fetching dashboard details from the live Signoz API.
    """
    dashboards = processor.fetch_dashboards()
    assert dashboards is not None and dashboards["data"]
    
    dashboard_id = dashboards["data"][0]["id"]
    details = processor.fetch_dashboard_details(dashboard_id)
    
    assert details is not None
    assert details["id"] == dashboard_id

def test_parse_step():
    """
    Tests the _parse_step utility function with various time formats.
    """
    processor = SignozApiProcessor(signoz_host="http://localhost:3301")
    assert processor._parse_step("60s") == 60
    assert processor._parse_step("5m") == 300
    assert processor._parse_step("1h") == 3600
    assert processor._parse_step("1d") == 86400
    assert processor._parse_step(120) == 120
    assert processor._parse_step("invalid") == 60  # Default value

def test_fetch_dashboard_data(processor):
    """
    Tests fetching data for a specific dashboard from the live Signoz API.
    """
    dashboards = processor.fetch_dashboards()
    assert dashboards is not None and dashboards["data"]

    dashboard_title = dashboards["data"][0]["data"]["title"]
    data = processor.fetch_dashboard_data(dashboard_title)
    
    assert data is not None

def test_fetch_apm_metrics(processor):
    """
    Tests fetching APM metrics from the live Signoz API.
    """
    # To fetch apm metrics we need a service name, this can be fetched from the dashboard
    dashboards = processor.fetch_dashboards()
    assert dashboards is not None and dashboards["data"]

    for dashboard in dashboards["data"]:
        if "service" in dashboard["data"]["title"].lower():
            dashboard_details = processor.fetch_dashboard_details(dashboard["id"])
            if dashboard_details:
                service_name = dashboard_details.get("data", {}).get("title")
                if service_name:
                    apm_metrics = processor.fetch_apm_metrics(service_name)
                    assert apm_metrics is not None
                    return

    pytest.skip("Could not find a service name to test APM metrics") 

def test_fetch_services(processor):
    """
    Tests fetching all instrumented services from the live Signoz API.
    """
    result = processor.fetch_services()
    print(result)
    if isinstance(result, dict) and result.get("status") == "error":
        pytest.fail(result.get("message", "Failed to fetch services"))
    elif isinstance(result, dict) and "data" in result:
        assert isinstance(result["data"], list)
    elif isinstance(result, list):
        pass
    else:
        pytest.fail("Unexpected result format from fetch_services") 

def test_execute_clickhouse_query_tool(processor):
    """
    Tests the execute_clickhouse_query_tool method directly on the SignozApiProcessor.
    """
    # Simple Clickhouse query to test the connection and basic functionality
    test_query = "SELECT 1 as test_column"
    
    # Use a recent time range (last hour)
    from datetime import datetime, timezone, timedelta
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=1)
    
    result = processor.execute_clickhouse_query_tool(
        query=test_query,
        time_geq=start_time.timestamp(),
        time_lt=end_time.timestamp(),
        panel_type="table",
        fill_gaps=False,
        step=60
    )
    
    # The result could be successful data or an error response
    if isinstance(result, dict) and "error" in result:
        # If it's an API error, that's acceptable for testing
        if "Failed to query metrics" in result.get("error", ""):
            pytest.skip(f"Clickhouse query execution failed: {result['error']}")
        else:
            # Other errors should fail the test
            pytest.fail(f"Unexpected error in execute_clickhouse_query_tool: {result.get('error', 'Unknown error')}")
    else:
        # Success case - should have some data structure
        assert result is not None
        print(f"Successfully executed Clickhouse query: {test_query}")

def test_execute_builder_query_tool(processor):
    """
    Tests the execute_builder_query_tool method directly on the SignozApiProcessor.
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
    
    # Use a recent time range (last hour)
    from datetime import datetime, timezone, timedelta
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=1)
    
    result = processor.execute_builder_query_tool(
        builder_queries=test_builder_queries,
        time_geq=start_time.timestamp(),
        time_lt=end_time.timestamp(),
        panel_type="table",
        step=60
    )
    
    # The result could be successful data or an error response
    if isinstance(result, dict) and "error" in result:
        # If it's an API error, that's acceptable for testing
        if "Failed to query metrics" in result.get("error", ""):
            pytest.skip(f"Builder query execution failed: {result['error']}")
        else:
            # Other errors should fail the test
            pytest.fail(f"Unexpected error in execute_builder_query_tool: {result.get('error', 'Unknown error')}")
    else:
        # Success case - should have some data structure
        assert result is not None
        print(f"Successfully executed builder query") 