from langchain_core.tools import tool


@tool
def test_tool(value: str) -> str:
    """Test tool used to verify the agentic tool-calling loop."""
    return f"Test tool received: {value}"


tools = [test_tool]
