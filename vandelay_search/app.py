"""
Vandelay Search Application
============================

The App class is the top-level container for the entire ADK agent workflow.
It manages lifecycle, configuration, and state for all agents.

Benefits:
1. Centralized configuration - Single location for shared resources
2. Lifecycle management - Startup/shutdown hooks for connections
3. State scope - Clear app:* prefixed state boundary
4. Unit of deployment - Formal deployable unit for versioning/testing

Reference: https://google.github.io/adk-docs/apps/
"""

from google.adk.apps import App

from .orchestrator import orchestrator
from .config_loader import load_config, get_neo4j_config, get_memory_settings


# Load configuration
config = load_config()
memory_settings = get_memory_settings(config)

# =============================================================================
# Default Plugins
# =============================================================================

def get_default_plugins():
    """
    Get default plugins for the Vandelay Search app.
    
    Import here to avoid circular dependencies.
    """
    from .plugins import LoggingPlugin, MetricsPlugin, Neo4jLifecyclePlugin
    
    return [
        LoggingPlugin(verbose=False),
        MetricsPlugin(),
        Neo4jLifecyclePlugin(verify_on_start=True),
    ]


# =============================================================================
# Define the Vandelay Search App
# =============================================================================

# Create app without plugins first (plugins are optional)
app = App(
    name="vandelay_search",
    root_agent=orchestrator,
)


def create_app_with_plugins(plugins=None, include_defaults=True):
    """
    Create a Vandelay Search App with plugins.
    
    Args:
        plugins: Additional plugins to include
        include_defaults: Whether to include default plugins
        
    Returns:
        App instance with plugins
    """
    all_plugins = []
    
    if include_defaults:
        all_plugins.extend(get_default_plugins())
    
    if plugins:
        all_plugins.extend(plugins)
    
    return App(
        name="vandelay_search",
        root_agent=orchestrator,
        plugins=all_plugins if all_plugins else None,
    )


# =============================================================================
# Lifecycle Hooks (for resource management)
# =============================================================================

# Note: ADK App supports on_startup and on_shutdown hooks for managing
# persistent resources like database connections. These are registered
# via plugins or custom middleware.

# Example plugin for Neo4j connection management:
# 
# class Neo4jPlugin:
#     async def on_startup(self, app_context):
#         """Initialize Neo4j driver on app startup."""
#         neo4j_config = get_neo4j_config()
#         # Initialize singleton driver
#         from .sub_agents.graph_query.tools import _get_driver
#         _get_driver()  # Warm up the connection
#         print("Neo4j connection initialized")
#     
#     async def on_shutdown(self, app_context):
#         """Close Neo4j driver on app shutdown."""
#         from .sub_agents.graph_query.tools import _driver
#         if _driver:
#             _driver.close()
#         print("Neo4j connection closed")


# =============================================================================
# App-level State Keys
# =============================================================================
# Use app:* prefix for application-wide state that persists across
# all users and sessions (with persistent SessionService)

APP_STATE_KEYS = {
    'app:version': '1.0.0',
    'app:name': 'Vandelay Search',
    'app:description': 'Hybrid RAG for Vandelay Financial Corporation',
}


# =============================================================================
# Convenience function to get configured runner
# =============================================================================

def get_runner(session_service=None, memory_service=None):
    """
    Get a configured Runner for the Vandelay Search app.
    
    Args:
        session_service: Optional SessionService (defaults to InMemory)
        memory_service: Optional MemoryService (defaults to InMemory)
        
    Returns:
        Configured Runner instance
    """
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.memory import InMemoryMemoryService
    
    if session_service is None:
        session_service = InMemorySessionService()
    
    if memory_service is None:
        memory_service = InMemoryMemoryService()
    
    return Runner(
        agent=orchestrator,
        app_name=app.name,
        session_service=session_service,
        memory_service=memory_service,
    )


def get_inmemory_runner():
    """
    Get an InMemoryRunner for quick testing.
    
    Usage:
        from vandelay_search.app import get_inmemory_runner
        
        runner = get_inmemory_runner()
        response = await runner.run_debug("What products do you offer?")
    """
    try:
        from google.adk.runners import InMemoryRunner
        return InMemoryRunner(app=app)
    except ImportError:
        # Fallback for older ADK versions
        return get_runner()
