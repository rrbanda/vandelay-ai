"""
Configuration Loader
====================

Centralized configuration loading from config.yaml.
All agents and tools use this to get their configuration.
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
        *keys: Path to the value in config (e.g., 'llm', 'model')
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


def get_llm_config(config: Dict = None) -> Dict[str, Any]:
    """
    Get LLM configuration with environment variable overrides.
    
    Returns:
        Dict with model, api_base, api_key, temperature
    """
    if config is None:
        config = load_config()
    
    llm = config.get('llm', {})
    
    return {
        'model': os.environ.get('ADK_MODEL', llm.get('model', 'openai/gpt-4')),
        'api_base': os.environ.get('OPENAI_API_BASE', llm.get('api_base', '')),
        'api_key': os.environ.get('OPENAI_API_KEY', llm.get('api_key', 'not-needed')),
        'temperature': llm.get('temperature', 0.1),
    }


def get_neo4j_config(config: Dict = None) -> Dict[str, str]:
    """
    Get Neo4j configuration with environment variable overrides.
    
    Environment variables take precedence over config.yaml values.
    For security, passwords should be set via NEO4J_PASSWORD environment variable.
    
    Returns:
        Dict with uri, username, password
        
    Raises:
        ValueError: If no password is configured (neither env var nor config)
    """
    if config is None:
        config = load_config()
    
    neo4j = config.get('neo4j', {})
    
    # Get password from env var first, fall back to config
    password = os.environ.get('NEO4J_PASSWORD') or neo4j.get('password', '')
    
    # Warn if no password is set (but don't fail - might be auth-disabled Neo4j)
    if not password:
        import logging
        logging.getLogger(__name__).warning(
            "No Neo4j password configured. Set NEO4J_PASSWORD environment variable "
            "or update config.yaml for authenticated Neo4j instances."
        )
    
    return {
        'uri': os.environ.get('NEO4J_URI', neo4j.get('uri', 'bolt://localhost:7687')),
        'username': os.environ.get('NEO4J_USERNAME', neo4j.get('username', 'neo4j')),
        'password': password,
    }


def setup_neo4j_env():
    """
    Set Neo4j environment variables from config.
    
    Call this early to ensure tools.py picks up the right values.
    """
    neo4j_config = get_neo4j_config()
    os.environ.setdefault('NEO4J_URI', neo4j_config['uri'])
    os.environ.setdefault('NEO4J_USERNAME', neo4j_config['username'])
    os.environ.setdefault('NEO4J_PASSWORD', neo4j_config['password'])


def get_vector_store_config(config: Dict = None) -> Dict[str, Any]:
    """
    Get LlamaStack Vector Store configuration with environment variable overrides.
    
    Returns:
        Dict with base_url, vector_store_id, embedding_model, verify_ssl, etc.
    """
    if config is None:
        config = load_config()
    
    vs = config.get('vector_store', {})
    
    # Handle verify_ssl: defaults to True for security
    # Can be overridden via VECTOR_STORE_VERIFY_SSL=false for dev environments
    verify_ssl_env = os.environ.get('VECTOR_STORE_VERIFY_SSL', '').lower()
    if verify_ssl_env in ('false', '0', 'no'):
        verify_ssl = False
    elif verify_ssl_env in ('true', '1', 'yes'):
        verify_ssl = True
    else:
        verify_ssl = vs.get('verify_ssl', True)
    
    return {
        'provider': vs.get('provider', 'llamastack'),
        'base_url': os.environ.get('LLAMASTACK_BASE_URL', vs.get('base_url', '')),
        'vector_store_id': os.environ.get('VECTOR_STORE_ID', vs.get('vector_store_id', '')),
        'vector_store_name': vs.get('vector_store_name', ''),
        'embedding_model': vs.get('embedding_model', 'all-MiniLM-L6-v2'),
        'embedding_dimension': vs.get('embedding_dimension', 384),
        'similarity_top_k': vs.get('similarity_top_k', 5),
        'verify_ssl': verify_ssl,
    }


def get_extraction_config(config: Dict = None) -> Dict[str, Any]:
    """
    Get extraction configuration with environment variable overrides.
    
    Returns:
        Dict with model, temperature, max_workers, timeout, prompts, document_types
    """
    if config is None:
        config = load_config()
    
    ext = config.get('extraction', {})
    
    return {
        'model': os.environ.get('EXTRACTION_MODEL', ext.get('model', 'gpt-4o')),
        'temperature': float(os.environ.get('EXTRACTION_TEMPERATURE', ext.get('temperature', 0))),
        'max_workers': int(os.environ.get('EXTRACTION_MAX_WORKERS', ext.get('max_workers', 5))),
        'timeout': int(os.environ.get('EXTRACTION_TIMEOUT', ext.get('timeout', 120))),
        'prompts': ext.get('prompts', {}),
        'document_types': ext.get('document_types', {}),
    }


def get_extraction_prompt(prompt_type: str, config: Dict = None) -> str:
    """
    Get an extraction prompt by type.
    
    Args:
        prompt_type: One of 'product', 'regulation', 'risk'
        config: Optional config dict
        
    Returns:
        The prompt template string
    """
    ext_config = get_extraction_config(config)
    prompts = ext_config.get('prompts', {})
    return prompts.get(prompt_type, '')


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
        Dict with documents path, extracted_data path
    """
    if config is None:
        config = load_config()
    
    paths = config.get('paths', {})
    
    return {
        'documents': paths.get('documents', 'data/fsi_documents'),
        'extracted_data': paths.get('extracted_data', 'data'),
    }


def get_domain_constants(config: Dict = None) -> Dict[str, Any]:
    """
    Get domain constants (risk levels, product categories, etc.).
    
    Returns:
        Dict with all domain constants
    """
    if config is None:
        config = load_config()
    
    return config.get('domain', {})


# =============================================================================
# Answer Critic Configuration
# =============================================================================

def get_answer_critic_config(config: Dict = None) -> Dict[str, Any]:
    """
    Get Answer Critic configuration.
    
    Returns:
        Dict with name, description, instruction, thresholds, prompts
    """
    if config is None:
        config = load_config()
    
    return config.get('answer_critic', {})


def get_critic_instruction(config: Dict = None) -> str:
    """Get the Answer Critic instruction prompt."""
    critic_config = get_answer_critic_config(config)
    return critic_config.get('instruction', '')


def get_critic_evaluation_prompt(config: Dict = None) -> str:
    """Get the Answer Critic evaluation prompt template."""
    critic_config = get_answer_critic_config(config)
    return critic_config.get('evaluation_prompt', '')


def get_critic_thresholds(config: Dict = None) -> Dict[str, int]:
    """Get the Answer Critic score thresholds."""
    critic_config = get_answer_critic_config(config)
    return critic_config.get('thresholds', {
        'complete': 80,
        'partial': 60,
        'retry': 40,
    })


# =============================================================================
# Agentic Loop Configuration
# =============================================================================

def get_agentic_loop_config(config: Dict = None) -> Dict[str, Any]:
    """
    Get Agentic RAG loop configuration.
    
    Returns:
        Dict with max_iterations, enable_critic, routing_hints, etc.
    """
    if config is None:
        config = load_config()
    
    loop_config = config.get('agentic_loop', {})
    
    return {
        'max_iterations': loop_config.get('max_iterations', 3),
        'enable_critic': loop_config.get('enable_critic', True),
        'enable_quick_check': loop_config.get('enable_quick_check', True),
        'quick_check_min_results': loop_config.get('quick_check_min_results', 1),
        'routing_hints': loop_config.get('routing_hints', {}),
        'synthesis_prompt': loop_config.get('synthesis_prompt', ''),
    }


def get_routing_hints(config: Dict = None) -> Dict[str, str]:
    """Get tool routing hints for query keywords."""
    loop_config = get_agentic_loop_config(config)
    return loop_config.get('routing_hints', {})


def get_synthesis_prompt(config: Dict = None) -> str:
    """Get the response synthesis prompt template."""
    loop_config = get_agentic_loop_config(config)
    return loop_config.get('synthesis_prompt', '')


# =============================================================================
# Specialized Tools Configuration
# =============================================================================

def get_specialized_tools_config(config: Dict = None) -> Dict[str, Any]:
    """
    Get specialized retriever tools configuration.
    
    Returns:
        Dict of tool_name -> {description, cypher, parameters}
    """
    if config is None:
        config = load_config()
    
    return config.get('specialized_tools', {})


def get_specialized_tool(tool_name: str, config: Dict = None) -> Dict[str, Any]:
    """
    Get a specific specialized tool configuration.
    
    Args:
        tool_name: Name of the tool (e.g., 'get_products_by_category')
        
    Returns:
        Dict with description, cypher, parameters
    """
    tools = get_specialized_tools_config(config)
    return tools.get(tool_name, {})


# =============================================================================
# Memory Service Configuration
# =============================================================================

def get_memory_config(config: Dict = None) -> Dict[str, Any]:
    """
    Get memory service configuration.
    
    Note: Using InMemoryMemoryService since we use LlamaStack (not Vertex AI).
    
    Returns:
        Dict with provider and settings
    """
    if config is None:
        config = load_config()
    
    memory_config = config.get('memory', {})
    
    return {
        'provider': memory_config.get('provider', 'inmemory'),
        'settings': memory_config.get('settings', {}),
    }


def get_memory_settings(config: Dict = None) -> Dict[str, Any]:
    """
    Get memory behavior settings.
    
    Returns:
        Dict with auto_save_sessions, preload_memories, max_memories_per_query
    """
    memory_config = get_memory_config(config)
    settings = memory_config.get('settings', {})
    
    return {
        'auto_save_sessions': settings.get('auto_save_sessions', True),
        'preload_memories': settings.get('preload_memories', True),
        'max_memories_per_query': settings.get('max_memories_per_query', 5),
    }
