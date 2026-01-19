"""
Cypher Expert Sub-Agent
========================

Specialized agent for custom Cypher queries on Neo4j.
"""

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

from ...config_loader import load_config, get_llm_config
from .tools import CYPHER_TOOLS


# Load configuration
config = load_config()
llm_config = get_llm_config(config)
agent_config = config.get('sub_agents', {}).get('cypher_expert', {})

# Create the sub-agent
cypher_expert_agent = Agent(
    name=agent_config.get('name', 'cypher_expert_agent'),
    model=LiteLlm(
        model=llm_config['model'],
        api_base=llm_config['api_base'],
        api_key=llm_config['api_key'],
    ),
    instruction=agent_config.get('instruction', ''),
    tools=CYPHER_TOOLS,
    output_key="cypher_response",  # Save response to state
    generate_content_config=types.GenerateContentConfig(
        temperature=llm_config.get('temperature', 0.1)
    ),
)
