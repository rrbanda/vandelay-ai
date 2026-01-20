"""
Vandelay Migration - Multi-Agent Migration Assistant
======================================================

VMware to BareMetal OpenShift migration assistant.

This agent EXTENDS the vandelay_search template by:
1. Importing reusable sub-agents (vector_search, graph_query, cypher_expert, answer_critic)
2. Adding a migration-specific sub-agent with PlanReActPlanner
3. Using migration-specific graph data and vector documents

Architecture:
    orchestrator (root)
        ├── vector_search_agent - From template
        ├── graph_query_agent - From template
        ├── cypher_expert_agent - From template
        ├── answer_critic_agent - From template
        └── migration_agent - Migration specialist

All configuration from config.yaml - no hardcoding.
"""

from . import agent

__all__ = ['agent']
