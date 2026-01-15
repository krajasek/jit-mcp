# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build and Development Commands

```bash
# Install dependencies
uv sync

# Run all tests
pytest

# Run a single test
pytest tests/test_registry.py::test_add_and_search_tool

# Run async tests specifically
pytest -v tests/

# Linting and formatting (via pre-commit)
ruff check --fix .
ruff format .

# Type checking
mypy src/
```

## Environment Setup

Requires `GOOGLE_API_KEY` environment variable for Gemini API access:
```bash
export GOOGLE_API_KEY="your-api-key"
```

## Architecture

JIT-MCP (Just-In-Time Model Context Protocol) dynamically loads MCP tools on-demand rather than pre-loading all tools into context. The system uses a 6-stage orchestration flow:

```
User Query -> Intent Detection -> Registry Search -> Candidate Review -> Hydration -> Execution
```

### Core Components (src/jit_mcp/)

- **orchestrator.py** - `JITOrchestrator`: Main entry point that coordinates the JIT flow. Manages the pipeline from query to tool execution.

- **llm_provider.py** - `LLMProvider`: Wraps Google Gemini API for intent detection (structured JSON output) and tool calling. Returns `IntentResponse` with `needs_tools`, `tool_categories`, `search_query`, and `thought` fields.

- **registry.py** - `MCPRegistry`: ChromaDB-backed persistent vector store for tool metadata. `ToolMetadata` model defines tool schema (name, description, uri, category). Supports semantic search via embeddings and category-based filtering.

- **search.py** - `SearchService`: Abstracts search over the registry with swappable providers (semantic via ChromaDB embeddings, BM25 fallback). Uses `SearchProvider` protocol.

- **mcp_client.py** - `MCPClient`: Official MCP Python SDK client for stdio-based server connections. Handles schema fetching (`list_tools`) and tool execution (`call_tool`).

- **context_manager.py** - `DynamicContextManager`: Tracks candidate and active tools during the JIT flow. Manages hydration state and generates system prompt extensions.

- **tool_provider.py** - `JITToolProvider`: Enables external agents to dynamically discover and execute MCP tools. Provides `discover()`, `discover_and_hydrate()`, and `execute()` methods. Use with `create_discover_tool_schema()` to bootstrap agent tool discovery.

### Data Flow

1. User query enters `JITOrchestrator.query()`
2. `LLMProvider.detect_intent()` determines if tools are needed and generates a search query
3. `SearchService.search()` queries ChromaDB for matching tool metadata
4. `DynamicContextManager` stores candidates
5. `MCPClient.get_tool_schemas()` hydrates full tool definitions from MCP servers
6. `LLMProvider.get_tool_calls()` generates function calls using Gemini's native tool calling
7. `MCPClient.execute_tool()` runs the selected tools

### Key Patterns

- All registry and LLM operations are async (uses `anyio` for thread-pool execution of sync ChromaDB calls)
- Tool URIs follow `mcp+stdio://` scheme mapped to `StdioServerParameters`
- Tests use `pytest-asyncio` and `tmp_path` fixtures for isolated ChromaDB instances
