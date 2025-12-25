import chromadb
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import anyio

class ToolMetadata(BaseModel):
    name: str
    description: str
    uri: str
    category: str
    schema_params: Optional[Dict[str, Any]] = None

class MCPRegistry:
    def __init__(self, db_path: str = "./mcp_registry"):
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(
            name="mcp_tools",
            metadata={"hnsw:space": "cosine"}
        )

    async def add_tool(self, tool: ToolMetadata) -> None:
        """Adds or updates a tool in the registry."""
        await anyio.to_thread.run_sync(
            lambda: self.collection.upsert(
                ids=[tool.name],
                metadatas=[{
                    "name": tool.name,
                    "uri": tool.uri,
                    "category": tool.category
                }],
                documents=[tool.description]
            )
        )

    async def search_semantic(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Performs semantic search based on tool descriptions."""
        results = await anyio.to_thread.run_sync(
            lambda: self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
        )
        return self._format_results(results)

    async def search_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Filters tools by category."""
        results = await anyio.to_thread.run_sync(
            lambda: self.collection.get(
                where={"category": category}
            )
        )
        formatted: List[Dict[str, Any]] = []
        ids = results.get("ids")
        metadatas = results.get("metadatas")
        documents = results.get("documents")
        
        if ids and metadatas:
            for i in range(len(ids)):
                formatted.append({
                    "id": ids[i],
                    "metadata": metadatas[i],
                    "document": documents[i] if documents and i < len(documents) else ""
                })
        return formatted

    def _format_results(self, results: Any) -> List[Dict[str, Any]]:
        formatted: List[Dict[str, Any]] = []
        if not results or not results.get("ids"):
            return formatted
            
        ids = results["ids"][0] if isinstance(results["ids"][0], list) else results["ids"]
        metadatas = results["metadatas"][0] if isinstance(results["metadatas"][0], list) else results["metadatas"]
        documents = results["documents"][0] if results.get("documents") and isinstance(results["documents"][0], list) else results.get("documents", [])
        distances = results.get("distances", [[]])[0] if results.get("distances") and isinstance(results["distances"][0], list) else results.get("distances", [])

        for i in range(len(ids)):
            item: Dict[str, Any] = {
                "id": ids[i],
                "metadata": metadatas[i],
                "document": documents[i] if documents and i < len(documents) else None,
            }
            if distances and i < len(distances):
                item["distance"] = distances[i]
            formatted.append(item)
        return formatted

    async def get_tool_uri(self, tool_name: str) -> Optional[str]:
        """Retrieves the URI for a specific tool."""
        result = await anyio.to_thread.run_sync(
            lambda: self.collection.get(
                ids=[tool_name]
            )
        )
        if result["metadatas"]:
            return str(result["metadatas"][0]["uri"])
        return None
