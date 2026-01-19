"""
Configuration Loader for Data Ingestion
========================================

Centralized configuration loading from config.yaml.
All ingestion components use this to get their configuration.
"""

import os
from pathlib import Path
from typing import Any, Dict

import yaml


_config_cache = None
_config_mtime = None


def load_config(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load configuration from config.yaml.
    
    Returns cached config on subsequent calls, unless:
    - force_reload=True
    - config file has been modified since last load
    """
    global _config_cache, _config_mtime
    
    config_path = Path(__file__).parent / "config.yaml"
    current_mtime = config_path.stat().st_mtime if config_path.exists() else None
    
    # Reload if forced, cache is empty, or file was modified
    if force_reload or _config_cache is None or _config_mtime != current_mtime:
        with open(config_path, 'r') as f:
            _config_cache = yaml.safe_load(f)
        _config_mtime = current_mtime
    
    return _config_cache


def reload_config() -> Dict[str, Any]:
    """Force reload configuration from disk."""
    return load_config(force_reload=True)


def get_config_value(*keys, env_var: str = None, default=None) -> Any:
    """
    Get a config value with environment variable override.
    
    Args:
        *keys: Path to the value in config (e.g., 'neo4j', 'uri')
        env_var: Optional environment variable name to check first
        default: Default value if not found
    """
    # Check environment variable first
    if env_var and os.environ.get(env_var):
        return os.environ.get(env_var)
    
    # Navigate through config
    config = load_config()
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value if value is not None else default


def get_neo4j_config(config: Dict = None) -> Dict[str, str]:
    """
    Get Neo4j configuration with environment variable overrides.
    
    Returns:
        Dict with uri, username, password
    """
    if config is None:
        config = load_config()
    
    neo4j = config.get('neo4j', {})
    
    return {
        'uri': os.environ.get('NEO4J_URI', neo4j.get('uri', 'bolt://localhost:7687')),
        'username': os.environ.get('NEO4J_USERNAME', neo4j.get('username', 'neo4j')),
        'password': os.environ.get('NEO4J_PASSWORD', neo4j.get('password', 'password')),
    }


def get_vector_store_config(config: Dict = None) -> Dict[str, Any]:
    """
    Get LlamaStack Vector Store configuration with environment variable overrides.
    
    Returns:
        Dict with base_url, vector_store_id, embedding_model, etc.
    """
    if config is None:
        config = load_config()
    
    vs = config.get('vector_store', {})
    
    return {
        'provider': vs.get('provider', 'llamastack'),
        'base_url': os.environ.get('LLAMASTACK_BASE_URL', vs.get('base_url', '')),
        'vector_store_id': os.environ.get('VECTOR_STORE_ID', vs.get('vector_store_id', '')),
        'vector_store_name': os.environ.get('VECTOR_STORE_NAME', vs.get('vector_store_name', 'fsi-documents')),
        'embedding_model': vs.get('embedding_model', 'sentence-transformers/nomic-ai/nomic-embed-text-v1.5'),
        'embedding_dimension': vs.get('embedding_dimension', 768),
    }


def get_loading_config(config: Dict = None) -> Dict[str, Any]:
    """
    Get loading configuration.
    
    Returns:
        Dict with bank_name, clear_on_load, batch_size
    """
    if config is None:
        config = load_config()
    
    loading = config.get('loading', {})
    
    return {
        'bank_name': loading.get('bank_name', 'Vandelay Financial Corporation'),
        'clear_on_load': loading.get('clear_on_load', False),
        'batch_size': loading.get('batch_size', 100),
    }


def get_paths_config(config: Dict = None) -> Dict[str, str]:
    """
    Get data paths configuration.
    
    Returns:
        Dict with documents path, cypher_file path, output path
    """
    if config is None:
        config = load_config()
    
    paths = config.get('paths', {})
    
    # Get data_ingestion directory (where this file lives)
    data_ingestion_dir = Path(__file__).parent
    
    return {
        'documents': str(data_ingestion_dir / paths.get('documents', 'data/fsi_documents')),
        'cypher_file': str(data_ingestion_dir / paths.get('cypher_file', 'data/fsi_sample_data.cypher')),
        'output': str(data_ingestion_dir / paths.get('output', 'output')),
    }
