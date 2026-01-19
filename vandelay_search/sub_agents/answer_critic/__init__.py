"""
Answer Critic Sub-Agent
========================

The third foundational component of Agentic RAG.
Validates if retrieved information fully answers the question.
"""

from .agent import answer_critic_agent
from .tools import CRITIC_TOOLS, evaluate_completeness

__all__ = ['answer_critic_agent', 'CRITIC_TOOLS', 'evaluate_completeness']
