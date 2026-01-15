import logging
from typing import Dict, List, Any, Optional, Tuple
from mcp import StdioServerParameters

from jit_mcp.registry import MCPRegistry, ToolMetadata
from jit_mcp.search import SearchService
from jit_mcp.mcp_client import MCPClient

logger = logging.getLogger(__name__)

# Allowlist of commands that can be executed via MCP stdio
ALLOWED_COMMANDS = frozenset({
    "npx", "node", "python", "python3", "uvx", "uv", "echo",
    "docker", "deno", "bun"
})


class JITToolProvider:
    """
    Provides just-in-time tool discovery and execution for external agents.

    This class enables Pattern 3 (Dynamic Tool Injection) where an agent can:
    1. Start with a single "discover_tools" capability
    2. Discover and hydrate relevant MCP tools on-demand
    3. Have those tools injected into its available tool set
    4. Execute the hydrated tools directly
    """

    def __init__(self, db_path: str = "./mcp_registry"):
        self.registry = MCPRegistry(db_path)
        self.search_service = SearchService(self.registry)
        self.mcp_client = MCPClient()

        # Cache: tool_name -> (schema, server_params)
        self._active_tools: Dict[str, Tuple[Dict[str, Any], StdioServerParameters]] = {}

        # Track which URIs we've already connected to
        self._hydrated_uris: set[str] = set()

    async def add_tool(self, tool: ToolMetadata) -> None:
        """Register a tool in the registry."""
        await self.registry.add_tool(tool)

    async def discover(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for tools matching the query without hydrating them.
        Returns lightweight tool metadata for preview.
        """
        candidates = await self.search_service.search(query, n_results=n_results)
        return [
            {
                "name": c["id"],
                "description": c.get("document", ""),
                "category": c.get("metadata", {}).get("category", ""),
                "uri": c.get("metadata", {}).get("uri", ""),
            }
            for c in candidates
        ]

    async def discover_and_hydrate(
        self,
        query: str,
        n_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for tools and hydrate their full schemas from MCP servers.

        Returns a list of complete tool schemas ready for injection into
        an agent's tool set.
        """
        candidates = await self.search_service.search(query, n_results=n_results)

        if not candidates:
            logger.info(f"No tools found for query: {query}")
            return []

        hydrated_schemas: List[Dict[str, Any]] = []

        for candidate in candidates:
            uri = candidate.get("metadata", {}).get("uri", "")

            if not uri:
                logger.warning(f"Tool {candidate['id']} has no URI, skipping")
                continue

            # Skip if we've already hydrated this server
            if uri in self._hydrated_uris:
                # Return cached schemas for this server
                for name, (schema, _) in self._active_tools.items():
                    if schema not in hydrated_schemas:
                        hydrated_schemas.append(schema)
                continue

            try:
                server_params = self._map_uri_to_params(uri)
                schemas = await self.mcp_client.get_tool_schemas(server_params)

                for schema in schemas:
                    tool_name = schema["name"]
                    self._active_tools[tool_name] = (schema, server_params)
                    hydrated_schemas.append(schema)
                    logger.info(f"Hydrated tool: {tool_name}")

                self._hydrated_uris.add(uri)

            except Exception as e:
                logger.error(f"Failed to hydrate tools from {uri}: {e}")
                continue

        return hydrated_schemas

    async def hydrate_by_name(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """
        Hydrate a specific tool by name.
        Returns the tool schema if found and hydrated successfully.
        """
        uri = await self.registry.get_tool_uri(tool_name)

        if not uri:
            logger.warning(f"Tool {tool_name} not found in registry")
            return None

        try:
            server_params = self._map_uri_to_params(uri)
            schemas = await self.mcp_client.get_tool_schemas(server_params)

            for schema in schemas:
                self._active_tools[schema["name"]] = (schema, server_params)
                if schema["name"] == tool_name:
                    return schema

            self._hydrated_uris.add(uri)

        except Exception as e:
            logger.error(f"Failed to hydrate tool {tool_name}: {e}")

        return None

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Execute a previously hydrated tool.

        Raises:
            KeyError: If the tool has not been hydrated
        """
        if tool_name not in self._active_tools:
            raise KeyError(
                f"Tool '{tool_name}' not found. "
                f"Call discover_and_hydrate() first. "
                f"Active tools: {list(self._active_tools.keys())}"
            )

        schema, server_params = self._active_tools[tool_name]

        logger.debug(f"Executing tool: {tool_name} with args: {arguments}")
        result = await self.mcp_client.execute_tool(server_params, tool_name, arguments)

        return result

    def get_active_tools(self) -> List[Dict[str, Any]]:
        """Return all currently hydrated tool schemas."""
        return [schema for schema, _ in self._active_tools.values()]

    def get_active_tool_names(self) -> List[str]:
        """Return names of all currently hydrated tools."""
        return list(self._active_tools.keys())

    def is_hydrated(self, tool_name: str) -> bool:
        """Check if a tool has been hydrated."""
        return tool_name in self._active_tools

    def clear_tools(self) -> None:
        """Clear all hydrated tools from cache."""
        self._active_tools.clear()
        self._hydrated_uris.clear()
        logger.info("Cleared all active tools")

    def _map_uri_to_params(self, uri: str) -> StdioServerParameters:
        """
        Maps a tool URI to StdioServerParameters.

        Expected URI formats:
        - mcp+stdio://command/arg1/arg2
        - mcp+stdio://npx/-y/@modelcontextprotocol/server-name

        Raises:
            ValueError: If the command is not in ALLOWED_COMMANDS
        """
        # Strip protocol prefix
        if uri.startswith("mcp+stdio://"):
            path = uri[len("mcp+stdio://"):]
        elif uri.startswith("mcp://"):
            path = uri[len("mcp://"):]
        else:
            path = uri

        parts = path.split("/")
        command = parts[0] if parts else "echo"
        args = parts[1:] if len(parts) > 1 else []

        if command not in ALLOWED_COMMANDS:
            raise ValueError(
                f"Command '{command}' is not in the allowed commands list. "
                f"Allowed: {sorted(ALLOWED_COMMANDS)}"
            )

        return StdioServerParameters(command=command, args=args)


def create_discover_tool_schema() -> Dict[str, Any]:
    """
    Returns a tool schema for the discovery tool that agents can use
    to bootstrap their tool discovery.
    """
    return {
        "name": "discover_tools",
        "description": (
            "Search for and load MCP tools based on a capability description. "
            "Use this when you need a tool that isn't currently available. "
            "Describe what capability you need (e.g., 'read CSV files', "
            "'access stock prices', 'send emails') and relevant tools will "
            "be loaded and made available for use."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Description of the capability or tool you need"
                },
                "n_results": {
                    "type": "integer",
                    "description": "Maximum number of tools to discover (default: 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    }
