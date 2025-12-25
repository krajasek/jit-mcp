from typing import List, Dict, Any

class DynamicContextManager:
    def __init__(self) -> None:
        self.active_tools: List[Dict[str, Any]] = []
        self.candidate_tools: List[Dict[str, Any]] = []

    def set_candidates(self, tools: List[Dict[str, Any]]) -> None:
        """Sets the list of candidate tools found during search."""
        self.candidate_tools = tools

    def hydrate_tools(self, tool_names: List[str], full_schemas: List[Dict[str, Any]]) -> None:
        """Loads the full schemas for the confirmed tools."""
        # Simple implementation: replace candidates with full schemas
        self.active_tools = full_schemas

    def get_system_prompt_extension(self) -> str:
        """Returns a prompt extension describing available tool categories or candidates."""
        if not self.candidate_tools and not self.active_tools:
            return "Available tool categories: Financial, Admin, Search, Code, Social. Request tools if needed."
        
        if self.candidate_tools and not self.active_tools:
            tool_list = ", ".join([t["id"] for t in self.candidate_tools])
            return f"I found these potential tools: {tool_list}. Shall I load them?"

        return ""

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Returns the full JSON-RPC schemas for the active tools."""
        return self.active_tools
