import json
from typing import Any, Optional

from openai import OpenAI
from tests.clients.signoz import SignozMCPClient


class OpenAIMCPClient:
    def __init__(
        self,
        test_client: Any,
        openai_api_key: Optional[str],
        mcp_api_key: str = "test-key",
    ):
        """
        Initialize the OpenAI-MCP Client for testing.
        """
        if not openai_api_key:
            raise ValueError("OpenAI API key must be provided for testing.")

        self.openai_client = OpenAI(api_key=openai_api_key)
        self.mcp_client = SignozMCPClient(
            test_client=test_client, api_key=mcp_api_key
        )
        self.mcp_tools = self._get_mcp_tools()

    def _get_mcp_tools(self):
        """Fetch and format tools from the MCP server."""
        try:
            mcp_tools_raw = self.mcp_client.list_tools()
            formatted_tools = []
            for tool in mcp_tools_raw:
                tool_name = tool.get("name")
                if isinstance(tool_name, str):
                    formatted_tools.append(
                        {
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "description": tool.get("description"),
                                "parameters": tool.get(
                                    "parameters", {"type": "object", "properties": {}}
                                ),
                            },
                        }
                    )
            return formatted_tools
        except Exception as e:
            print(f"Failed to fetch or format MCP tools: {e}")
            return []

    def chat(self, messages: list, model: str = "gpt-4o", **kwargs):
        """
        Send a chat request to OpenAI, handling MCP tool calls. Only non-streaming mode is supported: returns the full response as a string.
        """
        completion = self.openai_client.chat.completions.create(
            model=model,
            messages=messages,
            tools=self.mcp_tools,
            tool_choice="auto",
            stream=False,
            temperature=0,
            **kwargs,
        )
        content = ""
        tool_calls = None
        for choice in completion.choices:
            if hasattr(choice, "message") and choice.message:
                if choice.message.content:
                    content += choice.message.content
                if hasattr(choice.message, "tool_calls") and choice.message.tool_calls:
                    tool_calls = choice.message.tool_calls
        if not tool_calls:
            return content
        # If there are tool calls, execute them and get the final response
        messages.append({"role": "assistant", "tool_calls": [tc.to_dict() for tc in tool_calls]})
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            try:
                tool_result = self.mcp_client.execute_tool(
                    tool_name=function_name, parameters=function_args
                )
            except Exception as e:
                tool_result = {"error": str(e)}
            messages.append(
                {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(tool_result),
                }
            )
        # Get the final response after tool call(s)
        completion2 = self.openai_client.chat.completions.create(
            model=model, messages=messages, stream=False, temperature=0, **kwargs
        )
        final_content = ""
        for choice in completion2.choices:
            if hasattr(choice, "message") and choice.message and choice.message.content:
                final_content += choice.message.content
        print("final_content", final_content)
        return final_content

    def close(self):
        """Close the client session."""
        self.mcp_client.close_session() 