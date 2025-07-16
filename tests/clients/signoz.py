import json
import uuid
from typing import Any, Dict, List


class SignozMCPClient:
    def __init__(self, test_client: Any, api_key: str = "test-key"):
        self.test_client = test_client
        self.api_key = api_key
        self._initialize()

    def _handle_response(self, response):
        """Handle Flask's test response."""
        result = response.get_json()
        if response.status_code >= 400:
            error_message = result.get("error", {}).get("message", str(result))
            raise Exception(
                f"Request failed with status {response.status_code}: {error_message}"
            )
        return result

    def _initialize(self):
        """Initialize the MCP session."""
        payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {"protocolVersion": "2025-06-18"},
            "id": str(uuid.uuid4()),
        }
        response = self.test_client.post("/mcp", json=payload)
        result = self._handle_response(response)
        if "error" in result:
            raise Exception(f"Initialization failed: {result['error']}")

    def _send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request to the server."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": str(uuid.uuid4()),
        }
        response = self.test_client.post("/mcp", json=payload)
        result = self._handle_response(response)
        if "error" in result:
            raise Exception(
                f"API call failed for method {method}: {result['error']['message']}"
            )
        return result["result"]

    def list_tools(self) -> List[Dict[str, Any]]:
        """Fetch and format tools from the MCP server."""
        result = self._send_request("tools/list", {})
        return result.get("tools", [])

    def execute_tool(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool on the MCP server."""
        params = {"name": tool_name, "arguments": parameters}
        result = self._send_request("tools/call", params)
        content = result.get("content", [])
        if content and isinstance(content, list) and "text" in content[0]:
            return json.loads(content[0]["text"])
        return result

    def close_session(self):
        """No-op for test client."""
        pass 