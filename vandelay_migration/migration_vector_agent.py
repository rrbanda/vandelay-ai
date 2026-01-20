"""
Migration Vector Agent - Documentation Search (RAG)
====================================================

Handles unstructured documentation queries:
- How-to procedures for migration tasks
- CD pipeline update steps
- Firewall request procedures
- SSO registration guides
- Storage migration guides

Uses the migration-specific vector store (MIGRATION_VECTOR_STORE_ID).
"""

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

from .config_loader import load_config, get_llm_config

# Import vector search tools (hybrid preferred)
from .migration_tools import (
    search_migration_docs_with_graph_context,
    search_migration_docs,
)


# Load configuration
config = load_config()
llm_config = get_llm_config(config)
agent_config = config.get('sub_agents', {}).get('migration_vector', {})

# Default instruction if not in config
DEFAULT_INSTRUCTION = '''
You help developers understand HOW to complete migration tasks.

## What You Answer

- How do I update my CD pipeline?
- What are the steps for SSO registration?
- How do I submit a firewall request?
- What's the procedure for updating storage classes?

## Available Tools

1. **search_migration_docs_with_graph_context** (PREFERRED)
   - Searches documentation AND enriches with knowledge graph context
   - Returns: documents + entities_mentioned + graph_context
   - Use this for most queries - it provides richer context

2. **search_migration_docs** (fallback)
   - Vector search only, no graph enrichment
   - Use if you only need raw documentation

## How to Use Graph Context

When search_migration_docs_with_graph_context returns results:
- `documents`: The relevant documentation chunks
- `entities_mentioned`: Namespaces, CD tools, storage classes found in docs
- `graph_context`: Specific data from knowledge graph (clusters, IPs, phases)

Combine documentation procedures with specific graph data to give
personalized answers (e.g., "For payments-api, you'll migrate to NAMOSESWD20D...").

## Response Format

- Provide clear step-by-step instructions
- Include prerequisites
- Mention lead times for requests
- Warn about common pitfalls
- Include SPECIFIC values from graph_context when available

## Style

- Be practical and actionable
- Number your steps
- Include specific details (portal names, menu paths)
'''

# Vector tools list (hybrid GraphRAG preferred)
VECTOR_TOOLS = [
    search_migration_docs_with_graph_context,  # Preferred: hybrid
    search_migration_docs,                      # Fallback: vector only
]

# Create the vector agent
migration_vector_agent = Agent(
    name=agent_config.get('name', 'migration_vector_agent'),
    model=LiteLlm(
        model=llm_config['model'],
        api_base=llm_config['api_base'],
        api_key=llm_config['api_key'],
    ),
    instruction=agent_config.get('instruction', DEFAULT_INSTRUCTION),
    description=agent_config.get('description',
        'Provides step-by-step procedures and how-to guides for migration tasks'
    ),
    tools=VECTOR_TOOLS,
    output_key="vector_response",
    generate_content_config=types.GenerateContentConfig(
        temperature=llm_config.get('temperature', 0.1)
    ),
)
