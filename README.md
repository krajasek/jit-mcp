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

### Usage Example

```python
from jit_mcp.orchestrator import JITOrchestrator

orchestrator = JITOrchestrator()
response = orchestrator.query("Find the latest revenue for Nvidia and save to a CSV.")
print(response)
```

## Architecture

- **MCP Registry**: Built on ChromaDB for metadata storage and search.
- **Search Provider**: Modular implementation for hybrid search strategies.
- **Orchestrator**: The central controller for the JIT flow.
