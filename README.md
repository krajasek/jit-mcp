# JIT-MCP (Just-In-Time Model Context Protocol)

JIT-MCP is a sophisticated agentic system that dynamically manages Model Context Protocol (MCP) tools. Instead of pre-loading all tools into an LLM's context window, it retrieves and hydrates relevant tools just-in-time based on the model's identified intent.

## Capabilities

- **Dynamic Tool Discovery**: Automatically identifies the need for tools and searches an MCP registry.
- **Configurable Search**: Supports both BM25 (keyword) and Semantic (vector) search for tool discovery.
- **Context Optimization**: Reduces token usage and avoids "lost in the middle" problems by loading only necessary tools.
- **Stateful Orchestration**: Manages the multi-step flow between tool intent, discovery, confirmation, and execution.

## Getting Started

### Prerequisites

- [uv](https://github.com/astral-sh/uv)
- Python 3.11+

### Installation

```bash
uv sync
```

## Usage & Model Configuration

The `JITOrchestrator` is designed to be model-agnostic. While the current implementation includes a simulation of the model's "intent" block, it is built to integrate with any LLM (e.g., Gemini, OpenAI, Claude).

### Specifying a Model
You can pass your choice of model or a custom model wrapper to the orchestrator. For example:

```python
from jit_mcp.orchestrator import JITOrchestrator

# Initialize with a specific model configuration (hypothetical)
orchestrator = JITOrchestrator(model_name="gemini-1.5-pro")

# You can also pass custom model handlers if implemented:
# orchestrator = JITOrchestrator(model_handler=MyCustomModel())

response = orchestrator.query("Find the latest revenue for Nvidia and save to a CSV.")
print(response)
```

## MCP Registry Setup

The registry uses **ChromaDB** for persistent storage and semantic search.

### Initializing the Registry
By default, the registry is stored in `./mcp_registry`. You can specify a custom path:

```python
from jit_mcp.registry import MCPRegistry

registry = MCPRegistry(db_path="./my_tools_db")
```

### Loading Data into the Registry
To add tools to the registry, use the `ToolMetadata` model:

```python
from jit_mcp.registry import MCPRegistry, ToolMetadata

registry = MCPRegistry()

tool = ToolMetadata(
    name="google_calendar",
    description="Manage calendar events and schedules.",
    uri="mcp://calendar-server",
    category="Admin"
)

registry.add_tool(tool)
```

## JIT Orchestration Flow

JIT-MCP handles the orchestration flow through a 6-step state machine:

1.  **User Initiation**: User sends a query to the agentic system.
2.  **Tool Intent**: The LLM analyzes the query. If it identifies a need for tools, it outputs a "THOUGHT" block indicating requested capabilities (e.g., "I need a financial tool").
3.  **Registry Search**: The system performs a search (Semantic or BM25) on the MCP Registry based on the LLM's intent.
4.  **Candidate Review**: The system presents candidate tool summaries to the LLM for confirmation.
5.  **Hydration**: Once confirmed, the system fetches the full JSON-RPC schemas from the respective MCP servers and injects them into the context window.
6.  **Tool Execution**: The LLM generates tool calls; the system executes them and returns the final response.

## Architecture

- **MCP Registry**: Built on ChromaDB for metadata storage and search.
- **Search Provider**: Modular implementation for hybrid search strategies (BM25 + Semantic).
- **Dynamic Context Manager**: Manages the injection/ejection of tool schemas on the fly.
- **Orchestrator**: The central controller managing the multi-step JIT state machine.
