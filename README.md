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

The `JITOrchestrator` is fully asynchronous and designed to be model-agnostic. It integrates with the Gemini API to perform intent detection and tool calling.

### Prerequisites

1.  **API Key**: Set your Google Gemini API key in an `.env` file or environment:
    ```bash
    export GOOGLE_API_KEY="your-api-key"
    ```

### Basic Async Usage

```python
import asyncio
from jit_mcp.orchestrator import JITOrchestrator

async def main():
    orchestrator = JITOrchestrator(model_name="gemini-1.5-flash")
    
    # Run the dynamic JIT flow
    result = await orchestrator.query("Find revenue for Nvidia and save to CSV.")
    print(result)

if __name__ == "__main__":
    asyncio.run(main())
```

## MCP Registry & Search

The registry uses **ChromaDB** and supports `async` operations for non-blocking I/O.

### Loading Tools

```python
from jit_mcp.registry import ToolMetadata

tool = ToolMetadata(
    name="finance_tool",
    description="Access real-time stock and revenue data.",
    uri="mcp+stdio://path/to/server",
    category="Financial"
)

await orchestrator.add_tool_to_registry(tool)
```

## Production Architecture

- **Async Core**: Built on `anyio` and native `asyncio` for high-concurrency performance.
- **Official SDKs**: Uses `google-generativeai` and `mcp-python-sdk`.
- **ChromaDB Registry**: Persistent vector database for metadata-driven discovery.
- **State Machine**: Orchestrates 6 stages: User Query -> Intent -> Search -> Candidate Review -> Hydration -> Execution.
