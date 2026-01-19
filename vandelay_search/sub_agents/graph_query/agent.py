"""
Graph Query Sub-Agent
======================

Specialized agent for structured queries on the FSI knowledge graph.
"""

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

from ...config_loader import load_config, get_llm_config
from .tools import GRAPH_TOOLS


# Load configuration
config = load_config()
llm_config = get_llm_config(config)
agent_config = config.get('sub_agents', {}).get('graph_query', {})

# Create the sub-agent
graph_query_agent = Agent(
    name=agent_config.get('name', 'graph_query_agent'),
    model=LiteLlm(
        model=llm_config['model'],
        api_base=llm_config['api_base'],
        api_key=llm_config['api_key'],
    ),
    instruction=agent_config.get('instruction', ''),
    tools=GRAPH_TOOLS,
    output_key="graph_query_response",  # Save response to state
    generate_content_config=types.GenerateContentConfig(
        temperature=llm_config.get('temperature', 0.1)
    ),
)
