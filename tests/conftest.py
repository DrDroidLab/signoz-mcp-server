import pytest
import yaml
from signoz_mcp_server.processor.signoz_processor import SignozApiProcessor
import os
from typing import Any, List, Optional

# Import our evaluation utilities
from tests.utils import SignozResponseEvaluator


@pytest.fixture(scope="session")
def signoz_config():
    """
    Loads the Signoz configuration from the YAML file.
    """
    with open("src/signoz_mcp_server/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    return config['signoz']

@pytest.fixture(scope="session")
def signoz_processor(signoz_config):
    """
    Provides a SignozApiProcessor instance configured for live API testing.
    """
    return SignozApiProcessor(
        signoz_host=signoz_config["host"],
        signoz_api_key=signoz_config.get("api_key"),
        ssl_verify=str(signoz_config.get("ssl_verify", "true"))
    )

@pytest.fixture(scope="session")
def app():
    """
    Provides a test instance of the Flask application.
    """
    from signoz_mcp_server.mcp_server import app as flask_app
    flask_app.config.update({"TESTING": True})
    return flask_app

@pytest.fixture(scope="module")
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope="session")
def openai_api_key():
    """Fixture to get the OpenAI API key."""
    config_path = os.path.join(
        os.path.dirname(__file__), "../src/signoz_mcp_server/config.yaml"
    )
    config = {}
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError:
            pass  # Ignore malformed config
    print("config", config)
    key = config.get("openai", {}).get("api_key") if config else None
    return key

@pytest.fixture(scope="module")
def evaluator(openai_api_key):
    """Fixture to create a SignozResponseEvaluator instance for testing."""
    if SignozResponseEvaluator is None:
        pytest.skip("langevals not available - install with: pip install 'langevals[openai]'")
    
    if not openai_api_key:
        pytest.skip("OpenAI API key required for evaluation")
    
    # Use gpt-4o-mini for cost-effective testing
    return SignozResponseEvaluator(model="gpt-4o-mini")

@pytest.fixture(scope="session", autouse=True)
def setup_environment():
    """Setup environment for testing."""

    config_path = "src/signoz_mcp_server/config.yaml"
    if os.path.exists(config_path):
        try:
            with open(config_path) as f:
                config = yaml.safe_load(f)
                openai_key = config.get("openai", {}).get("api_key")
                if openai_key:
                    os.environ["OPENAI_API_KEY"] = openai_key
        except yaml.YAMLError:
            pass

    yield

# Custom pytest markers for pass rate functionality
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "pass_rate(rate): mark test to require a minimum pass rate"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )

# Track test results for pass rate calculation
_test_results = {}

def pytest_runtest_logreport(report):
    """Collect test results for pass rate calculation."""
    if report.when == "call":
        test_id = report.nodeid
        
        # Extract pass_rate marker if present from the test item
        if hasattr(report, 'item') and hasattr(report.item, 'iter_markers'):
            pass_rate_marker = None
            for marker in report.item.iter_markers('pass_rate'):
                pass_rate_marker = marker
                break
            
            if pass_rate_marker:
                required_rate = pass_rate_marker.args[0] if pass_rate_marker.args else 0.8
                
                # Initialize tracking for this test group
                base_test_name = test_id.split('[')[0]  # Remove parametrization
                if base_test_name not in _test_results:
                    _test_results[base_test_name] = {
                        'required_rate': required_rate,
                        'results': []
                    }
                
                # Record result
                _test_results[base_test_name]['results'].append(report.outcome == 'passed')

def pytest_sessionfinish(session, exitstatus):
    """Check pass rates at the end of the session."""
    for test_name, data in _test_results.items():
        results = data['results']
        required_rate = data['required_rate']
        
        if results:
            actual_rate = sum(results) / len(results)
            if actual_rate < required_rate:
                print(f"\nWARNING: {test_name} pass rate {actual_rate:.2%} below required {required_rate:.2%}")
                print(f"  Passed: {sum(results)}/{len(results)} tests")

# Utility functions for test assertions
def assert_response_quality(
    prompt: str, 
    response: str, 
    evaluator: Any,
    min_pass_rate: float = 0.8,
    specific_checks: Optional[List[str]] = None,
    required_checks: Optional[List[str]] = None
) -> None:
    """
    Assert response quality using LLM evaluation.
    
    This is a convenience function that can be used in tests to evaluate
    response quality with multiple criteria.
    """
    if evaluator is None:
        pytest.skip("Evaluator not available")

    from tests.utils import evaluate_response_quality, assert_evaluation_passes

    results = evaluate_response_quality(
        prompt=prompt,
        response=response, 
        evaluator=evaluator,
        specific_checks=specific_checks
    )
    
    assert_evaluation_passes(
        evaluation_results=results,
        min_pass_rate=min_pass_rate,
        required_checks=required_checks
    )