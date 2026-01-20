"""
Configuration Loader for Vandelay Migration Agent
===================================================

Loads configuration from config.yaml with environment variable overrides.
Follows the same pattern as vandelay_search for consistency.
"""

import os
from pathlib import Path
from typing import Dict, Any, Optional

import yaml


_config_cache: Optional[Dict[str, Any]] = None


def load_config(force_reload: bool = False) -> Dict[str, Any]:
    """
    Load configuration from config.yaml.
    
    Args:
        force_reload: If True, reload from disk even if cached
        
    Returns:
        Configuration dictionary
    """
    global _config_cache
    
    if _config_cache is not None and not force_reload:
        return _config_cache
    
    config_path = Path(__file__).parent / "config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        _config_cache = yaml.safe_load(f)
    
    return _config_cache


def get_llm_config(config: Dict = None) -> Dict[str, Any]:
    """Get LLM configuration with environment variable overrides."""
    if config is None:
        config = load_config()
    
    llm_config = config.get('llm', {})
    
    return {
        'model': os.environ.get('ADK_MODEL', llm_config.get('model', '')),
        'api_base': os.environ.get('OPENAI_API_BASE', llm_config.get('api_base', '')),
        'api_key': os.environ.get('OPENAI_API_KEY', llm_config.get('api_key', '')),
        'temperature': float(os.environ.get('LLM_TEMPERATURE', llm_config.get('temperature', 0.1))),
    }


def get_neo4j_config(config: Dict = None) -> Dict[str, str]:
    """Get Neo4j configuration with environment variable overrides."""
    if config is None:
        config = load_config()
    
    neo4j_config = config.get('neo4j', {})
    
    return {
        'uri': os.environ.get('NEO4J_URI', neo4j_config.get('uri', 'bolt://localhost:7687')),
        'username': os.environ.get('NEO4J_USERNAME', neo4j_config.get('username', 'neo4j')),
        'password': os.environ.get('NEO4J_PASSWORD', neo4j_config.get('password', '')),
    }


def get_vector_store_config(config: Dict = None) -> Dict[str, Any]:
    """Get vector store configuration with environment variable overrides."""
    if config is None:
        config = load_config()
    
    vs_config = config.get('vector_store', {})
    
    # Handle search_mode: defaults to 'vector' for backward compatibility
    search_mode = os.environ.get('VECTOR_STORE_SEARCH_MODE', vs_config.get('search_mode', 'vector'))
    if search_mode not in ('vector', 'keyword', 'hybrid'):
        search_mode = 'vector'
    
    # Handle ranking_alpha: weight for vector vs keyword in hybrid search
    try:
        ranking_alpha = float(os.environ.get('VECTOR_STORE_RANKING_ALPHA', vs_config.get('ranking_alpha', 0.7)))
        ranking_alpha = max(0.0, min(1.0, ranking_alpha))  # Clamp to 0-1
    except (ValueError, TypeError):
        ranking_alpha = 0.7
    
    return {
        'base_url': os.environ.get('LLAMASTACK_BASE_URL', vs_config.get('base_url', '')),
        'vector_store_id': os.environ.get(
            'MIGRATION_VECTOR_STORE_ID',
            vs_config.get('migration_vector_store_id', 'migration_docs_store')
        ),
        'verify_ssl': os.environ.get('VECTOR_STORE_VERIFY_SSL', str(vs_config.get('verify_ssl', False))).lower() == 'true',
        # Hybrid search options
        'search_mode': search_mode,
        'ranker_type': vs_config.get('ranker_type', 'weighted'),
        'ranking_alpha': ranking_alpha,
    }


def setup_neo4j_env() -> None:
    """Set Neo4j environment variables from config (for sub-agents that read from env)."""
    neo4j_config = get_neo4j_config()
    
    if 'NEO4J_URI' not in os.environ and neo4j_config.get('uri'):
        os.environ['NEO4J_URI'] = neo4j_config['uri']
    if 'NEO4J_USERNAME' not in os.environ and neo4j_config.get('username'):
        os.environ['NEO4J_USERNAME'] = neo4j_config['username']
    if 'NEO4J_PASSWORD' not in os.environ and neo4j_config.get('password'):
        os.environ['NEO4J_PASSWORD'] = neo4j_config['password']


# =============================================================================
# GraphRAG Configuration
# =============================================================================

def get_graphrag_config(config: Dict = None) -> Dict[str, Any]:
    """
    Get GraphRAG (hybrid vector-graph retrieval) configuration.
    
    Returns:
        Dict with enable_graph_context, max_entity_lookups, 
        max_connections_per_entity, entity_patterns
    """
    if config is None:
        config = load_config()
    
    graphrag = config.get('graphrag', {})
    
    return {
        'enable_graph_context': graphrag.get('enable_graph_context', True),
        'max_entity_lookups': graphrag.get('max_entity_lookups', 10),
        'max_connections_per_entity': graphrag.get('max_connections_per_entity', 5),
        'entity_patterns': graphrag.get('entity_patterns', {}),
    }


def get_entity_patterns(config: Dict = None) -> Dict[str, list]:
    """
    Get entity patterns for GraphRAG entity extraction.
    
    Returns:
        Dict mapping category -> list of patterns
        e.g., {'namespaces': ['payments-api', ...], 'cd_tools': ['argocd', ...]}
    """
    graphrag_config = get_graphrag_config(config)
    return graphrag_config.get('entity_patterns', {})
