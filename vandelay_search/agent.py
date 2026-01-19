"""
Vandelay Search - Entry Point
==============================

This is the main entry point for ADK web discovery.
Exports the orchestrator as the root agent.

IMPORTANT: For ADK web UI to display state, this module must export
either `root_agent` or `agent` at the module level.

Architecture:
    orchestrator (root)
        ├── vector_search_agent (semantic search)
        ├── graph_query_agent (structured queries) 
        ├── cypher_expert_agent (custom Cypher)
        └── answer_critic_agent (validates answers)
"""

from .orchestrator import orchestrator
from .config_loader import load_config


# Load config for app name
config = load_config()
app_name = config.get('orchestrator', {}).get('name', 'vandelay_search')

# Export the orchestrator as root_agent (required for ADK web)
root_agent = orchestrator

# Also export as 'agent' for compatibility
agent = orchestrator

# Note: App is now in app.py to avoid circular imports with plugins
# If you need App, import from .app import app
