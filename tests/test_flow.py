import pytest
from jit_mcp.context_manager import DynamicContextManager

def test_context_manager_hydration():
    cm = DynamicContextManager()
    candidates = [{"id": "tool1", "metadata": {"uri": "mcp://t1"}, "document": "desc1"}]
    cm.set_candidates(candidates)
    
    assert "tool1" in cm.get_system_prompt_extension()
    
    full_schemas = [{"name": "tool1", "description": "full desc"}]
    cm.hydrate_tools(["tool1"], full_schemas)
    
    assert len(cm.get_tool_definitions()) == 1
    assert cm.get_tool_definitions()[0]["name"] == "tool1"
