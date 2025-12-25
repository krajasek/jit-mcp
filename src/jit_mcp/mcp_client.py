import asyncio
from typing import List, Dict, Any, Optional
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPClient:
    """
    Production-grade MCP Client using the official Python SDK.
    Supports connecting to local servers via stdio.
    """
    
    async def get_tool_schemas(self, server_params: StdioServerParameters) -> List[Dict[str, Any]]:
        """
        Connects to an MCP server and fetches all available tool schemas.
        """
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                return [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.inputSchema
                    }
                    for tool in tools.tools
                ]

    async def execute_tool(
        self, 
        server_params: StdioServerParameters, 
        tool_name: str, 
        arguments: Dict[str, Any]
    ) -> Any:
        """
        Executes a tool on a specific MCP server.
        """
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return result.content
