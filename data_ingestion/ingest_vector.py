#!/usr/bin/env python3
"""
Vector Store Ingestion Script
==============================

Standalone script to ingest FSI documents into LlamaStack Vector Store.

Features:
- Creates vector store if it doesn't exist
- Clears existing data before ingestion (optional)
- Supports data from git repository URL or local files
- Can run on container startup

Usage:
    # Use local data (default)
    python -m data_ingestion.ingest_vector
    
    # Use data from git URL
    python -m data_ingestion.ingest_vector --git-url https://github.com/user/repo.git
    
    # Clear existing data first
    python -m data_ingestion.ingest_vector --clear
    
    # Specify documents directory
    python -m data_ingestion.ingest_vector --docs-dir data/fsi_documents

Environment Variables:
    LLAMASTACK_BASE_URL: LlamaStack server URL
    VECTOR_STORE_ID: Vector store ID (created if not exists)
    VECTOR_STORE_NAME: Name for new vector store
    DATA_GIT_URL: Git repository URL for data source
    DATA_GIT_BRANCH: Git branch (default: main)
"""

import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Dict

import httpx

from data_ingestion.config_loader import get_vector_store_config
from data_ingestion.loaders.vector_loader import FSIVectorLoader
from data_ingestion.git_data_source import get_data_source


def wait_for_llamastack(base_url: str, max_retries: int = 30, delay: int = 2) -> bool:
    """
    Wait for LlamaStack to be available.
    
    Args:
        base_url: LlamaStack server URL
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        True if available, False otherwise
    """
    print(f"Waiting for LlamaStack at {base_url}...")
    
    # Use health endpoint or models endpoint
    health_url = f"{base_url.rstrip('/')}/v1/models"
    
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=10.0, verify=False) as client:
                response = client.get(health_url)
                if response.status_code == 200:
                    print(f"[ok] LlamaStack is available (attempt {attempt + 1})")
                    return True
        except (httpx.HTTPError, httpx.ConnectError) as e:
            if attempt < max_retries - 1:
                print(f"  Attempt {attempt + 1}/{max_retries}: {type(e).__name__}")
                time.sleep(delay)
            else:
                print(f"[error] LlamaStack not available after {max_retries} attempts")
                return False
        except Exception as e:
            print(f"  Unexpected error: {e}")
            time.sleep(delay)
    
    return False


def list_available_embedding_models(base_url: str) -> List[str]:
    """
    List available embedding models from LlamaStack.
    
    Args:
        base_url: LlamaStack server URL
        
    Returns:
        List of embedding model IDs
    """
    url = f"{base_url.rstrip('/')}/v1/models"
    
    try:
        with httpx.Client(timeout=30.0, verify=False) as client:
            response = client.get(url)
            response.raise_for_status()
            models = response.json()
            
            # Filter for embedding models
            embedding_models = []
            for model in models.get('data', []):
                model_id = model.get('id', '')
                if 'embed' in model_id.lower() or 'sentence' in model_id.lower():
                    embedding_models.append(model_id)
            
            return embedding_models
    except Exception as e:
        print(f"[warn] Could not list models: {e}")
        return []


def run_vector_ingestion(
    git_url: str = None,
    git_branch: str = "main",
    docs_dir: str = "data/fsi_documents",
    docs_pattern: str = "*.txt",
    clear_first: bool = True,
    wait_for_server: bool = True,
    chunk_size: int = 1000,
    verbose: bool = True,
) -> dict:
    """
    Run the vector store ingestion pipeline.
    
    Args:
        git_url: Git repository URL for data source (None for local)
        git_branch: Git branch to use
        docs_dir: Directory containing documents (relative to data source)
        docs_pattern: Glob pattern for document files
        clear_first: Clear existing data before loading
        wait_for_server: Wait for LlamaStack to be available
        chunk_size: Maximum chunk size for documents
        verbose: Print progress
        
    Returns:
        Dict with ingestion results
    """
    if verbose:
        print("=" * 60)
        print("VECTOR STORE INGESTION")
        print("=" * 60)
    
    # Get config
    config = get_vector_store_config()
    base_url = config.get('base_url', '')
    vector_store_id = config.get('vector_store_id', '')
    embedding_model = config.get('embedding_model', '')
    
    if not base_url:
        return {'success': False, 'error': 'LLAMASTACK_BASE_URL not configured'}
    
    if verbose:
        print(f"LlamaStack URL: {base_url}")
        print(f"Vector Store ID: {vector_store_id or '(will be created)'}")
        print(f"Embedding Model: {embedding_model}")
        print(f"Data source: {git_url or 'local'}")
        print(f"Documents dir: {docs_dir}")
        print(f"Clear first: {clear_first}")
        print()
    
    # Wait for LlamaStack if needed
    if wait_for_server:
        if not wait_for_llamastack(base_url):
            return {'success': False, 'error': 'LlamaStack not available'}
    
    # List available embedding models
    if verbose:
        models = list_available_embedding_models(base_url)
        if models:
            print(f"Available embedding models: {', '.join(models[:5])}")
            if len(models) > 5:
                print(f"  ... and {len(models) - 5} more")
            print()
    
    # Create loader
    loader = FSIVectorLoader(
        base_url=base_url,
        vector_store_id=vector_store_id,
        embedding_model=embedding_model,
    )
    
    try:
        # Ensure vector store exists (create if needed)
        # First make sure the store exists
        if not loader.ensure_vector_store():
            return {'success': False, 'error': 'Failed to ensure vector store exists'}
        
        # Then clear if requested
        if clear_first:
            if verbose:
                print("Clearing vector store (delete and recreate)...")
            if not loader.clear_vector_store():
                # If clear fails, we can still proceed with existing store
                if verbose:
                    print("[warn] Could not clear, proceeding with existing store")
        
        # Get data source
        data_source = get_data_source(git_url, git_branch)
        
        # Load documents
        if verbose:
            print(f"\nLoading documents from: {docs_dir}")
        
        documents = data_source.fetch_documents(docs_dir, docs_pattern)
        
        if not documents:
            return {'success': False, 'error': f'No documents found in {docs_dir}'}
        
        if verbose:
            print(f"Found {len(documents)} documents")
        
        # Ingest documents
        result = loader.load_documents(
            documents,
            doc_type="fsi_document",
            chunk_size=chunk_size,
            verbose=verbose,
        )
        
        # Print summary
        if verbose:
            loader.print_summary()
        
        # Get the final vector store ID (in case it was created)
        final_store_id = loader.vector_store_id
        
        # Cleanup
        data_source.cleanup()
        
        if verbose:
            print("\n" + "=" * 60)
            print("VECTOR INGESTION COMPLETE!")
            print("=" * 60)
            if final_store_id and final_store_id != vector_store_id:
                print(f"\n[INFO] New vector store created: {final_store_id}")
                print(f"[INFO] Set VECTOR_STORE_ID={final_store_id} to reuse")
        
        return {
            'success': True,
            'vector_store_id': final_store_id,
            'documents': len(documents),
            'chunks': result.get('successful', 0),
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}
    
    finally:
        loader.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Vector Store Ingestion - Load FSI documents into LlamaStack"
    )
    
    parser.add_argument(
        "--git-url",
        type=str,
        default=os.environ.get('DATA_GIT_URL'),
        help="Git repository URL for data source"
    )
    parser.add_argument(
        "--git-branch",
        type=str,
        default=os.environ.get('DATA_GIT_BRANCH', 'main'),
        help="Git branch to use (default: main)"
    )
    parser.add_argument(
        "--docs-dir",
        type=str,
        default="data/fsi_documents",
        help="Directory containing documents (relative to data source)"
    )
    parser.add_argument(
        "--docs-pattern",
        type=str,
        default="*.txt",
        help="Glob pattern for document files (default: *.txt)"
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="Maximum chunk size for documents (default: 1000)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        default=True,
        help="Clear existing data before loading (default: True)"
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Don't clear existing data"
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for LlamaStack to be available"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )
    
    args = parser.parse_args()
    
    # Handle clear flag
    clear_first = not args.no_clear
    
    result = run_vector_ingestion(
        git_url=args.git_url,
        git_branch=args.git_branch,
        docs_dir=args.docs_dir,
        docs_pattern=args.docs_pattern,
        clear_first=clear_first,
        wait_for_server=not args.no_wait,
        chunk_size=args.chunk_size,
        verbose=not args.quiet,
    )
    
    if not result['success']:
        print(f"\n[ERROR] Ingestion failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
