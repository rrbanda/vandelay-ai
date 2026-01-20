"""
GraphRAG Orchestrator (Retriever Router)
==========================================

Root orchestrator that implements AGENTIC RAG with GraphRAG patterns.
ALL configuration loaded from config.yaml - NO hardcoding.

GraphRAG Patterns Implemented (per Neo4j GraphRAG Pattern Catalog):
- Cypher Templates: Pre-defined queries in graph_query tools
- Graph-Enhanced Vector Search: vector_search_with_graph_context()
- Basic Retriever: Direct graph traversal tools
- Pattern Matching: Cypher MATCH patterns throughout

Reference: https://graphrag.com/concepts/intro-to-graphrag/

Three Foundational Components:
1. RETRIEVER ROUTER: This orchestrator - routes to appropriate retrievers
2. RETRIEVER AGENTS: vector_search, graph_query, cypher_expert
3. ANSWER CRITIC: Validates answers and generates follow-ups

State Management:
- Uses session.state for tracking retrieval history, quality scores
- Callbacks for before/after agent invocation
- Proper key prefixes (temp:, user:, session)

Memory (Long-Term Knowledge):
- Uses MemoryService for cross-session knowledge
- load_memory tool for retrieving past conversations
- Auto-save sessions to memory after completion

Pattern: https://blog.langchain.dev/choosing-the-right-multi-agent-architecture/
Reference: 
- State: https://google.github.io/adk-docs/sessions/state/
- Memory: https://google.github.io/adk-docs/sessions/memory/
"""

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool
from google.genai import types

from .config_loader import load_config, get_llm_config, get_agentic_loop_config, setup_neo4j_env
from .callbacks import before_agent_call, after_agent_call
from .memory_config import get_memory_tools, get_preload_memory_tool
from .sub_agents import (
    vector_search_agent,
    graph_query_agent,
    cypher_expert_agent,
    answer_critic_agent,
)


# Setup Neo4j environment variables from config
setup_neo4j_env()

# Load ALL configuration from config.yaml
config = load_config()
llm_config = get_llm_config(config)
orchestrator_config = config.get('orchestrator', {})
loop_config = get_agentic_loop_config(config)

# Wrap sub-agents as tools using AgentTool
vector_search_tool = AgentTool(agent=vector_search_agent)
graph_query_tool = AgentTool(agent=graph_query_agent)
cypher_expert_tool = AgentTool(agent=cypher_expert_agent)
answer_critic_tool = AgentTool(agent=answer_critic_agent)

# Get memory tools (if available)
memory_tools = get_memory_tools()
preload_memory_tool = get_preload_memory_tool()

# Build instruction with state template placeholders
# ADK will inject state values using {key} syntax
base_instruction = orchestrator_config.get('instruction', '')

# Add state and memory aware context to instruction
# Session-scoped keys (visible in ADK web UI)
# The ? suffix makes them optional (won't error if not set)
state_aware_instruction = base_instruction + """

## Current Session Context
You have access to session state for tracking your work:
- Query count: {query_count?}
- Current query: {current_query?}
- Last answer score: {last_answer_score?}
- Retrieval history: {retrieval_history?}
- Tools used: {tools_used?}

Use this context to:
1. Avoid repeating the same retrieval queries
2. Build on previous results with follow-up queries
3. Know when to stop iterating (quality >= 80 or max 3 iterations)

## Long-Term Memory
You have access to long-term memory from past conversations.
If the user asks about something that might have been discussed before,
use the load_memory tool to search past conversations.

User preferences and history (if available):
- User name: {user:name?}
- User preferences: {user:preferences?}
"""

# Build tools list
agent_tools = [
    vector_search_tool,
    graph_query_tool,
    cypher_expert_tool,
    answer_critic_tool,
]

# Add memory tools if available
if preload_memory_tool:
    agent_tools.append(preload_memory_tool)
agent_tools.extend(memory_tools)

# Create the orchestrator agent with callbacks
# ALL instruction comes from config.yaml - no hardcoding
#
# NOTE: We use AgentTool pattern (tools list) for explicit routing to sub-agents.
# The sub_agents parameter is for LLM-driven delegation/transfer, which we don't use.
# Using both would be redundant and potentially cause duplicate calls.
# See: https://google.github.io/adk-docs/agents/multi-agents/
orchestrator = Agent(
    name=orchestrator_config.get('name', 'graphrag'),
    model=LiteLlm(
        model=llm_config['model'],
        api_base=llm_config['api_base'],
        api_key=llm_config['api_key'],
    ),
    instruction=state_aware_instruction,
    tools=agent_tools,
    # Callbacks for state management
    before_agent_callback=before_agent_call,
    after_agent_callback=after_agent_call,
    # Output key saves final response to state
    output_key="last_response",
    generate_content_config=types.GenerateContentConfig(
        temperature=llm_config.get('temperature', 0.1)
    ),
)
