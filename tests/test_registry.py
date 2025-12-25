import pytest
from jit_mcp.registry import MCPRegistry, ToolMetadata

@pytest.fixture
def temp_registry(tmp_path):
    db_path = str(tmp_path / "test_mcp_registry")
    registry = MCPRegistry(db_path=db_path)
    return registry

def test_add_and_search_tool(temp_registry):
    tool = ToolMetadata(
        name="test_tool",
        description="A tool for testing purposes.",
        uri="mcp://test",
        category="Test"
    )
    temp_registry.add_tool(tool)
    
    results = temp_registry.search_semantic("testing purposes")
    assert len(results) > 0
    assert results[0]["id"] == "test_tool"

def test_get_tool_uri(temp_registry):
    tool = ToolMetadata(
        name="test_tool",
        description="A tool for testing purposes.",
        uri="mcp://test",
        category="Test"
    )
    temp_registry.add_tool(tool)
    uri = temp_registry.get_tool_uri("test_tool")
    assert uri == "mcp://test"

def test_search_by_category(temp_registry):
    tool1 = ToolMetadata(name="t1", description="d1", uri="u1", category="Cat1")
    tool2 = ToolMetadata(name="t2", description="d2", uri="u2", category="Cat2")
    temp_registry.add_tool(tool1)
    temp_registry.add_tool(tool2)
    
    cat1_tools = temp_registry.search_by_category("Cat1")
    assert len(cat1_tools) == 1
    assert cat1_tools[0]["id"] == "t1"
