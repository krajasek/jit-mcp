"""
Example: Integrating JIT-MCP with an external agent loop (Pattern 3).

This demonstrates how an agent with its own agentic loop can dynamically
discover and use MCP tools just-in-time.
"""

import asyncio
import logging
from typing import Any, Callable, Awaitable, Dict, List, Optional
from dataclasses import dataclass

from jit_mcp.tool_provider import JITToolProvider, create_discover_tool_schema
from jit_mcp.registry import ToolMetadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """Represents a tool call from the agent."""
    name: str
    arguments: Dict[str, Any]


@dataclass
class AgentResponse:
    """Response from the agent."""
    content: Optional[str] = None
    tool_call: Optional[ToolCall] = None
    is_done: bool = False


class JITAgentLoop:
    """
    An agent loop with JIT tool discovery capabilities.

    The agent starts with only the 'discover_tools' capability.
    When it needs additional tools, it calls discover_tools to
    search the registry and hydrate relevant tools into its context.
    """

    def __init__(
        self,
        llm_generate: Callable[[str, List[Dict[str, Any]]], Awaitable[AgentResponse]],
        db_path: str = "./mcp_registry"
    ):
        """
        Args:
            llm_generate: Async function that takes (prompt, tools) and returns AgentResponse
            db_path: Path to the ChromaDB registry
        """
        self.llm_generate = llm_generate
        self.provider = JITToolProvider(db_path)

        # Start with only the discovery tool
        self._base_tools = [create_discover_tool_schema()]

    def get_current_tools(self) -> List[Dict[str, Any]]:
        """Returns all currently available tools (base + hydrated)."""
        return self._base_tools + self.provider.get_active_tools()

    async def add_tool_to_registry(self, tool: ToolMetadata) -> None:
        """Register a tool in the underlying registry."""
        await self.provider.add_tool(tool)

    async def run(self, user_input: str, max_turns: int = 10) -> str:
        """
        Run the agent loop until completion or max turns.

        Returns the final response from the agent.
        """
        messages = [f"User: {user_input}"]
        current_prompt = user_input

        for turn in range(max_turns):
            logger.info(f"Turn {turn + 1}: {len(self.get_current_tools())} tools available")

            # Get agent response
            response = await self.llm_generate(current_prompt, self.get_current_tools())

            if response.is_done:
                return response.content or "Done"

            if response.tool_call:
                tool_name = response.tool_call.name
                tool_args = response.tool_call.arguments

                logger.info(f"Agent called tool: {tool_name}")

                # Handle the special discover_tools call
                if tool_name == "discover_tools":
                    query = tool_args.get("query", "")
                    n_results = tool_args.get("n_results", 5)

                    new_tools = await self.provider.discover_and_hydrate(
                        query, n_results=n_results
                    )

                    if new_tools:
                        tool_names = [t["name"] for t in new_tools]
                        result = f"Discovered and loaded {len(new_tools)} tools: {tool_names}"
                        logger.info(result)
                    else:
                        result = f"No tools found for: {query}"

                # Handle hydrated MCP tools
                elif self.provider.is_hydrated(tool_name):
                    try:
                        result = await self.provider.execute(tool_name, tool_args)
                        result = str(result)
                    except Exception as e:
                        result = f"Error executing {tool_name}: {e}"

                else:
                    result = f"Unknown tool: {tool_name}. Use discover_tools to find available tools."

                # Feed result back to agent
                messages.append(f"Tool ({tool_name}): {result}")
                current_prompt = f"{user_input}\n\nPrevious actions:\n" + "\n".join(messages[-5:])

            elif response.content:
                return response.content

        return "Max turns reached"


# =============================================================================
# Example with a mock LLM (for testing without API keys)
# =============================================================================

class MockLLM:
    """A mock LLM that simulates tool discovery and usage."""

    def __init__(self):
        self.turn = 0

    async def generate(
        self,
        prompt: str,
        tools: List[Dict[str, Any]]
    ) -> AgentResponse:
        """Simulate LLM behavior for demonstration."""
        self.turn += 1
        tool_names = [t["name"] for t in tools]

        # Turn 1: Discover tools
        if self.turn == 1:
            return AgentResponse(
                tool_call=ToolCall(
                    name="discover_tools",
                    arguments={"query": "stock prices financial data"}
                )
            )

        # Turn 2: Use discovered tool (if available)
        if self.turn == 2 and "finance_tool" in tool_names:
            return AgentResponse(
                tool_call=ToolCall(
                    name="finance_tool",
                    arguments={"ticker": "NVDA", "metric": "revenue"}
                )
            )

        # Turn 3: Done
        return AgentResponse(
            content="I found the revenue data for NVIDIA.",
            is_done=True
        )


# =============================================================================
# Example with Google Gemini
# =============================================================================

async def create_gemini_generator():
    """
    Creates an LLM generator function using Google Gemini.
    Requires GOOGLE_API_KEY environment variable.

    Note: Uses google-genai (the newer SDK). Install via: pip install google-genai
    """
    import os
    from google import genai
    from google.genai import types

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not set")

    client = genai.Client(api_key=api_key)

    async def generate(prompt: str, tools: List[Dict[str, Any]]) -> AgentResponse:
        # Convert tool schemas to Gemini format
        gemini_tools = []
        for tool in tools:
            gemini_tools.append(types.Tool(
                function_declarations=[types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    parameters=tool.get("input_schema", {})
                )]
            ))

        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=gemini_tools if gemini_tools else None
            )
        )

        # Check for tool calls
        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    return AgentResponse(
                        tool_call=ToolCall(
                            name=part.function_call.name,
                            arguments=dict(part.function_call.args) if part.function_call.args else {}
                        )
                    )

            # Text response
            if response.candidates[0].content.parts:
                text = response.candidates[0].content.parts[0].text
                if text:
                    return AgentResponse(content=text, is_done=True)

        return AgentResponse(content="No response generated", is_done=True)

    return generate


# =============================================================================
# Main examples
# =============================================================================

async def example_mock():
    """Run example with mock LLM (no API key required)."""
    print("\n" + "=" * 60)
    print("Example: Mock LLM Integration")
    print("=" * 60 + "\n")

    mock_llm = MockLLM()
    agent = JITAgentLoop(llm_generate=mock_llm.generate)

    # Register some tools in the registry
    await agent.add_tool_to_registry(ToolMetadata(
        name="finance_tool",
        description="Access real-time stock prices and financial metrics",
        uri="mcp+stdio://echo/mock-finance-server",
        category="Financial"
    ))

    await agent.add_tool_to_registry(ToolMetadata(
        name="csv_writer",
        description="Write data to CSV files",
        uri="mcp+stdio://echo/mock-csv-server",
        category="FileOps"
    ))

    # Run the agent
    result = await agent.run("What is NVIDIA's revenue?")
    print(f"\nFinal result: {result}")


async def example_gemini():
    """Run example with Google Gemini (requires GOOGLE_API_KEY)."""
    print("\n" + "=" * 60)
    print("Example: Gemini Integration")
    print("=" * 60 + "\n")

    try:
        generate = await create_gemini_generator()
    except ValueError as e:
        print(f"Skipping Gemini example: {e}")
        return

    agent = JITAgentLoop(llm_generate=generate)

    # Register tools
    await agent.add_tool_to_registry(ToolMetadata(
        name="weather_tool",
        description="Get current weather and forecasts for any location",
        uri="mcp+stdio://npx/-y/@modelcontextprotocol/server-weather",
        category="Search"
    ))

    result = await agent.run("What's the weather in San Francisco?")
    print(f"\nFinal result: {result}")


async def main():
    """Run all examples."""
    await example_mock()

    # Uncomment to run Gemini example (requires API key)
    # await example_gemini()


if __name__ == "__main__":
    asyncio.run(main())
