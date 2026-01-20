# Vandelay Migration - VCS to Vandelay Cloud Migration Assistant

An AI assistant for VCS 1.0 to Vandelay Cloud (BareMetal OpenShift) migrations, built with Google ADK.

## Overview

This agent helps application teams migrate from VCS 1.0 (VMware) to Vandelay Cloud (BareMetal OpenShift) by providing:

- **Migration Path Lookup**: Source/destination cluster mappings, EgressIP changes
- **Documentation Search**: Procedural guides for CD tools, certificates, SSO, storage
- **Service Requests**: Submit firewall, DNS, certificate, and SSO requests via MCP

## GraphRAG Pattern Implementation

This agent implements GraphRAG patterns as defined by the [Neo4j GraphRAG Pattern Catalog](https://graphrag.com/concepts/intro-to-graphrag/):

> *"GraphRAG is Retrieval Augmented Generation (RAG) using a Knowledge Graph."*

### Implemented Patterns

| Pattern | Implementation | Description |
|---------|----------------|-------------|
| **[Cypher Templates](https://graphrag.com/reference/retrieval/cypher-templates/)** | `migration_tools.py` | Pre-defined queries for namespaces, clusters, egress IPs, storage classes |
| **[Graph-Enhanced Vector Search](https://graphrag.com/reference/retrieval/graph-enhanced-vector-search/)** | `search_migration_docs_with_graph_context()` | Vector search + graph context for mentioned entities |
| **[Basic Retriever](https://graphrag.com/reference/retrieval/basic-retriever/)** | `get_migration_path()`, `get_cluster_config()`, etc. | Direct graph traversal |
| **[Pattern Matching](https://graphrag.com/reference/retrieval/pattern-matching/)** | All Cypher queries | MATCH patterns for structured data |

### What This Is NOT

- **Not Microsoft GraphRAG**: No community detection (Leiden algorithm) or hierarchical summaries
- **Not LLM-extracted entities**: Knowledge graph built from structured CSV data, not extracted from text
- **Not Global Search**: No corpus-wide thematic summaries

### Anti-Hallucination Design

For migration data, accuracy is critical. Our approach ensures:

1. **Graph tools return exact database values** - Cluster configs, EgressIPs, phase dates come directly from Neo4j
2. **CSV → Graph ingestion** - Tabular data from migration portal is loaded as structured graph nodes
3. **Cypher Templates** - Queries are pre-defined, not LLM-generated

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Vandelay Migration Agent                      │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Orchestrator                              │ │
│  │           Routes queries to sub-agents                       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌───────────────────────────┴────────────────────────────────┐  │
│  │                     Sub-Agents                              │  │
│  ├─────────────────┬─────────────────┬────────────────────────┤  │
│  │ migration_graph │ migration_vector│  service_request       │  │
│  │ (Neo4j data)    │ (Doc search)    │  (MCP server)          │  │
│  └─────────────────┴─────────────────┴────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────┴────────────────────────────────┐  │
│  │                     Data Sources                            │  │
│  ├─────────────────┬─────────────────┬────────────────────────┤  │
│  │ Neo4j Graph     │ LlamaStack      │  MCP Service Request   │  │
│  │ (from CSV)      │ Vector Store    │  Server                │  │
│  └─────────────────┴─────────────────┴────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Graph Schema

The migration knowledge graph is built from CSV exports:

```
(Namespace)-[:MIGRATES_FROM]->(SourceCluster)
(Namespace)-[:MIGRATES_TO]->(DestinationCluster)
(Namespace)-[:HAS_SOURCE_EGRESS]->(EgressIP)
(Namespace)-[:HAS_DEST_EGRESS]->(EgressIP)
(Namespace)-[:SCHEDULED_IN]->(MigrationPhase)
(SourceCluster)-[:MAPS_TO]->(DestinationCluster)
(DestinationCluster)-[:HAS_CONFIG]->(ClusterConfig)
(*Cluster)-[:HAS_STORAGE_CLASS]->(StorageClass)
```

### Data Sources (CSV)

| File | Graph Nodes | Description |
|------|-------------|-------------|
| `namespaces.csv` | Namespace, EgressIP | Application namespaces from migration portal |
| `cluster_mappings.csv` | SourceCluster, DestinationCluster | VCS → Vandelay Cloud mappings |
| `cluster_configs.csv` | ClusterConfig | VIP, infra nodes, SSO configuration |
| `migration_phases.csv` | MigrationPhase | Timeline (DEV, UAT, PROD waves) |
| `storage_classes.csv` | StorageClass | Storage provisioner mappings |

## Example Queries

| Query | Tool Used | Data Source |
|-------|-----------|-------------|
| "What cluster is payments-api migrating to?" | `get_migration_path()` | Neo4j |
| "What's the VIP for NAMOSESWD20D?" | `get_cluster_config()` | Neo4j |
| "What are the new EgressIPs for auth-gateway?" | `get_egress_ips()` | Neo4j |
| "How do I update my ArgoCD pipeline?" | `search_migration_docs()` | Vector Store |
| "Submit a firewall request for payments-api" | `submit_firewall_request()` | MCP Server |

## Quick Start

### 1. Ingest Migration Data

```bash
# Load CSV data into Neo4j
python -m data_ingestion.ingest_migration_graph --clear

# Load documentation into vector store
python -m data_ingestion.ingest_migration_vector --clear
```

### 2. Run the Agent

```bash
cd vandelay_migration
adk web --port 8001
```

## Project Structure

```
vandelay_migration/
├── orchestrator.py          # Main orchestrator
├── migration_graph_agent.py # Neo4j queries sub-agent
├── migration_vector_agent.py# Vector search sub-agent
├── service_request_agent.py # MCP integration sub-agent
├── migration_tools.py       # All tools (graph, vector, MCP)
├── config.yaml              # Configuration
└── config_loader.py         # Config utilities
```

## Credits

- Built with [Google Agent Development Kit](https://google.github.io/adk-docs/)
- GraphRAG patterns from [Neo4j GraphRAG Pattern Catalog](https://graphrag.com/concepts/intro-to-graphrag/)
- MCP integration for service requests
