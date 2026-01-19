"""
Sub-agents for the GraphRAG multi-agent system.

Implements the THREE FOUNDATIONAL COMPONENTS of Agentic RAG:

1. RETRIEVER AGENTS (vector_search, graph_query, cypher_expert)
   - Generic retrievers: vector_search_docs, run_cypher_query
   - Specialized retrievers: get_products_by_category, get_regulation_requirements, etc.

2. ANSWER CRITIC (answer_critic)
   - Validates if retrieved information fully answers the question
   - Generates follow-up queries if incomplete
   - Acts as quality gate before returning to user

The RETRIEVER ROUTER is implemented in the orchestrator.
"""

from .vector_search.agent import vector_search_agent
from .graph_query.agent import graph_query_agent
from .cypher_expert.agent import cypher_expert_agent
from .answer_critic.agent import answer_critic_agent

__all__ = [
    # Retriever Agents
    'vector_search_agent',
    'graph_query_agent', 
    'cypher_expert_agent',
    # Answer Critic
    'answer_critic_agent',
]
