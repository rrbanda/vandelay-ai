"""
Vector Search Tools - Banking Domain (GraphRAG Enhanced)
=========================================================

Tools for semantic search on banking documents using LlamaStack Vector Store.
Includes HYBRID GRAPHRAG retrieval that combines vector search with
knowledge graph context expansion.

GraphRAG Pattern:
1. Vector search on documents (semantic similarity)
2. Extract entity mentions from results (products, regulations, etc.)
3. Fetch related graph context for mentioned entities (Neo4j)
4. Return combined context for richer answers

State Management:
- Uses ToolContext for tracking retrieval history
- Supports the Agentic RAG loop pattern
"""

import json
import httpx
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

from ...config_loader import (
    get_vector_store_config,
    get_graphrag_config,
    get_entity_patterns,
    get_neo4j_config,
)

# Try to import ToolContext for state tracking (optional)
try:
    from google.adk.tools.tool_context import ToolContext
    HAS_TOOL_CONTEXT = True
except ImportError:
    HAS_TOOL_CONTEXT = False
    ToolContext = None


@dataclass
class VectorStoreConfig:
    """Configuration for LlamaStack Vector Store."""
    provider: str
    base_url: str
    vector_store_id: str
    vector_store_name: str = ""
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 384
    similarity_top_k: int = 5
    # SSL verification: True for production, False only for dev with self-signed certs
    verify_ssl: bool = True
    # Hybrid search options (LlamaStack enhanced features)
    search_mode: str = "vector"  # 'vector', 'keyword', or 'hybrid'
    ranker_type: str = "weighted"  # 'rrf' or 'weighted'
    ranking_alpha: float = 0.7  # Weight for vector vs keyword (0.0-1.0)


class LlamaStackVectorClient:
    """
    Client for LlamaStack Vector Store operations.
    Uses the LlamaStack API for vector similarity search.
    """
    
    def __init__(self, config: VectorStoreConfig):
        """
        Initialize the LlamaStack Vector Store client.
        
        Args:
            config: Vector store configuration
        """
        self.config = config
        self.base_url = config.base_url.rstrip('/')
        self.vector_store_id = config.vector_store_id
        # Use SSL verification setting from config (default: True for security)
        # Set verify_ssl: false in config only for development with self-signed certs
        self.client = httpx.Client(timeout=60.0, verify=config.verify_ssl)
    
    def query(
        self, 
        query: str, 
        max_chunks: int = None,
        search_mode: str = None,
    ) -> List[Dict[str, Any]]:
        """
        Query the vector store for similar documents using hybrid search.
        
        Supports three search modes:
        - 'vector': Pure semantic similarity search (default)
        - 'keyword': Traditional keyword-based search for exact matches
        - 'hybrid': Combines both vector and keyword search for optimal results
        
        Uses endpoint: POST /v1/vector-io/query (with hybrid search params)
        
        Args:
            query: The search query text
            max_chunks: Maximum number of results to return
            search_mode: Override the default search mode ('vector', 'keyword', 'hybrid')
            
        Returns:
            List of matching chunks with content and metadata
        """
        max_chunks = max_chunks or self.config.similarity_top_k
        mode = search_mode or self.config.search_mode
        
        url = f"{self.base_url}/v1/vector-io/query"
        
        # Build payload with hybrid search parameters
        payload = {
            "vector_db_id": self.vector_store_id,
            "query": query,
            "params": {"max_chunks": max_chunks}
        }
        
        # Add hybrid search parameters if not using basic vector search
        if mode in ("hybrid", "keyword"):
            payload["search_mode"] = mode
            
            # Add ranking options for hybrid search
            if mode == "hybrid" and self.config.ranker_type:
                payload["ranking_options"] = {
                    "ranker": {
                        "type": self.config.ranker_type,
                    }
                }
                # Add alpha parameter for weighted ranker
                if self.config.ranker_type == "weighted":
                    payload["ranking_options"]["ranker"]["alpha"] = self.config.ranking_alpha
        
        try:
            response = self.client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            result = response.json()
            
            # Extract chunks without embeddings for cleaner output
            chunks = []
            for chunk in result.get("chunks", []):
                chunks.append({
                    "content": chunk.get("content", ""),
                    "metadata": chunk.get("metadata", {}),
                    "score": chunk.get("score", 0.0)
                })
            
            # Log search mode used
            if mode != "vector":
                print(f"  (search_mode={mode}, alpha={self.config.ranking_alpha})")
            
            return chunks
            
        except httpx.HTTPStatusError as e:
            # If hybrid/keyword search fails with 400, fall back to basic vector search
            # This handles servers that don't support hybrid search parameters
            if mode != "vector" and e.response.status_code == 400:
                print(f"Hybrid search returned 400, falling back to vector search")
                return self.query(query, max_chunks, search_mode="vector")
            print(f"Vector store query error: {e}")
            return []
        except httpx.HTTPError as e:
            print(f"Vector store query error: {e}")
            return []
    
    def insert(
        self, 
        chunks: List[Dict[str, Any]]
    ) -> bool:
        """
        Insert documents into the vector store.
        
        Uses endpoint: POST /v1/vector-io/insert
        
        Args:
            chunks: List of chunks to insert, each with 'content' and optional 'metadata'
            
        Returns:
            True if successful, False otherwise
        """
        url = f"{self.base_url}/v1/vector-io/insert"
        payload = {
            "vector_db_id": self.vector_store_id,
            "chunks": chunks
        }
        
        try:
            response = self.client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return True
            
        except httpx.HTTPError as e:
            print(f"Vector store insert error: {e}")
            return False
    
    def close(self):
        """Close the HTTP client."""
        self.client.close()


# Global client instance (lazy loaded)
_vector_client = None
_vector_client_store_id = None


def _get_vector_client() -> LlamaStackVectorClient:
    """Get or create the LlamaStack vector client from config."""
    global _vector_client, _vector_client_store_id
    
    # Always get fresh config to detect changes
    config_dict = get_vector_store_config()
    current_store_id = config_dict.get('vector_store_id', '')
    
    # Recreate client if store ID changed or not initialized
    if _vector_client is None or _vector_client_store_id != current_store_id:
        config = VectorStoreConfig(
            provider=config_dict.get('provider', 'llamastack'),
            base_url=config_dict.get('base_url', ''),
            vector_store_id=current_store_id,
            embedding_model=config_dict.get('embedding_model', 'all-MiniLM-L6-v2'),
            embedding_dimension=config_dict.get('embedding_dimension', 384),
            similarity_top_k=config_dict.get('similarity_top_k', 5),
            verify_ssl=config_dict.get('verify_ssl', True),
            # Hybrid search options
            search_mode=config_dict.get('search_mode', 'vector'),
            ranker_type=config_dict.get('ranker_type', 'weighted'),
            ranking_alpha=config_dict.get('ranking_alpha', 0.7),
        )
        _vector_client = LlamaStackVectorClient(config)
        _vector_client_store_id = current_store_id
    
    return _vector_client


def vector_search_docs(
    query: str, 
    limit: int = 5,
    tool_context: Optional[ToolContext] = None,
) -> List[Dict[str, Any]]:
    """
    Search banking documents using hybrid search (vector + keyword).
    
    GENERIC RETRIEVER for semantic search on banking documents with optional
    keyword matching for improved recall.
    
    This uses LlamaStack's vector store API with hybrid search capability:
    - 'vector': Pure semantic similarity search
    - 'keyword': Traditional keyword-based search for exact matches  
    - 'hybrid': Combines both for optimal results (configurable via ranking_alpha)
    
    The search mode and ranking are configured in config.yaml under vector_store.
    
    Use for:
    - Policy questions ("How do I open a checking account?")
    - FAQ-style questions ("What are overdraft fees?")
    - General product information lookup
    - Compliance policy details
    - Queries with specific terms (Basel III, AML) benefit from hybrid mode
    
    Args:
        query: Natural language search query (e.g., "mortgage rates for first-time buyers")
        limit: Maximum number of results to return
        tool_context: Optional ADK ToolContext for state tracking
        
    Returns:
        List of matching documents with their content, metadata, and relevance scores
    """
    # Get config for logging
    config_dict = get_vector_store_config()
    search_mode = config_dict.get('search_mode', 'vector')
    print(f"---VECTOR SEARCH ({search_mode}): '{query}' (limit={limit})---")
    
    client = _get_vector_client()
    
    try:
        results = client.query(query, max_chunks=limit)
        
        if not results:
            formatted_results = [{"message": f"No matches found for '{query}'"}]
        else:
            # Format results for the agent
            formatted_results = []
            for i, chunk in enumerate(results):
                metadata = chunk.get("metadata", {})
                
                # Extract person info from metadata if available
                result = {
                    "rank": i + 1,
                    "content": chunk.get("content", ""),
                    "score": chunk.get("score", 0.0),
                }
                
                # Include any metadata fields (name, title, id, etc.)
                if metadata:
                    result["metadata"] = metadata
                    # Try to extract common fields for easier access
                    if "name" in metadata:
                        result["name"] = metadata["name"]
                    if "id" in metadata:
                        result["id"] = metadata["id"]
                    if "title" in metadata or "current_title" in metadata:
                        result["title"] = metadata.get("title") or metadata.get("current_title")
                    if "department" in metadata:
                        result["department"] = metadata["department"]
                
                formatted_results.append(result)
            
            print(f"Found {len(formatted_results)} matching documents")
        
        # Track in state if context provided
        if tool_context is not None and HAS_TOOL_CONTEXT:
            _track_retrieval_in_state(
                tool_context, 
                tool_name="vector_search_docs",
                query=query,
                results=formatted_results,
            )
        
        return formatted_results
        
    except Exception as e:
        print(f"Vector search error: {e}")
        error_result = [{"error": str(e), "message": "Vector search failed"}]
        
        # Track error in state
        if tool_context is not None and HAS_TOOL_CONTEXT:
            _track_retrieval_in_state(
                tool_context,
                tool_name="vector_search_docs",
                query=query,
                results=error_result,
                has_error=True,
            )
        
        return error_result


def _track_retrieval_in_state(
    context: ToolContext,
    tool_name: str,
    query: str,
    results: List[Dict],
    has_error: bool = False,
) -> None:
    """
    Track a retrieval in the session state.
    
    Updates the temp:retrieval_history state key.
    """
    # Get current history
    history_json = context.state.get("temp:retrieval_history", "[]")
    try:
        history = json.loads(history_json)
    except (json.JSONDecodeError, TypeError):
        history = []
    
    # Add new entry
    entry = {
        "tool": tool_name,
        "query": query,
        "result_count": len(results),
        "has_error": has_error,
    }
    history.append(entry)
    
    # Update state
    context.state["temp:retrieval_history"] = json.dumps(history)


def insert_resume_chunks(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Insert resume chunks into the LlamaStack vector store.
    
    This uses LlamaStack's vector store API (/v1/vector-io/insert) to add
    new documents to the vector store with embeddings generated automatically.
    
    Args:
        chunks: List of chunks to insert. Each chunk should have:
            - content: The text content to embed
            - metadata: Optional dict with fields like name, id, title, etc.
        
    Returns:
        Dict with success status and message
    """
    print(f"---LLAMASTACK VECTOR INSERT: {len(chunks)} chunks---")
    
    client = _get_vector_client()
    
    try:
        success = client.insert(chunks)
        
        if success:
            return {
                "success": True,
                "message": f"Successfully inserted {len(chunks)} chunks into vector store"
            }
        else:
            return {
                "success": False,
                "message": "Insert operation failed"
            }
            
    except Exception as e:
        print(f"Vector insert error: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Vector insert failed"
        }


# =============================================================================
# GraphRAG Hybrid Retrieval (Vector + Graph Context)
# =============================================================================

def _get_neo4j_driver():
    """
    Get Neo4j driver for graph context lookups.
    
    Reuses the driver from graph_query tools to avoid connection duplication.
    Falls back to creating a new driver if import fails.
    """
    # Try to reuse the existing driver from graph_query tools
    try:
        from ..graph_query.tools import _get_driver
        return _get_driver()
    except ImportError:
        # Fallback: create our own driver
        from neo4j import GraphDatabase
        neo4j_config = get_neo4j_config()
        return GraphDatabase.driver(
            neo4j_config['uri'],
            auth=(neo4j_config['username'], neo4j_config['password'])
        )


def _extract_entity_mentions(
    results: List[Dict[str, Any]],
    entity_patterns: Dict[str, List[str]] = None
) -> Set[str]:
    """
    Extract entity mentions from vector search results using pattern matching.
    
    Uses entity patterns from config to identify mentions of products,
    regulations, risk terms, etc. in the document content.
    
    Args:
        results: Vector search results with 'content' field
        entity_patterns: Dict of category -> patterns (loaded from config if None)
        
    Returns:
        Set of matched entity patterns (lowercased)
    """
    if entity_patterns is None:
        entity_patterns = get_entity_patterns()
    
    if not entity_patterns:
        return set()
    
    mentions = set()
    
    for result in results:
        content = result.get("content", "").lower()
        
        # Check each category of patterns
        for category, patterns in entity_patterns.items():
            for pattern in patterns:
                pattern_lower = pattern.lower()
                if pattern_lower in content:
                    mentions.add(pattern_lower)
    
    return mentions


def _fetch_graph_context(
    entity_mentions: Set[str],
    max_lookups: int = 10,
    max_connections: int = 5
) -> List[Dict[str, Any]]:
    """
    Fetch graph context for mentioned entities from Neo4j.
    
    Queries the knowledge graph to find entities matching the mentions
    and returns their 1-hop neighborhood (related entities).
    
    Args:
        entity_mentions: Set of entity patterns to look up
        max_lookups: Maximum number of entities to look up
        max_connections: Maximum connections to return per entity
        
    Returns:
        List of entity context dicts with entity info and connections
    """
    if not entity_mentions:
        return []
    
    # Limit lookups
    mentions_list = list(entity_mentions)[:max_lookups]
    
    # Cypher query to find entities and their connections
    # Uses subquery to get first match per search term, then expands connections
    query = '''
    UNWIND $mentions AS search_term
    CALL {
        WITH search_term
        MATCH (e)
        WHERE toLower(e.name) CONTAINS search_term
           OR (e.category IS NOT NULL AND toLower(e.category) CONTAINS search_term)
           OR (e.full_name IS NOT NULL AND toLower(e.full_name) CONTAINS search_term)
        RETURN e
        LIMIT 1
    }
    WITH e, search_term
    OPTIONAL MATCH (e)-[r]-(related)
    WHERE related IS NOT NULL
    WITH e, search_term, 
         collect(DISTINCT {
             relationship: type(r),
             direction: CASE WHEN startNode(r) = e THEN 'outgoing' ELSE 'incoming' END,
             related_entity: related.name,
             related_type: labels(related)[0]
         })[0..$max_connections] AS connections
    RETURN search_term AS matched_term,
           e.name AS entity_name,
           labels(e)[0] AS entity_type,
           e.description AS entity_description,
           connections
    LIMIT $max_lookups
    '''
    
    try:
        driver = _get_neo4j_driver()
        result = driver.execute_query(
            query,
            mentions=mentions_list,
            max_lookups=max_lookups,
            max_connections=max_connections,
            result_transformer_=lambda r: r.data()
        )
        return result if result else []
    except Exception as e:
        print(f"Graph context lookup error: {e}")
        return []


def vector_search_with_graph_context(
    query: str,
    limit: int = 5,
    include_graph_context: bool = True,
    tool_context: Optional[ToolContext] = None,
) -> Dict[str, Any]:
    """
    HYBRID GRAPHRAG RETRIEVAL: Vector search + knowledge graph context expansion.
    
    This implements the core Neo4j GraphRAG pattern by combining:
    1. Semantic search on banking documents (LlamaStack vector store)
    2. Entity extraction from search results (pattern matching)
    3. Graph context expansion for mentioned entities (Neo4j traversal)
    
    Use this tool for questions about banking policies, procedures, or concepts
    that may reference specific entities (products, regulations, risks).
    
    Examples:
    - "What are the Basel III capital requirements?" -> Gets policy docs + regulation graph
    - "Explain credit risk assessment" -> Gets docs + portfolio/risk connections
    - "What are the AML compliance procedures?" -> Gets compliance docs + regulation details
    
    Args:
        query: Natural language search query
        limit: Maximum number of vector search results (default 5)
        include_graph_context: Whether to fetch graph context for entities (default True)
        tool_context: Optional ADK ToolContext for state tracking
        
    Returns:
        Dict with:
        - documents: List of vector search results
        - entities_mentioned: List of extracted entity mentions
        - graph_context: List of entity details and connections from knowledge graph
    """
    print(f"---HYBRID GRAPHRAG RETRIEVAL: '{query}'---")
    
    # Load GraphRAG config
    graphrag_config = get_graphrag_config()
    enable_graph = graphrag_config.get('enable_graph_context', True) and include_graph_context
    max_lookups = graphrag_config.get('max_entity_lookups', 10)
    max_connections = graphrag_config.get('max_connections_per_entity', 5)
    
    # Step 1: Vector search
    vector_results = vector_search_docs(query, limit, tool_context)
    
    # Check if we got valid results (not just error messages)
    has_valid_results = (
        vector_results and 
        not any(r.get("error") for r in vector_results) and
        not all(r.get("message", "").startswith("No matches") for r in vector_results)
    )
    
    if not enable_graph or not has_valid_results:
        return {
            "documents": vector_results,
            "entities_mentioned": [],
            "graph_context": [],
            "graphrag_enabled": False
        }
    
    # Step 2: Extract entity mentions from vector results
    entity_patterns = get_entity_patterns()
    entity_mentions = _extract_entity_mentions(vector_results, entity_patterns)
    print(f"  Entities extracted: {list(entity_mentions)}")
    
    # Step 3: Fetch graph context for mentioned entities
    graph_context = []
    if entity_mentions:
        graph_context = _fetch_graph_context(
            entity_mentions,
            max_lookups=max_lookups,
            max_connections=max_connections
        )
        print(f"  Graph context items: {len(graph_context)}")
    
    # Track in state if context provided
    if tool_context is not None and HAS_TOOL_CONTEXT:
        _track_retrieval_in_state(
            tool_context,
            tool_name="vector_search_with_graph_context",
            query=query,
            results=vector_results,
        )
    
    return {
        "documents": vector_results,
        "entities_mentioned": list(entity_mentions),
        "graph_context": graph_context,
        "graphrag_enabled": True
    }


# Export tools list - includes both basic and hybrid GraphRAG tools
VECTOR_TOOLS = [vector_search_docs, vector_search_with_graph_context]
