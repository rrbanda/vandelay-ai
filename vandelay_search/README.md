# Vandelay Search - FSI GraphRAG Agent

A production-ready GraphRAG agent built with Google ADK for FSI (Financial Services Industry) knowledge.

## Overview

This agent combines **vector search** and **graph traversal** to provide intelligent answers about banking products, regulations, and risk management.

## GraphRAG Pattern Implementation

This agent implements GraphRAG patterns as defined by the [Neo4j GraphRAG Pattern Catalog](https://graphrag.com/concepts/intro-to-graphrag/):

> *"GraphRAG is Retrieval Augmented Generation (RAG) using a Knowledge Graph."*

### Implemented Patterns

| Pattern | Implementation | Description |
|---------|----------------|-------------|
| **[Cypher Templates](https://graphrag.com/reference/retrieval/cypher-templates/)** | `graph_query/tools.py`, `config.yaml` | Pre-defined, parameterized Cypher queries for common lookups (products, regulations, portfolios) |
| **[Graph-Enhanced Vector Search](https://graphrag.com/reference/retrieval/graph-enhanced-vector-search/)** | `vector_search_with_graph_context()` | Vector search followed by graph context expansion for mentioned entities |
| **[Basic Retriever](https://graphrag.com/reference/retrieval/basic-retriever/)** | `get_all_products()`, `get_regulation_details()`, etc. | Direct graph traversal from entry points |
| **[Pattern Matching](https://graphrag.com/reference/retrieval/pattern-matching/)** | All Cypher queries | MATCH patterns for structured data retrieval |

### What This Is NOT

To be precise about terminology:

- **Not Microsoft GraphRAG**: We do not implement community detection (Leiden algorithm) or hierarchical community summaries
- **Not LLM-extracted entities**: Our knowledge graph is built from structured data (not extracted from unstructured text via LLM)
- **Not Global Search**: We don't have corpus-wide thematic summaries

### Why This Matters (Anti-Hallucination)

The key benefit of our GraphRAG approach for structured data:

1. **Graph query tools return exact database values** - no LLM generation of facts
2. **Cypher Templates ensure deterministic retrieval** - queries are pre-defined, not generated
3. **Hybrid retrieval** combines semantic understanding (vector) with precise lookups (graph)

This prevents hallucination on structured data like product details, fees, regulatory requirements, and customer information.

### Use Case: Vandelay Financial Corporation AI Assistant

- **Product Queries**: Find checking accounts, mortgages, credit cards
- **Compliance Queries**: Basel III requirements, AML/KYC regulations
- **Risk Analysis**: Portfolio risk, counterparty exposure, mitigation strategies
- **Document Search**: Semantic search across banking documents

## IMPORTANT: Prerequisites

**Before running this agent, you must ingest data first!**

The agent queries a Neo4j Knowledge Graph and LlamaStack Vector Store that must be populated with FSI data.

```bash
# From the repository root, run data ingestion

# Clear existing data and load FSI knowledge graph
python -m data_ingestion.ingest_graph --clear

# Clear existing data and load FSI documents into vector store
python -m data_ingestion.ingest_vector --clear
```

See `data_ingestion/README.md` for detailed instructions and environment variable configuration.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Vandelay Search Agent                     │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    Orchestrator                          │ │
│  │           Routes queries to sub-agents                   │ │
│  └─────────────────────────────────────────────────────────┘ │
│                              │                                │
│  ┌───────────────────────────┴────────────────────────────┐  │
│  │                     Sub-Agents                          │  │
│  ├────────────────┬────────────────┬─────────────────────┤  │
│  │ vector_search  │  graph_query   │  cypher_expert      │  │
│  │ (semantic)     │  (structured)  │  (custom queries)   │  │
│  └────────────────┴────────────────┴─────────────────────┘  │
│                              │                                │
│  ┌───────────────────────────┴────────────────────────────┐  │
│  │                     Data Stores                         │  │
│  ├────────────────────────────┬───────────────────────────┤  │
│  │    Neo4j Knowledge Graph   │   LlamaStack Vector Store │  │
│  │    (Products, Regulations) │   (Document Chunks)       │  │
│  └────────────────────────────┴───────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Prerequisites

- Python 3.10+
- Neo4j database (populated via data_ingestion)
- OpenAI-compatible LLM endpoint

### 2. Install Dependencies

```bash
pip install google-adk litellm neo4j httpx
```

### 3. Configure Environment

```bash
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your-password"

# LLM Configuration
export OPENAI_API_BASE="https://your-llm-endpoint/v1"
export OPENAI_API_KEY="your-api-key"
export ADK_MODEL="openai/your-model-name"
```

### 4. Ingest Data (REQUIRED)

```bash
# From repository root - clear existing data and load FSI data
python -m data_ingestion.ingest_graph --clear
python -m data_ingestion.ingest_vector --clear
```

### 5. Run Agent

#### Option A: Local Development

```bash
cd vandelay_search
adk web --port 8000
```

Then open http://localhost:8000 in your browser.

#### Option B: Container with Podman Desktop

```bash
# From repository root
cd vandelay-ai

# Build the container image
podman build -t vandelay-search:latest -f vandelay_search/Dockerfile vandelay_search/

# Run with podman kube play (recommended)
podman kube play openshift/vandelay-search/pod.yaml

# Or run directly
podman run -p 8000:8000 \
  -e NEO4J_URI=bolt://host.containers.internal:7687 \
  -e NEO4J_USERNAME=neo4j \
  -e NEO4J_PASSWORD=your-password \
  vandelay-search:latest
```

Then open http://localhost:8000 in your browser.

See `openshift/vandelay-search/README.md` for full deployment options (Podman Desktop and OpenShift).

## Project Structure

```
vandelay_search/
├── __init__.py          # Exports root_agent
├── agent.py             # Agent entry point
├── app.py               # ADK App configuration
├── orchestrator.py      # Main orchestrator agent
├── config.yaml          # Agent configuration
├── config_loader.py     # Config utilities
├── Dockerfile           # Container build file
│
├── sub_agents/          # Specialized agents
│   ├── vector_search/   # Semantic search
│   ├── graph_query/     # Structured queries
│   ├── cypher_expert/   # Custom Cypher
│   └── answer_critic/   # Answer validation
│
└── plugins/             # ADK plugins
    ├── logging_plugin.py
    ├── metrics_plugin.py
    └── neo4j_lifecycle_plugin.py

# OpenShift/Podman manifests are in: openshift/vandelay-search/
# ├── pod.yaml           # Quick-start pod (Podman Desktop)
# ├── deployment.yaml    # Production deployment
# ├── configmap.yaml     # Configuration
# ├── secret.yaml        # Secrets template
# ├── service.yaml       # Service exposure
# └── route.yaml         # OpenShift route
```

## Example Queries

| Query | Sub-Agent Used |
|-------|----------------|
| "What checking accounts do you offer?" | graph_query |
| "Tell me about Basel III requirements" | graph_query |
| "How does fraud protection work?" | vector_search |
| "Find high-risk portfolios" | graph_query |
| "What are the fees for Premium Checking?" | graph_query |
| "Show me the graph schema" | cypher_expert |

## Configuration

All settings are in `config.yaml`:

- **llm**: LLM model and endpoint
- **neo4j**: Database connection
- **orchestrator**: Agent instructions and routing
- **sub_agents**: Sub-agent configurations
- **answer_critic**: Answer validation thresholds

## Container Deployment

For Podman Desktop (local) or OpenShift (production) deployment:

```bash
# From repository root
cd vandelay-ai

# Build the image
podman build -t vandelay-search:latest -f vandelay_search/Dockerfile vandelay_search/

# Quick start with Podman Desktop
podman kube play openshift/vandelay-search/pod.yaml

# Access at http://localhost:8000

# Stop when done
podman kube down openshift/vandelay-search/pod.yaml
```

See `openshift/vandelay-search/README.md` for detailed deployment instructions including OpenShift production deployment.

## Credits

- Built with [Google Agent Development Kit](https://google.github.io/adk-docs/)
- GraphRAG patterns from [Neo4j GraphRAG Pattern Catalog](https://graphrag.com/concepts/intro-to-graphrag/)
- Container patterns from [ADK Samples](https://github.com/google/adk-samples)
