import pytest
import os
from jit_mcp.registry import MCPRegistry, ToolMetadata

@pytest.fixture
def temp_registry(tmp_path):
    db_path = str(tmp_path / "test_mcp_registry")
    registry = MCPRegistry(db_path=db_path)
    return registry

@pytest.mark.asyncio
async def test_add_and_search_tool(temp_registry):
    tool = ToolMetadata(
        name="test_tool",
        description="A tool for testing purposes.",
        uri="mcp://test",
        category="Test"
    )
    await temp_registry.add_tool(tool)
    
    results = await temp_registry.search_semantic("testing purposes")
    assert len(results) > 0
    assert results[0]["id"] == "test_tool"

@pytest.mark.asyncio
async def test_get_tool_uri(temp_registry):
    tool = ToolMetadata(
        name="test_tool",
        description="A tool for testing purposes.",
        uri="mcp://test",
        category="Test"
    )
    await temp_registry.add_tool(tool)
    uri = await temp_registry.get_tool_uri("test_tool")
    assert uri == "mcp://test"
