"""
Vector Search Tools - Banking Domain
======================================

Tools for semantic search on banking documents using LlamaStack Vector Store.
Searches FAQs, product guides, policies, and compliance documents.
Uses the LlamaStack API endpoints: /v1/vector-io/query and /v1/vector-io/insert

State Management:
- Uses ToolContext for tracking retrieval history
- Supports the Agentic RAG loop pattern
"""

import json
import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ...config_loader import get_vector_store_config

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
        max_chunks: int = None
    ) -> List[Dict[str, Any]]:
        """
        Query the vector store for similar documents.
        
        Uses endpoint: POST /v1/vector-io/query
        
        Args:
            query: The search query text
            max_chunks: Maximum number of results to return
            
        Returns:
            List of matching chunks with content and metadata
        """
        max_chunks = max_chunks or self.config.similarity_top_k
        
        url = f"{self.base_url}/v1/vector-io/query"
        payload = {
            "vector_db_id": self.vector_store_id,
            "query": query,
            "params": {"max_chunks": max_chunks}
        }
        
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
            
            return chunks
            
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
    Search banking documents using semantic vector similarity.
    
    GENERIC RETRIEVER for semantic search on banking documents.
    
    This uses LlamaStack's vector store API (/v1/vector-io/query) to find
    documents whose content semantically matches the query.
    
    Use for:
    - Policy questions ("How do I open a checking account?")
    - FAQ-style questions ("What are overdraft fees?")
    - General product information lookup
    - Compliance policy details
    
    Args:
        query: Natural language search query (e.g., "mortgage rates for first-time buyers")
        limit: Maximum number of results to return
        tool_context: Optional ADK ToolContext for state tracking
        
    Returns:
        List of matching documents with their content, metadata, and relevance scores
    """
    print(f"---VECTOR SEARCH: '{query}' (limit={limit})---")
    
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


# Export tools list - main tool for the vector search agent
VECTOR_TOOLS = [vector_search_docs]
