"""
Vandelay Migration - Entry Point
==================================

This is the main entry point for ADK web discovery.
Exports the orchestrator as the root agent.

IMPORTANT: For ADK web UI to display state, this module must export
either `root_agent` or `agent` at the module level.

Architecture:
    orchestrator (root)
        ├── vector_search_agent (from template)
        ├── graph_query_agent (from template)
        ├── cypher_expert_agent (from template)
        ├── answer_critic_agent (from template)
        └── migration_agent (local, with PlanReActPlanner)
"""

from .orchestrator import orchestrator
from .config_loader import load_config


# Load config for app name
config = load_config()
app_name = config.get('orchestrator', {}).get('name', 'vandelay_migration')

# Export the orchestrator as root_agent (required for ADK web)
root_agent = orchestrator

# Also export as 'agent' for compatibility
agent = orchestrator
