import pytest
import yaml
from src.signoz_mcp_server.processor.signoz_processor import SignozApiProcessor

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

@pytest.fixture
def client(app):
    """
    Provides a test client for the Flask application.
    """
    return app.test_client() 