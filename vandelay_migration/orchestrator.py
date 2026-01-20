"""
Vandelay Migration Orchestrator
================================

Routes user queries to specialized sub-agents for VCS to Vandelay Cloud migration.

GraphRAG Patterns Implemented (per Neo4j GraphRAG Pattern Catalog):
- Cypher Templates: Pre-defined queries in migration_tools.py
- Graph-Enhanced Vector Search: search_migration_docs_with_graph_context()
- Basic Retriever: Direct graph traversal for namespaces, clusters, etc.
- Pattern Matching: Cypher MATCH patterns throughout

Reference: https://graphrag.com/concepts/intro-to-graphrag/

Sub-Agents:
1. migration_graph_agent - Neo4j queries (namespaces, clusters, egress IPs)
2. migration_vector_agent - Documentation search (how-to procedures)
3. service_request_agent - MCP integration (submit/check requests)
4. answer_critic_agent - Response validation (from template)

Architecture:
    orchestrator
        ├── migration_graph_agent   ← Neo4j structured data (anti-hallucination)
        ├── migration_vector_agent  ← RAG documentation + graph context
        ├── service_request_agent   ← MCP server (firewall, DNS, certs, SSO)
        └── answer_critic_agent     ← From vandelay_search template
"""

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.agent_tool import AgentTool
from google.genai import types

# Import answer_critic from the template (reusable)
from vandelay_search.sub_agents import answer_critic_agent

# Import migration-specific agents (local)
from .migration_graph_agent import migration_graph_agent
from .migration_vector_agent import migration_vector_agent
from .service_request_agent import service_request_agent

# Import local config
from .config_loader import load_config, get_llm_config, setup_neo4j_env


# Setup Neo4j environment variables from config
setup_neo4j_env()

# Load configuration
config = load_config()
llm_config = get_llm_config(config)
orchestrator_config = config.get('orchestrator', {})

# Wrap sub-agents as tools using AgentTool
migration_graph_tool = AgentTool(agent=migration_graph_agent)
migration_vector_tool = AgentTool(agent=migration_vector_agent)
service_request_tool = AgentTool(agent=service_request_agent)
answer_critic_tool = AgentTool(agent=answer_critic_agent)

# Build tools list
agent_tools = [
    migration_graph_tool,      # Neo4j queries
    migration_vector_tool,     # Documentation RAG
    service_request_tool,      # MCP integration (KEY EXTENSION)
    answer_critic_tool,        # Response validation
]

# Create the orchestrator agent
orchestrator = Agent(
    name=orchestrator_config.get('name', 'vandelay_migration'),
    model=LiteLlm(
        model=llm_config['model'],
        api_base=llm_config['api_base'],
        api_key=llm_config['api_key'],
    ),
    instruction=orchestrator_config.get('instruction', '''
You are the Vandelay Banking Corporation Migration Assistant.

You help teams prepare for VMware OpenShift to BareMetal OpenShift migrations.
IMPORTANT: You do NOT perform actual migrations. You provide information,
guidance, and submit service requests so teams can execute migrations themselves.

## Sub-Agents Available

1. **migration_graph_agent** - For structured data queries:
   - "What cluster is payments-api migrating to?"
   - "What are the egress IPs for my namespace?"
   - "List all namespaces pending migration"
   - "What CD tool does trading-platform use?"

2. **migration_vector_agent** - For procedural documentation:
   - "How do I update my CD pipeline?"
   - "What are the steps for SSO registration?"
   - "How do I update storage classes?"
   - "What is the firewall request procedure?"

3. **service_request_agent** - For infrastructure requests (MCP):
   - "Submit a firewall request for payments-api"
   - "Check status of ticket FW-1001"
   - "Submit DNS request for my vanity URL"
   - "List open requests for my namespace"

4. **answer_critic_agent** - For validating response quality

## Routing Guidelines

| Question Type | Route To |
|---------------|----------|
| Cluster, namespace, egress IP, storage class | migration_graph_agent |
| How-to, procedures, steps, guides | migration_vector_agent |
| Submit request, check ticket, list requests | service_request_agent |
| Validate answer quality | answer_critic_agent |

## Important Rules

- Route to the CORRECT specialized agent
- For hybrid questions, call MULTIPLE agents
- NEVER loop more than 3 times
- Warn about lead times for service requests
'''),
    tools=agent_tools,
    output_key="last_response",
    generate_content_config=types.GenerateContentConfig(
        temperature=llm_config.get('temperature', 0.1)
    ),
)
