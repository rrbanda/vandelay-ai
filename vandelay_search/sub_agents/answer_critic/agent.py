"""
Answer Critic Sub-Agent
========================

Validates if retrieved information fully answers the question.
All configuration loaded from config.yaml - no hardcoding.
"""

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

from ...config_loader import load_config, get_llm_config, get_answer_critic_config
from .tools import CRITIC_TOOLS


# Load configuration
config = load_config()
llm_config = get_llm_config(config)
critic_config = get_answer_critic_config(config)

# Create the Answer Critic agent
answer_critic_agent = Agent(
    name=critic_config.get('name', 'answer_critic_agent'),
    model=LiteLlm(
        model=llm_config['model'],
        api_base=llm_config['api_base'],
        api_key=llm_config['api_key'],
    ),
    instruction=critic_config.get('instruction', ''),
    tools=CRITIC_TOOLS,
    output_key="critic_response",  # Save response to state
    generate_content_config=types.GenerateContentConfig(
        temperature=0.1  # Low temperature for consistent evaluation
    ),
)
