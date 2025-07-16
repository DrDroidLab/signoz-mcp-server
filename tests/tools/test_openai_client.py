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

