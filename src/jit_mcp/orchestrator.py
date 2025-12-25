from jit_mcp.registry import MCPRegistry, ToolMetadata
from jit_mcp.search import SearchService
from jit_mcp.context_manager import DynamicContextManager
from jit_mcp.mcp_client import MCPClient

class JITOrchestrator:
    def __init__(self, db_path: str = "./mcp_registry"):
        self.registry = MCPRegistry(db_path)
        self.search_service = SearchService(self.registry)
        self.context_manager = DynamicContextManager()
        self.mcp_client = MCPClient()
        self._initialize_registry()

    def _initialize_registry(self) -> None:
        # Seed with some mock data for demonstration
        self.registry.add_tool(ToolMetadata(
            name="google_calendar",
            description="Manage calendar events and schedules.",
            uri="mcp://calendar-server",
            category="Admin"
        ))
        self.registry.add_tool(ToolMetadata(
            name="csv_writer",
            description="Export data to CSV files.",
            uri="mcp://file-server",
            category="FileOps"
        ))

    def query(self, user_text: str) -> str:
        """
        Main entry point for a user query.
        This simulates the multi-step state machine.
        """
        print(f"\n[Step 1] User Query: {user_text}")
        
        # Step 2: Tool Intent (Simulated LLM thought)
        # In a real system, we'd call the LLM and parse its "Thought" block.
        print("[Step 2] Model Intent: Needs calendar and file writing tools.")
        search_query = "calendar and csv writing"
        
        # Step 3: Registry Search
        print(f"[Step 3] Searching Registry for: '{search_query}'")
        candidates = self.search_service.search(search_query)
        self.context_manager.set_candidates(candidates)
        
        # Step 4: Candidate Review (Simulated LLM confirmation)
        print(f"[Step 4] Candidates found: {[c['id'] for c in candidates]}")
        confirmed_tools = [c['id'] for c in candidates] # Assume LLM confirms all
        
        # Step 5: Hydration
        print("[Step 5] Hydrating full schemas...")
        full_schemas = []
        for name in confirmed_tools:
            uri = self.registry.get_tool_uri(name)
            if uri:
                schema = self.mcp_client.fetch_schema(name, uri)
                if schema:
                    full_schemas.append(schema)
        
        self.context_manager.hydrate_tools(confirmed_tools, full_schemas)
        
        # Step 6: Execution
        print("[Step 6] Execution Phase")
        tool_defs = self.context_manager.get_tool_definitions()
        return f"Successfully loaded {len(tool_defs)} tools: {[t['name'] for t in tool_defs]}"

if __name__ == "__main__":
    orchestrator = JITOrchestrator()
    result = orchestrator.query("I need to schedule a meeting and save the details to a CSV.")
    print(f"\nResult: {result}")
