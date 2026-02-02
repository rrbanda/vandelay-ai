# Data Ingestion Module

This module handles data ingestion into **Neo4j Knowledge Graph** and **LlamaStack Vector Store**.

**This is a PREREQUISITE for running the RAG agent** - data must be ingested before the agent can query it.

---

## Migration Knowledge Graph (Standalone)

Self-contained script to ingest VCS → Vandelay Cloud migration data.

### Quick Start (Port Forward)

```bash
# 1. Port forward Neo4j from OpenShift
oc port-forward svc/neo4j 7687:7687 &

# 2. Run from this folder
cd data_ingestion
pip install neo4j
python standalone_ingest.py --password YOUR_PASSWORD --clear
```

### Quick Start (OpenShift Job)

```bash
# Run inside OpenShift cluster
cd data_ingestion/openshift
./run-ingest.sh neo4j-service YOUR_PASSWORD
```

### Test Data Included

```
data/migration_csv/
├── namespaces.csv         # 10 sample namespaces
├── cluster_mappings.csv   # Source → Destination clusters
├── cluster_configs.csv    # VIP, infra nodes, SSO
├── migration_phases.csv   # DEV, UAT, PROD waves
└── storage_classes.csv    # Storage class mappings
```

### Expected Output

```
Node counts:
  Namespace: 10
  SourceCluster: 2
  DestinationCluster: 2
  ClusterConfig: 2
  EgressIP: 20
  MigrationPhase: 5
  StorageClass: 4

Relationship counts:
  MIGRATES_FROM: 10
  MIGRATES_TO: 10
  HAS_SOURCE_EGRESS: 10
  HAS_DEST_EGRESS: 10
  SCHEDULED_IN: 10
  MAPS_TO: 2
  HAS_CONFIG: 2
  HAS_STORAGE_CLASS: 8
```

### Verify in Neo4j Browser

```cypher
-- List all namespaces with migration path
MATCH (ns:Namespace)-[:MIGRATES_FROM]->(src:SourceCluster)
MATCH (ns)-[:MIGRATES_TO]->(dest:DestinationCluster)
RETURN ns.name, src.name, dest.name, ns.env
```

---

## FSI Data Ingestion (Original)

## Architecture

```
                       FSI Data Sources
                             │
            ┌────────────────┼────────────────┐
            │                │                │
            ▼                ▼                ▼
   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
   │   Cypher    │   │  Documents  │   │  Documents  │
   │   File      │   │   (.txt)    │   │   (.txt)    │
   └─────────────┘   └─────────────┘   └─────────────┘
            │                │                │
            ▼                │                ▼
   ┌─────────────┐           │        ┌─────────────┐
   │ ingest_     │           │        │ ingest_     │
   │ graph.py    │           │        │ vector.py   │
   └─────────────┘           │        └─────────────┘
            │                │                │
            ▼                │                ▼
   ┌─────────────┐           │        ┌─────────────┐
   │  Knowledge  │           │        │   Vector    │
   │   Graph     │◀──────────┘────────│   Store     │
   │  (Neo4j)    │                    │ (LlamaStack)│
   └─────────────┘                    └─────────────┘
            │                                │
            └────────────┬───────────────────┘
                         ▼
            ┌────────────────────────┐
            │   RAG Agent Queries    │
            │   (vandelay_search)    │
            └────────────────────────┘
```

## Quick Start

### Prerequisites

1. **Neo4j** - Running at `bolt://localhost:7687`
2. **LlamaStack** - For vector store

### Step 1: Configure Environment

```bash
# Neo4j
export NEO4J_URI="bolt://localhost:7687"
export NEO4J_USERNAME="neo4j"
export NEO4J_PASSWORD="your-password"

# LlamaStack
export LLAMASTACK_BASE_URL="https://your-llamastack-server"
export VECTOR_STORE_ID="your-vector-store-id"
```

### Step 2: Run Ingestion

```bash
# Ingest graph data (from Cypher file)
python -m data_ingestion.ingest_graph

# Ingest vector data (documents)
python -m data_ingestion.ingest_vector

# With options
python -m data_ingestion.ingest_graph --clear      # Clear existing data first
python -m data_ingestion.ingest_vector --clear     # Clear existing data first
```

### Step 3: Verify

1. Open Neo4j Browser: http://localhost:7474
2. Run: `MATCH (n) RETURN n LIMIT 100`
3. You should see Bank, Customer, Product, and other nodes

### Step 4: Run RAG Agent

```bash
cd vandelay_search
adk web --port 8888
```

## Ingestion Scripts

### Graph Ingestion (`ingest_graph.py`)

Loads structured data from a Cypher file into Neo4j.

```bash
# Use local data (default)
python -m data_ingestion.ingest_graph

# Use data from git URL
python -m data_ingestion.ingest_graph --git-url https://github.com/user/repo.git

# Clear existing data first
python -m data_ingestion.ingest_graph --clear

# Specify cypher file path
python -m data_ingestion.ingest_graph --cypher-file data/fsi_sample_data.cypher
```

**Data Source:** `data/fsi_sample_data.cypher`

### Vector Ingestion (`ingest_vector.py`)

Loads documents into LlamaStack Vector Store for semantic search.

```bash
# Use local data (default)
python -m data_ingestion.ingest_vector

# Use data from git URL
python -m data_ingestion.ingest_vector --git-url https://github.com/user/repo.git

# Clear existing data first
python -m data_ingestion.ingest_vector --clear

# Specify documents directory
python -m data_ingestion.ingest_vector --docs-dir data/fsi_documents
```

**Data Source:** `data/fsi_documents/*.txt`

## FSI Knowledge Graph Schema

The knowledge graph captures relationships between FSI entities:

```
Bank ──OFFERS──────▶ Product
 │
 ├──HAS_CUSTOMER───▶ Customer ──HOLDS────────▶ Account
 │                       │ ──MAKES───────────▶ Transaction
 │                       └──HAS_RISK_LEVEL───▶ (property)
 │
 └──OWNS───────────▶ Portfolio
```

### Node Types

| Node | Description | Key Properties |
|------|-------------|----------------|
| Bank | Financial institution | id, name |
| Product | Banking products | id, name, category, rates |
| Customer | Bank customers | id, name, risk_level, type |
| Account | Customer accounts | id, type, balance |
| Transaction | Financial transactions | id, amount, type, date |
| Portfolio | Financial portfolios | id, name, risk_score |

## Module Structure

```
data_ingestion/
├── __init__.py              # Module exports
├── README.md                # This file
├── config.yaml              # Configuration
├── config_loader.py         # Config loading utilities
├── ingest_graph.py          # Graph ingestion CLI
├── ingest_vector.py         # Vector ingestion CLI
├── git_data_source.py       # Git data source utility
│
├── models/                  # Pydantic models
│   ├── __init__.py
│   ├── base.py              # Base entities
│   ├── products.py          # Product models
│   ├── regulations.py       # Regulation models
│   └── risks.py             # Risk models
│
├── loaders/                 # Data store loaders
│   ├── __init__.py
│   ├── schema.py            # Neo4j schema
│   ├── graph_loader.py      # FSIGraphLoader
│   └── vector_loader.py     # FSIVectorLoader
│
├── data/                    # Sample data
│   ├── fsi_sample_data.cypher    # Graph data (Cypher)
│   └── fsi_documents/            # Vector documents
│       ├── account_types_guide.txt
│       ├── aml_compliance_policy.txt
│       ├── banking_faq.txt
│       └── ...
│
└── output/                  # Output files
    └── .gitkeep
```

## Configuration

All settings are in `config.yaml`:

- **neo4j**: Neo4j connection settings
- **vector_store**: LlamaStack settings
- **paths**: Data paths

Environment variables override config values.

## Demo Script

For demos, follow this script:

```
1. Show input data
   $ ls data_ingestion/data/
   → fsi_sample_data.cypher (graph data)
   → fsi_documents/ (vector documents)

2. Run graph ingestion
   $ python -m data_ingestion.ingest_graph
   → Loads Cypher data into Neo4j

3. Run vector ingestion
   $ python -m data_ingestion.ingest_vector
   → Loads documents into LlamaStack

4. Verify Knowledge Graph
   → Open http://localhost:7474
   → Run: MATCH (b:Bank)-[:HAS_CUSTOMER]->(c:Customer) RETURN b, c

5. Run RAG agent
   $ cd vandelay_search && adk web
   → Query: "What is Sarah Chen's risk level?"
   → Agent queries both Graph and Vector Store
```
