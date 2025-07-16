import pytest
from tests.clients.openai import OpenAIMCPClient
from tests.conftest import assert_response_quality

# Mark all tests in this file as 'integration'
pytestmark = pytest.mark.integration

# Test data for parameterized testing
test_models = ["gpt-4.1"]
service_queries = [
    "Fetch all services from SigNoz.",
    "Show me the available services.", 
    "List all services in SigNoz.",
]
connection_queries = [
    "Test the connection to SigNoz.",
    "Check SigNoz connection status.",
    "Verify connection to SigNoz.",
]
dashboard_queries = [
    "Fetch all available dashboards from SigNoz.",
    "Show me the dashboards.",
    "List all dashboards available.",
]

@pytest.fixture(scope="module")
def mcp_client(openai_api_key, client):
    """Fixture to create an OpenAIMCPClient instance for testing."""
    if not openai_api_key:
        pytest.skip("OpenAI API key not available")

    mcp_client_instance = OpenAIMCPClient(
        test_client=client,
        openai_api_key=openai_api_key,
    )
    yield mcp_client_instance
    mcp_client_instance.close()

@pytest.mark.parametrize("model", test_models)
@pytest.mark.parametrize("query", service_queries)
@pytest.mark.flaky(max_runs=3)
@pytest.mark.pass_rate(0.8)
def test_fetch_services_robust(mcp_client, evaluator, model, query):
    """Test fetching services using LLM evaluation."""
    messages = [{"role": "user", "content": query}]
    response = mcp_client.chat(messages=messages, model=model)

    assert_response_quality(
        prompt=query,
        response=response,
        evaluator=evaluator,
        min_pass_rate=0.8,
        specific_checks=["services_info"],
        required_checks=["is_helpful"]
    )

@pytest.mark.parametrize("model", test_models)
@pytest.mark.parametrize("query", connection_queries)
@pytest.mark.flaky(max_runs=3)
@pytest.mark.pass_rate(0.8)
def test_connection_status_robust(mcp_client, evaluator, model, query):
    """Test connection status using LLM evaluation."""
    messages = [{"role": "user", "content": query}]
    response = mcp_client.chat(messages=messages, model=model)

    assert_response_quality(
        prompt=query,
        response=response,
        evaluator=evaluator,
        min_pass_rate=0.8,
        specific_checks=["connection_status"],
        required_checks=["is_helpful"]
    )

@pytest.mark.parametrize("model", test_models)
@pytest.mark.parametrize("query", dashboard_queries)
@pytest.mark.flaky(max_runs=3)
@pytest.mark.pass_rate(0.8)
def test_fetch_dashboards_robust(mcp_client, evaluator, model, query):
    """Test fetching dashboards using LLM evaluation."""
    messages = [{"role": "user", "content": query}]
    response = mcp_client.chat(messages=messages, model=model)

    assert_response_quality(
        prompt=query,
        response=response,
        evaluator=evaluator,
        min_pass_rate=0.8,
        specific_checks=["dashboard_info"],
        required_checks=["is_helpful"]
    )

@pytest.mark.parametrize("model", test_models)
@pytest.mark.flaky(max_runs=3)
@pytest.mark.pass_rate(0.8)
def test_fetch_dashboard_data_python(mcp_client, evaluator, model):
    """Test fetching Python Microservices dashboard data."""
    query = "Fetch data for the Python Microservices dashboard from SigNoz."
    messages = [{"role": "user", "content": query}]
    response = mcp_client.chat(messages=messages, model=model)

    assert_response_quality(
        prompt=query,
        response=response,
        evaluator=evaluator,
        min_pass_rate=0.8,
        specific_checks=["dashboard_data:Python Microservices"],
        required_checks=["is_helpful"]
    )

@pytest.mark.parametrize("model", test_models)
@pytest.mark.flaky(max_runs=3)
@pytest.mark.pass_rate(0.8)
def test_fetch_dashboard_data_go_with_duration(mcp_client, evaluator, model):
    """Test fetching Go Microservices dashboard data with duration."""
    query = "Fetch data for the Go Microservices dashboard for the last 12 hours."
    messages = [{"role": "user", "content": query}]
    response = mcp_client.chat(messages=messages, model=model)

    assert_response_quality(
        prompt=query,
        response=response,
        evaluator=evaluator,
        min_pass_rate=0.8,
        specific_checks=["dashboard_data:Go Microservices"],
        required_checks=["is_helpful"]
    )

@pytest.mark.parametrize("model", test_models)
@pytest.mark.flaky(max_runs=3)
@pytest.mark.pass_rate(0.8)
def test_fetch_apm_metrics_recommendation_service(mcp_client, evaluator, model):
    """Test fetching APM metrics for recommendation service."""
    query = "Fetch APM metrics for the service 'recommendationservice' from SigNoz."
    messages = [{"role": "user", "content": query}]
    response = mcp_client.chat(messages=messages, model=model)

    assert_response_quality(
        prompt=query,
        response=response,
        evaluator=evaluator,
        min_pass_rate=0.8,
        specific_checks=["apm_metrics:recommendationservice"],
        required_checks=["is_helpful"]
    )

@pytest.mark.parametrize("model", test_models)
@pytest.mark.flaky(max_runs=3)
@pytest.mark.pass_rate(0.8)
def test_fetch_apm_metrics_with_duration(mcp_client, evaluator, model):
    """Test fetching APM metrics with time duration."""
    query = "Fetch APM metrics for the 'recommendationservice' service in the last 24 hours."
    messages = [{"role": "user", "content": query}]
    response = mcp_client.chat(messages=messages, model=model)
    
    assert_response_quality(
        prompt=query,
        response=response,
        evaluator=evaluator,
        min_pass_rate=0.8,
        specific_checks=["apm_metrics:recommendationservice"],
        required_checks=["is_helpful"]
    )

@pytest.mark.flaky(max_runs=3)
@pytest.mark.pass_rate(0.7)
def test_comprehensive_signoz_interaction(mcp_client, evaluator):
    """Comprehensive test that checks multiple interactions in sequence."""
    
    interactions = [
        ("Test the connection to SigNoz.", ["connection_status"]),
        ("Fetch all services from SigNoz.", ["services_info"]),
        ("Fetch all available dashboards from SigNoz.", ["dashboard_info"]),
        ("Fetch data for the Python Microservices dashboard.", ["dashboard_data:Python Microservices"]),
        ("Fetch APM metrics for the 'recommendationservice' service.", ["apm_metrics:recommendationservice"]),
    ]
    
    for query, checks in interactions:
        messages = [{"role": "user", "content": query}]
        response = mcp_client.chat(messages=messages, model="gpt-4o")
        
        assert_response_quality(
            prompt=query,
            response=response,
            evaluator=evaluator,
            min_pass_rate=0.8,
            specific_checks=checks,
            required_checks=["is_helpful"]
        )

# --- NEW TESTS FOR ADDITIONAL TOOLS ---

@pytest.mark.parametrize("model", test_models)
@pytest.mark.flaky(max_runs=3)
@pytest.mark.pass_rate(0.8)
def test_fetch_dashboard_details_robust(mcp_client, evaluator, model):
    """Test fetching dashboard details for a specific dashboard ID."""
    # Use a generic dashboard ID; in real test, replace with a valid one if available
    dashboard_id = "01980876-e99c-7ccb-ae10-35fd656c67d5"
    query = f"Show me details for the dashboard with ID '{dashboard_id}'."
    messages = [{"role": "user", "content": query}]
    response = mcp_client.chat(messages=messages, model=model)

    assert_response_quality(
        prompt=query,
        response=response,
        evaluator=evaluator,
        min_pass_rate=0.8,
        specific_checks=[f"dashboard_details:{dashboard_id}"],
        required_checks=["is_helpful"]
    )

@pytest.mark.parametrize("model", test_models)
@pytest.mark.flaky(max_runs=3)
@pytest.mark.pass_rate(0.8)
def test_execute_clickhouse_query_robust(mcp_client, evaluator, model):
    """Test executing a Clickhouse SQL query."""
    query = "Run a Clickhouse SQL query to count the number of traces in the last hour."
    messages = [{"role": "user", "content": query}]
    response = mcp_client.chat(messages=messages, model=model)

    assert_response_quality(
        prompt=query,
        response=response,
        evaluator=evaluator,
        min_pass_rate=0.8,
        specific_checks=["clickhouse_query_result"],
        required_checks=["is_helpful"]
    )

@pytest.mark.parametrize("model", test_models)
@pytest.mark.flaky(max_runs=3)
@pytest.mark.pass_rate(0.8)
def test_execute_builder_query_robust(mcp_client, evaluator, model):
    """Test executing a builder query for request rate grouped by service."""
    query = "Run a builder query to show the request rate grouped by service for the last 2 hours."
    messages = [{"role": "user", "content": query}]
    response = mcp_client.chat(messages=messages, model=model)

    assert_response_quality(
        prompt=query,
        response=response,
        evaluator=evaluator,
        min_pass_rate=0.8,
        specific_checks=["builder_query_result"],
        required_checks=["is_helpful"]
    )

@pytest.mark.parametrize("model", test_models)
@pytest.mark.flaky(max_runs=3)
@pytest.mark.pass_rate(0.8)
def test_fetch_traces_or_logs_robust(mcp_client, evaluator, model):
    """Test fetching traces from SigNoz (logs part skipped due to schema mismatch)."""
    # Test for traces with a specific service name
    service_name = "recommendationservice"
    query_traces = f"Fetch the latest traces from SigNoz for {service_name}"
    messages_traces = [{"role": "user", "content": query_traces}]
    response_traces = mcp_client.chat(messages=messages_traces, model=model)
    assert_response_quality(
        prompt=query_traces,
        response=response_traces,
        evaluator=evaluator,
        min_pass_rate=0.8,
        specific_checks=["traces_info"],
        required_checks=["is_helpful"]
    )
    # Skipping logs part due to missing 'resource_attributes' column in logs table.
    # query_logs = f"Fetch the latest logs from SigNoz for {service_name}"
    # messages_logs = [{"role": "user", "content": query_logs}]
    # response_logs = mcp_client.chat(messages=messages_logs, model=model)
    # assert_response_quality(
    #     prompt=query_logs,
    #     response=response_logs,
    #     evaluator=evaluator,
    #     min_pass_rate=0.8,
    #     specific_checks=["logs_info"],
    #     required_checks=["is_helpful"]
    # )

