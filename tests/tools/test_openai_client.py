import json
from unittest.mock import patch

import pytest

from tests.clients.openai import OpenAIMCPClient

# Mark all tests in this file as 'integration'
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def mcp_client(openai_api_key, client):
    """Fixture to create an OpenAIMCPClient instance for testing."""
    mcp_client_instance = OpenAIMCPClient(
        test_client=client,
        openai_api_key=openai_api_key,
    )
    yield mcp_client_instance
    mcp_client_instance.close()


def test_fetch_all_services(mcp_client):
    """Test a successful tool call using the Flask test client."""
    messages = [
        {"role": "user", "content": "Fetch all services from SigNoz."}
    ]
    response = mcp_client.chat(messages=messages)

    assert "Recommendation Service" in response
    assert "Shipping Service" in response
    assert "Email Service" in response


def test_test_connection(mcp_client):
    """Test the test_connection tool call."""
    messages = [{"role": "user", "content": "Test the connection to SigNoz."}]
    response = mcp_client.chat(messages=messages)

    assert "success" in response
    assert "host" in response
    assert "SSL verification" in response


def test_fetch_dashboards(mcp_client):
    """Test the fetch_dashboards tool call."""
    messages = [{"role": "user", "content": "Fetch all available dashboards from SigNoz."}]
    response = mcp_client.chat(messages=messages)

    assert "Python Microservices" in response
    assert "Go Microservices" in response


def test_fetch_dashboard_data(mcp_client):
    """Test the fetch_dashboard_data tool call."""
    messages = [{"role": "user", "content": "Fetch data for the Python Microservices dashboard."}]
    response = mcp_client.chat(messages=messages)

    assert "Python Microservices" in response
    assert "Total Calls" in response
    assert "Latencies" in response
    assert "Traces by Service" in response


def test_fetch_dashboard_data_with_duration(mcp_client):
    """Test fetch_dashboard_data with a duration."""
    messages = [{"role": "user", "content": "Fetch data for the Go Microservices dashboard for the last 12 hours."}]
    response = mcp_client.chat(messages=messages)

    assert "Go Microservices" in response
    assert "Total Requests" in response
    assert "Traces by Service" in response


def test_fetch_apm_metrics(mcp_client):
    """Test the fetch_apm_metrics tool call."""
    messages = [{"role": "user", "content": "Fetch APM metrics for the 'recommendationservice' service."}]
    response = mcp_client.chat(messages=messages)

    assert 'recommendationservice' in response
    assert '99th Percentile Duration (p99):' in response
    assert 'Call Rate:' in response
    assert 'Error Rate:' in response
    assert 'Number of 4XX Responses:' in response


def test_fetch_apm_metrics_with_duration(mcp_client):
    """Test fetch_apm_metrics with duration."""
    messages = [{"role": "user", "content": "Fetch APM metrics for the 'recommendationservice' service in the last 24 hours."}]
    response = mcp_client.chat(messages=messages)
    
    assert 'recommendationservice' in response
    assert '99th Percentile Duration (p99):' in response
    assert 'Call Rate:' in response
    assert 'Error Rate:' in response
    assert 'Number of 4XX Responses:' in response

