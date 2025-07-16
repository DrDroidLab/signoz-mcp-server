import json
import pytest

def test_test_connection_prompt(client):
    """
    Tests that a prompt to test the connection results in a call to the 'test_connection' tool.
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