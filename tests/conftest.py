import sys
print("sys.path", sys.path)
import pytest
import yaml
from src.signoz_mcp_server.processor.signoz_processor import SignozApiProcessor
import os

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
    from src.signoz_mcp_server.mcp_server import app as flask_app
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

    key = os.environ.get("OPENAI_API_KEY") or (
        config.get("openai", {}).get("api_key") if config else None
    )
    return key