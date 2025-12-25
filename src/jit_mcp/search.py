from typing import List, Dict, Any, Protocol
from jit_mcp.registry import MCPRegistry

class SearchProvider(Protocol):
    async def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        ...

class SemanticSearchProvider:
    def __init__(self, registry: MCPRegistry):
        self.registry = registry

    async def search(self, query: str, n_results: int = 5, **kwargs: Any) -> List[Dict[str, Any]]:
        return await self.registry.search_semantic(query, n_results=n_results)

class BM25SearchProvider:
    def __init__(self, registry: MCPRegistry):
        self.registry = registry

    async def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        # Fallback to semantic for this implementation
        return await self.registry.search_semantic(query)

class SearchService:
    def __init__(self, registry: MCPRegistry, mode: str = "semantic"):
        self.registry = registry
        self.mode = mode
        self._providers: Dict[str, SearchProvider] = {
            "semantic": SemanticSearchProvider(registry),
            "bm25": BM25SearchProvider(registry)
        }

    async def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        provider = self._providers.get(self.mode, self._providers["semantic"])
        return await provider.search(query, **kwargs)

    def set_mode(self, mode: str) -> None:
        if mode in self._providers:
            self.mode = mode
        else:
            raise ValueError(f"Unsupported search mode: {mode}")
