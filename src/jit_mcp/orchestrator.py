import asyncio
import logging
from typing import List, Dict, Any, Optional
from mcp import StdioServerParameters

from jit_mcp.registry import MCPRegistry, ToolMetadata
from jit_mcp.search import SearchService
from jit_mcp.context_manager import DynamicContextManager
from jit_mcp.mcp_client import MCPClient
from jit_mcp.llm_provider import LLMProvider

logger = logging.getLogger(__name__)

class JITOrchestrator:
    def __init__(
        self, 
        db_path: str = "./mcp_registry", 
        model_name: str = "gemini-1.5-flash"
    ):
        self.registry = MCPRegistry(db_path)
        self.search_service = SearchService(self.registry)
        self.context_manager = DynamicContextManager()
        self.mcp_client = MCPClient()
        self.llm = LLMProvider(model_name=model_name)
        self.global_categories = ["Financial", "Admin", "Search", "Code", "Social", "FileOps"]

    async def add_tool_to_registry(self, tool: ToolMetadata) -> None:
        """Helper to register a tool."""
        await self.registry.add_tool(tool)

    async def query(self, user_text: str) -> str:
        """
        Production JIT Orchestration Flow.
        """
        logger.info(f"Processing query: {user_text}")

        # Step 1 & 2: Intent Detection via LLM
        intent = await self.llm.detect_intent(user_text, self.global_categories)
        logger.info(f"Intent detected: {intent}")

        if not intent.needs_tools:
            # Fallback to direct LLM response if no tools needed
            # (In a real system, you'd just return the LLM's direct answer)
            return "No tools needed. [Direct Answer Simulation]"

        # Step 3: Registry Search
        logger.info(f"Searching for tools matching: {intent.search_query}")
        candidates = await self.search_service.search(intent.search_query)
        self.context_manager.set_candidates(candidates)

        if not candidates:
            return f"I need tools for '{intent.search_query}' but couldn't find any in the registry."

        # Step 4 & 5: Hydration
        # For simplicity, we hydrate all candidates that the LLM might need.
        full_schemas = []
        for cand in candidates:
            uri = cand["metadata"]["uri"]
            # Parsing URI to StdioServerParameters (Assumption: mcp://command?arg=val)
            # For this production-grade example, we simulate stdio params.
            # In a real system, you'd map URI to actual server commands.
            server_params = self._map_uri_to_params(uri)
            
            try:
                schemas = await self.mcp_client.get_tool_schemas(server_params)
                full_schemas.extend(schemas)
            except Exception as e:
                logger.error(f"Failed to fetch schemas from {uri}: {e}")

        self.context_manager.hydrate_tools([c["id"] for c in candidates], full_schemas)

        # Step 6: Tool Calling & Execution
        logger.info(f"Hydrated {len(full_schemas)} tool definitions.")
        tool_calls = await self.llm.get_tool_calls(user_text, full_schemas)
        
        if not tool_calls:
            return "Intent confirmed tools, but model didn't generate any calls."

        # Execute Tool Calls
        results = []
        for call in tool_calls:
            # Assuming we can find the right server for the tool name
            # Real implementation would track which schema came from which server
            server_params = self._find_server_for_tool(call["name"], candidates)
            if server_params:
                res = await self.mcp_client.execute_tool(server_params, call["name"], call["args"])
                results.append(res)
        
        return f"Executed {len(tool_calls)} tools. Results: {results}"

    def _map_uri_to_params(self, uri: str) -> StdioServerParameters:
        """
        Maps a tool URI to StdioServerParameters.
        This is where production logic for server management lives.
        """
        # Mocking for demonstration: replace with real command mapping
        return StdioServerParameters(command="echo", args=["mock-server"])

    def _find_server_for_tool(self, tool_name: str, candidates: List[Dict[str, Any]]) -> Optional[StdioServerParameters]:
        # Implementation to link tool names back to their servers
        return self._map_uri_to_params("mcp://default")
