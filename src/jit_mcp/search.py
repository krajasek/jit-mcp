from typing import List, Dict, Any, Protocol
from jit_mcp.registry import MCPRegistry

class SearchProvider(Protocol):
    def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        ...

class SemanticSearchProvider:
    def __init__(self, registry: MCPRegistry):
        self.registry = registry

    def search(self, query: str, n_results: int = 5, **kwargs: Any) -> List[Dict[str, Any]]:
        return self.registry.search_semantic(query, n_results=n_results)

class BM25SearchProvider:
    """
    Placeholder for BM25 search. 
    In a real implementation, this might use a dedicated index.
    For now, we'll use keyword-based filtering or a simple mock.
    """
    def __init__(self, registry: MCPRegistry):
        self.registry = registry

    def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        # Mock BM25 using keyword filtering for now
        # Ideally, use rank_bm25 or ChromaDB's where clause if it supported FTS well.
        # Here we'll just do a simple fallback to semantic if no exact category match.
        return self.registry.search_semantic(query) # Fallback for now

class SearchService:
    def __init__(self, registry: MCPRegistry, mode: str = "semantic"):
        self.registry = registry
        self.mode = mode
        self._providers: Dict[str, SearchProvider] = {
            "semantic": SemanticSearchProvider(registry),
            "bm25": BM25SearchProvider(registry)
        }

    def search(self, query: str, **kwargs: Any) -> List[Dict[str, Any]]:
        provider = self._providers.get(self.mode, self._providers["semantic"])
        return provider.search(query, **kwargs)

    def set_mode(self, mode: str) -> None:
        if mode in self._providers:
            self.mode = mode
        else:
            raise ValueError(f"Unsupported search mode: {mode}")
