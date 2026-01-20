"""
Migration Graph Agent - Neo4j Knowledge Graph Queries
======================================================

Handles structured data queries about migration entities:
- Namespaces, Clusters, EgressIPs
- Cluster configurations (VIP, Infra Nodes, SSO)
- Migration phases and timeline
- Storage class mappings

Uses the migration-specific Neo4j schema populated from CSV data.

Data Sources:
- Namespaces: Excel export from migration portal
- Clusters: Derived from namespace mappings
- ClusterConfig: Confluence table (VIPs, Infra Nodes, SSO)
- MigrationPhases: Static timeline from documentation
- StorageClasses: Platform reference data
"""

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

from .config_loader import load_config, get_llm_config

# Import graph query tools
from .migration_tools import (
    get_migration_path,
    get_namespace_details,
    get_cluster_config,
    get_egress_ips,
    get_storage_class_mapping,
    list_migration_namespaces,
    get_migration_phase_info,
    list_namespaces_by_owner,
)


# Load configuration
config = load_config()
llm_config = get_llm_config(config)
agent_config = config.get('sub_agents', {}).get('migration_graph', {})

# Default instruction if not in config
DEFAULT_INSTRUCTION = '''
You help developers understand their application's migration from VCS to Vandelay Cloud.

## What You Can Answer

- Which cluster is my namespace migrating to?
- What will my new EgressIP be?
- What's the VIP and SM_REGHOST_HOSTNAME for my destination cluster?
- What storage class should I use instead of thin/thin-csi?
- What's the migration timeline?
- Who owns a particular namespace?

## Key Information to Provide

1. **Cluster Migration Path**: Source VCS cluster → Destination Vandelay Cloud cluster

2. **EgressIP Changes**: Show both old (VCS) and new (Vandelay Cloud) IPs
   - IMPORTANT: Remind developers that firewall rules take 14 days!
   - They need to submit requests for internal systems (SFTP, databases, MQ, etc.)

3. **Cluster Configuration**: 
   - VIP hostname and IP (for Vanity URL mapping)
   - Infra Node IPs (for F5 VIP setup if needed)
   - SM_REGHOST_HOSTNAME (for SiteMinder configuration)
   - Proxy port is 17777 (changed from 9999/7777)

4. **Storage Mapping**: 
   - thin/thin-csi → sc-ontap-nas (recommended) or dell-csm-sc

5. **Ownership**: App manager, support manager, org, management hierarchy

## Style

- Be specific with names, IPs, and cluster details
- Explain what changes mean for the developer
- Highlight action items with lead times
- If asked about procedures (how to do something), suggest using the documentation search
'''

# Graph tools list
GRAPH_TOOLS = [
    get_migration_path,
    get_namespace_details,
    get_cluster_config,
    get_egress_ips,
    get_storage_class_mapping,
    list_migration_namespaces,
    get_migration_phase_info,
    list_namespaces_by_owner,
]

# Create the graph agent
migration_graph_agent = Agent(
    name=agent_config.get('name', 'migration_graph_agent'),
    model=LiteLlm(
        model=llm_config['model'],
        api_base=llm_config['api_base'],
        api_key=llm_config['api_key'],
    ),
    instruction=agent_config.get('instruction', DEFAULT_INSTRUCTION),
    description=agent_config.get('description', 
        'Answers developer questions about their app migration - clusters, IPs, VIPs, storage, ownership'
    ),
    tools=GRAPH_TOOLS,
    output_key="graph_response",
    generate_content_config=types.GenerateContentConfig(
        temperature=llm_config.get('temperature', 0.1)
    ),
)
