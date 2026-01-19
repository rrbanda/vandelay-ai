"""
Vandelay Search - Multi-Agent RAG System
==========================================

Vandelay Financial Corporation AI Assistant using hybrid RAG:
- Vector Search (semantic) via LlamaStack
- Graph RAG (structured) via Neo4j Knowledge Graph
- Cypher Expert (custom queries)
- Answer Critic (quality validation)

Architecture:
    orchestrator (root)
        ├── vector_search_agent - Semantic search on documents
        ├── graph_query_agent - Structured graph queries
        ├── cypher_expert_agent - Custom Cypher queries
        └── answer_critic_agent - Answer validation

All configuration from config.yaml - no hardcoding.
"""

from . import agent

__all__ = ['agent']
