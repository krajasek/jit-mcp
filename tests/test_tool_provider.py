import pytest
from jit_mcp.tool_provider import JITToolProvider, create_discover_tool_schema
from jit_mcp.registry import ToolMetadata


@pytest.fixture
def temp_provider(tmp_path):
    db_path = str(tmp_path / "test_mcp_registry")
    return JITToolProvider(db_path=db_path)


class TestJITToolProvider:
    @pytest.mark.asyncio
    async def test_add_and_discover(self, temp_provider):
        """Test that tools can be added and discovered."""
        tool = ToolMetadata(
            name="test_finance",
            description="Get stock prices and financial data",
            uri="mcp+stdio://echo/test",
            category="Financial"
        )
        await temp_provider.add_tool(tool)

        results = await temp_provider.discover("stock prices")
        assert len(results) > 0
        assert results[0]["name"] == "test_finance"

    @pytest.mark.asyncio
    async def test_discover_no_results(self, temp_provider):
        """Test discovery with no matching tools."""
        results = await temp_provider.discover("nonexistent capability")
        assert results == []

    def test_get_active_tools_empty(self, temp_provider):
        """Test that active tools is empty initially."""
        assert temp_provider.get_active_tools() == []
        assert temp_provider.get_active_tool_names() == []

    def test_is_hydrated_false(self, temp_provider):
        """Test that is_hydrated returns False for unknown tools."""
        assert not temp_provider.is_hydrated("unknown_tool")

    def test_clear_tools(self, temp_provider):
        """Test clearing active tools."""
        # Manually add to cache for testing
        temp_provider._active_tools["test"] = ({"name": "test"}, None)
        temp_provider._hydrated_uris.add("test://uri")

        temp_provider.clear_tools()

        assert temp_provider.get_active_tools() == []
        assert len(temp_provider._hydrated_uris) == 0

    @pytest.mark.asyncio
    async def test_execute_not_hydrated(self, temp_provider):
        """Test that executing non-hydrated tool raises KeyError."""
        with pytest.raises(KeyError) as exc_info:
            await temp_provider.execute("unknown_tool", {})

        assert "not found" in str(exc_info.value)
        assert "discover_and_hydrate" in str(exc_info.value)

    def test_map_uri_to_params(self, temp_provider):
        """Test URI to StdioServerParameters mapping."""
        # Test mcp+stdio:// format
        params = temp_provider._map_uri_to_params("mcp+stdio://npx/-y/@mcp/server")
        assert params.command == "npx"
        assert params.args == ["-y", "@mcp", "server"]

        # Test mcp:// format
        params = temp_provider._map_uri_to_params("mcp://python/server.py")
        assert params.command == "python"
        assert params.args == ["server.py"]

        # Test plain path
        params = temp_provider._map_uri_to_params("node/index.js")
        assert params.command == "node"
        assert params.args == ["index.js"]

    def test_map_uri_to_params_disallowed_command(self, temp_provider):
        """Test that disallowed commands raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            temp_provider._map_uri_to_params("mcp+stdio://rm/-rf/--no-preserve-root//")

        assert "not in the allowed commands list" in str(exc_info.value)
        assert "rm" in str(exc_info.value)

    def test_map_uri_to_params_allowed_commands(self, temp_provider):
        """Test that all expected commands are allowed."""
        allowed = ["npx", "node", "python", "python3", "uvx", "uv", "echo", "docker", "deno", "bun"]
        for cmd in allowed:
            params = temp_provider._map_uri_to_params(f"mcp+stdio://{cmd}/arg")
            assert params.command == cmd


class TestDiscoverToolSchema:
    def test_schema_structure(self):
        """Test that the discover tool schema is valid."""
        schema = create_discover_tool_schema()

        assert schema["name"] == "discover_tools"
        assert "description" in schema
        assert "input_schema" in schema

        input_schema = schema["input_schema"]
        assert input_schema["type"] == "object"
        assert "query" in input_schema["properties"]
        assert "query" in input_schema["required"]

    def test_schema_has_n_results(self):
        """Test that n_results parameter is present."""
        schema = create_discover_tool_schema()
        props = schema["input_schema"]["properties"]

        assert "n_results" in props
        assert props["n_results"]["type"] == "integer"
