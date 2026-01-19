"""
FSI Vector Store Loader.

This module provides functions to load FSI documents into LlamaStack Vector Store.

Usage:
    from data_ingestion.loaders import FSIVectorLoader
    
    loader = FSIVectorLoader()
    loader.ensure_vector_store()  # Creates if not exists
    loader.load_documents(documents)
"""

import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from data_ingestion.config_loader import get_vector_store_config


class FSIVectorLoader:
    """
    Load FSI documents into LlamaStack Vector Store.
    
    Handles document chunking and ingestion for semantic search.
    Supports creating vector stores if they don't exist.
    """
    
    def __init__(
        self,
        base_url: str = None,
        vector_store_id: str = None,
        vector_store_name: str = None,
        embedding_model: str = None,
        embedding_dimension: int = None,
        verify_ssl: bool = False,
    ):
        """
        Initialize the vector loader.
        
        Args:
            base_url: LlamaStack server URL (from config if not provided)
            vector_store_id: Vector store ID (from config if not provided)
            vector_store_name: Name for new vector store (used if creating)
            embedding_model: Embedding model name (from config if not provided)
            embedding_dimension: Embedding dimension (from config if not provided)
            verify_ssl: Whether to verify SSL certificates
        """
        config = get_vector_store_config()
        
        self.base_url = (base_url or config.get('base_url', '')).rstrip('/')
        self.vector_store_id = vector_store_id or config.get('vector_store_id', '')
        self.vector_store_name = vector_store_name or config.get('vector_store_name', 'fsi-documents')
        self.embedding_model = embedding_model or config.get('embedding_model', 'all-MiniLM-L6-v2')
        self.embedding_dimension = embedding_dimension or config.get('embedding_dimension', 384)
        
        self.client = httpx.Client(timeout=120.0, verify=verify_ssl)
        
        self._stats = {
            'documents': 0,
            'chunks': 0,
        }
    
    def close(self):
        """Close the HTTP client."""
        if self.client:
            self.client.close()
    
    def list_vector_stores(self) -> List[Dict[str, Any]]:
        """
        List all available vector stores.
        
        Returns:
            List of vector store info dicts
        """
        # LlamaStack uses /v1/vector_stores (OpenAI-compatible)
        url = f"{self.base_url}/v1/vector_stores"
        
        try:
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()
            # Handle OpenAI-style response with 'data' array
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return data if isinstance(data, list) else []
        except httpx.HTTPError as e:
            print(f"[error] Failed to list vector stores: {e}")
            return []
    
    def vector_store_exists(self, store_id: str = None) -> bool:
        """
        Check if a vector store exists.
        
        Args:
            store_id: Vector store ID to check (uses self.vector_store_id if not provided)
            
        Returns:
            True if exists
        """
        store_id = store_id or self.vector_store_id
        if not store_id:
            return False
        
        url = f"{self.base_url}/v1/vector_stores/{store_id}"
        
        try:
            response = self.client.get(url)
            return response.status_code == 200
        except httpx.HTTPError:
            return False
    
    def create_vector_store(
        self,
        store_id: str = None,
        store_name: str = None,
        embedding_model: str = None,
        embedding_dimension: int = None,
    ) -> Tuple[bool, str]:
        """
        Create a new vector store using OpenAI-compatible API.
        
        Args:
            store_id: Vector store ID (auto-generated if not provided)
            store_name: Name for the vector store
            embedding_model: Embedding model to use
            embedding_dimension: Embedding dimension
            
        Returns:
            Tuple of (success, store_id)
        """
        store_name = store_name or self.vector_store_name
        embedding_model = embedding_model or self.embedding_model
        embedding_dimension = embedding_dimension or self.embedding_dimension
        
        # OpenAI-compatible endpoint
        url = f"{self.base_url}/v1/vector_stores"
        
        # OpenAI-style payload
        payload = {
            "name": store_name,
        }
        
        # Add optional fields if store_id provided
        if store_id:
            payload["vector_store_id"] = store_id
        
        # Add embedding config as metadata (LlamaStack may use this)
        payload["metadata"] = {
            "embedding_model": embedding_model,
            "embedding_dimension": embedding_dimension,
        }
        
        print(f"Creating vector store: {store_name}")
        print(f"  Embedding model: {embedding_model}")
        print(f"  Dimension: {embedding_dimension}")
        
        try:
            response = self.client.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in (200, 201):
                data = response.json()
                created_id = data.get('id') or data.get('vector_store_id') or store_id
                print(f"[ok] Vector store created: {created_id}")
                self.vector_store_id = created_id
                return True, created_id
            elif response.status_code == 409:
                print(f"[ok] Vector store already exists: {store_id}")
                self.vector_store_id = store_id
                return True, store_id or ""
            else:
                print(f"[error] Failed to create: {response.status_code} - {response.text}")
                return False, ""
                
        except httpx.HTTPError as e:
            print(f"[error] HTTP error: {e}")
            return False, ""
    
    def ensure_vector_store(self) -> bool:
        """
        Ensure the vector store exists, creating if necessary.
        
        If vector_store_id is set and exists, use it.
        If not, create a new one.
        
        Returns:
            True if vector store is ready
        """
        # If we have an ID, check if it exists
        if self.vector_store_id:
            if self.vector_store_exists():
                print(f"[ok] Using existing vector store: {self.vector_store_id}")
                return True
            else:
                print(f"[info] Vector store {self.vector_store_id} not found, creating...")
                success, _ = self.create_vector_store(store_id=self.vector_store_id)
                return success
        else:
            # No ID set, create new one
            print("[info] No vector store ID configured, creating new one...")
            success, store_id = self.create_vector_store()
            if success:
                print(f"[info] Created vector store: {store_id}")
                print(f"[info] Set VECTOR_STORE_ID={store_id} to reuse this store")
            return success
    
    def clear_vector_store(self) -> bool:
        """
        Clear all data from the vector store.
        
        Note: LlamaStack may not support clearing directly.
        We delete and recreate the store.
        
        Returns:
            True if successful
        """
        if not self.vector_store_id:
            print("[warn] No vector store ID set")
            return False
        
        # Try to delete the store using OpenAI-compatible endpoint
        url = f"{self.base_url}/v1/vector_stores/{self.vector_store_id}"
        
        try:
            response = self.client.delete(url)
            if response.status_code in (200, 204, 404):
                print(f"[ok] Deleted vector store: {self.vector_store_id}")
            else:
                print(f"[warn] Delete returned: {response.status_code}")
        except httpx.HTTPError as e:
            print(f"[warn] Failed to delete: {e}")
        
        # Recreate the store (new one, as ID may not be reusable)
        success, new_id = self.create_vector_store()
        if success:
            self.vector_store_id = new_id
        return success
    
    def register_vector_db(self) -> bool:
        """
        Register a new vector database with LlamaStack.
        
        DEPRECATED: Use ensure_vector_store() instead.
        
        Returns:
            True if successful or already exists
        """
        return self.ensure_vector_store()
    
    def upload_file(self, filename: str, content: str) -> Optional[str]:
        """
        Upload a file to LlamaStack using the Files API.
        
        Uses endpoint: POST /v1/files
        
        Args:
            filename: Name of the file
            content: File content as string
            
        Returns:
            File ID if successful, None otherwise
        """
        url = f"{self.base_url}/v1/files"
        
        try:
            # Create file-like object from content
            files = {
                'file': (filename, content.encode('utf-8'), 'text/plain'),
            }
            data = {
                'purpose': 'assistants',
            }
            
            response = self.client.post(url, files=files, data=data)
            response.raise_for_status()
            
            result = response.json()
            file_id = result.get('id')
            return file_id
            
        except httpx.HTTPError as e:
            print(f"  Upload error for {filename}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response: {e.response.text[:200]}")
            return None
    
    def add_file_to_vector_store(self, file_id: str) -> bool:
        """
        Add an uploaded file to the vector store.
        
        Uses endpoint: POST /v1/vector_stores/{id}/files
        
        Args:
            file_id: ID of the uploaded file
            
        Returns:
            True if successful
        """
        url = f"{self.base_url}/v1/vector_stores/{self.vector_store_id}/files"
        payload = {
            "file_id": file_id,
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
            print(f"  Add file error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response: {e.response.text[:200]}")
            return False
    
    def insert_chunks(self, chunks: List[Dict[str, Any]]) -> bool:
        """
        Insert document chunks into the vector store.
        
        DEPRECATED: Use upload_file + add_file_to_vector_store instead.
        This method attempts the legacy /v1/vector-io/insert endpoint.
        
        Args:
            chunks: List of chunks, each with 'content' and optional 'metadata'
            
        Returns:
            True if successful
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
            print(f"  Insert error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"  Response: {e.response.text[:200]}")
            return False
    
    def chunk_document(
        self,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> List[str]:
        """
        Split document text into overlapping chunks.
        
        Args:
            text: Document text
            chunk_size: Maximum chunk size in characters
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        # For short documents, return as single chunk
        if len(text) <= chunk_size:
            return [text]
        
        # Split into overlapping chunks
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - overlap
            
            # Avoid tiny final chunks
            if len(text) - start < overlap:
                break
        
        return chunks
    
    def process_document(
        self,
        doc_name: str,
        doc_content: str,
        doc_type: str = "fsi_document",
        chunk_size: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Process a document into chunks ready for ingestion.
        
        Args:
            doc_name: Name of the document
            doc_content: Document content
            doc_type: Type of document
            chunk_size: Maximum chunk size
            
        Returns:
            List of chunks with content and metadata
        """
        # Chunk the document
        text_chunks = self.chunk_document(doc_content, chunk_size=chunk_size)
        
        # Build chunks with metadata
        chunks = []
        for i, chunk_text in enumerate(text_chunks):
            chunk = {
                "content": chunk_text,
                "metadata": {
                    "name": doc_name,
                    "source": doc_name,
                    "doc_type": doc_type,
                    "chunk_index": i,
                    "total_chunks": len(text_chunks),
                }
            }
            chunks.append(chunk)
        
        return chunks
    
    def load_document(
        self,
        doc_name: str,
        doc_content: str,
        doc_type: str = "fsi_document",
        chunk_size: int = 1000,
        verbose: bool = False,
    ) -> bool:
        """
        Load a single document into the vector store.
        
        Args:
            doc_name: Name of the document
            doc_content: Document content
            doc_type: Type of document
            chunk_size: Maximum chunk size
            verbose: Whether to print progress
            
        Returns:
            True if successful
        """
        if verbose:
            print(f"  Processing: {doc_name}")
        
        chunks = self.process_document(doc_name, doc_content, doc_type, chunk_size)
        
        if verbose:
            print(f"    Created {len(chunks)} chunks")
        
        success = self.insert_chunks(chunks)
        
        if success:
            self._stats['documents'] += 1
            self._stats['chunks'] += len(chunks)
        
        return success
    
    def load_documents(
        self,
        documents: List[Dict[str, str]],
        doc_type: str = "fsi_document",
        chunk_size: int = 1000,
        batch_size: int = 10,
        verbose: bool = True,
        use_files_api: bool = True,
    ) -> Dict[str, int]:
        """
        Load multiple documents into the vector store.
        
        Uses the LlamaStack Files API approach:
        1. Upload each document as a file
        2. Add file to vector store
        
        Args:
            documents: List of documents with 'name' and 'content' keys
            doc_type: Type of document
            chunk_size: Maximum chunk size (used for legacy insert method)
            batch_size: Number of chunks per batch (used for legacy insert method)
            verbose: Whether to print progress
            use_files_api: Use Files API (recommended) vs legacy insert
            
        Returns:
            Dict with 'successful' and 'failed' counts
        """
        if verbose:
            print(f"Loading {len(documents)} documents to vector store...")
            if use_files_api:
                print("  Using Files API (OpenAI-compatible)")
        
        successful = 0
        failed = 0
        
        if use_files_api:
            # Use Files API approach (recommended)
            for doc in documents:
                if verbose:
                    print(f"  Uploading: {doc['name']}...", end=" ")
                
                # Upload file
                file_id = self.upload_file(doc['name'], doc['content'])
                
                if not file_id:
                    if verbose:
                        print("[upload failed]")
                    failed += 1
                    continue
                
                # Add to vector store
                if self.add_file_to_vector_store(file_id):
                    if verbose:
                        print(f"[ok] file_id={file_id[:20]}...")
                    successful += 1
                else:
                    if verbose:
                        print("[add failed]")
                    failed += 1
        else:
            # Legacy chunk-based insert approach
            all_chunks = []
            for doc in documents:
                chunks = self.process_document(
                    doc['name'],
                    doc['content'],
                    doc_type,
                    chunk_size
                )
                all_chunks.extend(chunks)
                if verbose:
                    print(f"  [ok] {doc['name']}: {len(chunks)} chunks")
            
            if verbose:
                print(f"\nTotal chunks to ingest: {len(all_chunks)}")
            
            # Insert in batches
            for i in range(0, len(all_chunks), batch_size):
                batch = all_chunks[i:i + batch_size]
                batch_num = i // batch_size + 1
                total_batches = (len(all_chunks) + batch_size - 1) // batch_size
                
                if verbose:
                    print(f"  Batch {batch_num}/{total_batches}...", end=" ")
                
                if self.insert_chunks(batch):
                    if verbose:
                        print("[ok]")
                    successful += len(batch)
                else:
                    if verbose:
                        print("[failed]")
                    failed += len(batch)
        
        self._stats['documents'] = len(documents) if use_files_api else len(documents)
        self._stats['chunks'] = successful
        
        if verbose:
            print(f"\n[ok] Ingested {successful} {'documents' if use_files_api else 'chunks'}")
            if failed > 0:
                print(f"[warn] Failed: {failed}")
        
        return {'successful': successful, 'failed': failed}
    
    def load_from_directory(
        self,
        directory: str,
        pattern: str = "*.txt",
        doc_type: str = "fsi_document",
        chunk_size: int = 1000,
        verbose: bool = True,
    ) -> Dict[str, int]:
        """
        Load all documents from a directory.
        
        Args:
            directory: Path to the directory
            pattern: Glob pattern for files
            doc_type: Type of document
            chunk_size: Maximum chunk size
            verbose: Whether to print progress
            
        Returns:
            Dict with 'successful' and 'failed' counts
        """
        path = Path(directory)
        
        if not path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        # Load documents
        documents = []
        for file_path in sorted(path.glob(pattern)):
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            documents.append({
                'name': file_path.name,
                'content': content,
            })
        
        if verbose:
            print(f"Found {len(documents)} documents in {directory}")
        
        return self.load_documents(
            documents,
            doc_type=doc_type,
            chunk_size=chunk_size,
            verbose=verbose,
        )
    
    def get_stats(self) -> Dict[str, int]:
        """Get loading statistics."""
        return self._stats.copy()
    
    def print_summary(self):
        """Print a summary of the loaded data."""
        print("\n" + "=" * 50)
        print("Vector Store Loading Summary")
        print("=" * 50)
        print(f"  Documents loaded: {self._stats['documents']}")
        print(f"  Chunks created: {self._stats['chunks']}")
        print(f"  Vector store ID: {self.vector_store_id}")
