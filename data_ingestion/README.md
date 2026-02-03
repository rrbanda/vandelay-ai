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

---

## Testing the Migration Knowledge Graph

### Step 1: Run Automated Tests

```bash
cd data_ingestion
python test_ingestion.py --password YOUR_PASSWORD
```

**Expected output:**
```
============================================================
MIGRATION KNOWLEDGE GRAPH - VERIFICATION TESTS
============================================================

TEST 1: Node Counts
----------------------------------------
  ✓ Namespace: 10 (expected >= 10)
  ✓ SourceCluster: 2 (expected >= 2)
  ✓ DestinationCluster: 2 (expected >= 2)
  ✓ ClusterConfig: 2 (expected >= 2)
  ✓ MigrationPhase: 5 (expected >= 5)
  ✓ StorageClass: 4 (expected >= 4)

TEST 2: Relationship Counts
----------------------------------------
  ✓ MIGRATES_FROM: 10 (expected >= 10)
  ✓ MIGRATES_TO: 10 (expected >= 10)
  ✓ MAPS_TO: 2 (expected >= 2)
  ✓ HAS_CONFIG: 2 (expected >= 2)

ALL TESTS PASSED
✅ Ingestion verified successfully!
```

### Step 2: Test with Neo4j Browser

Open `http://localhost:7474` (requires port-forward for 7474 as well) and run these queries:

---

## Sample Prompts & Cypher Queries

These queries demonstrate the types of questions the knowledge graph can answer.

### Prompt 1: "Is my application in scope?"

Find namespaces for a given app_id with migration schedule:

```cypher
MATCH (ns:Namespace)-[:MIGRATES_TO]->(dest:DestinationCluster)
MATCH (ns)-[:SCHEDULED_IN]->(phase:MigrationPhase)
WHERE ns.app_id = 'APP-12345'
RETURN ns.name as namespace, 
       ns.app_name as application, 
       dest.name as destination_cluster, 
       phase.name as wave,
       phase.start_date as migration_start,
       phase.end_date as migration_end
```

**Expected:** `payments-api` → `NAMOSESWD20D`, DEV wave (2026-01-05 to 2026-02-28)

---

### Prompt 2: "What are the migration details for payments-api?"

Get full migration path with cluster config:

```cypher
MATCH (ns:Namespace {name: 'payments-api'})-[:MIGRATES_FROM]->(src:SourceCluster)
MATCH (ns)-[:MIGRATES_TO]->(dest:DestinationCluster)
OPTIONAL MATCH (dest)-[:HAS_CONFIG]->(cfg:ClusterConfig)
OPTIONAL MATCH (ns)-[:HAS_DEST_EGRESS]->(egress:EgressIP)
RETURN ns.name as namespace, 
       ns.app_name as application,
       ns.app_manager as owner,
       src.name as source_cluster, 
       dest.name as destination_cluster,
       cfg.vip_name as vip_hostname,
       cfg.vip_ip_address as vip_ip,
       cfg.sm_reghost_hostname as sso_host,
       collect(DISTINCT egress.ip_address) as new_egress_ips
```

**Expected:** 
- Source: `NAMOSESWD10D` → Destination: `NAMOSESWD20D`
- VIP: `N14536-vip.ecs.dyn.nsroot.net`
- SSO Host: `smpolicy01.nam.nsroot.net`

---

### Prompt 3: "What namespaces are migrating to cluster NAMOSESWD20D?"

List all namespaces for a destination cluster:

```cypher
MATCH (ns:Namespace)-[:MIGRATES_TO]->(dest:DestinationCluster {name: 'NAMOSESWD20D'})
RETURN ns.name as namespace, 
       ns.app_name as application, 
       ns.app_manager as owner, 
       ns.env as environment,
       ns.sector as sector
ORDER BY ns.name
```

**Expected:** 7 namespaces (payments-api, accounts-service, auth-gateway, notification-service, trading-platform, kyc-service, mobile-backend)

---

### Prompt 4: "What is the migration timeline?"

View all migration phases:

```cypher
MATCH (p:MigrationPhase)
RETURN p.name as phase, 
       p.description as description, 
       p.start_date as start_date, 
       p.end_date as end_date, 
       p.status as status
ORDER BY p.start_date
```

**Expected:**
| Phase | Description | Start | End | Status |
|-------|-------------|-------|-----|--------|
| DEV | Development environment migration | 2026-01-05 | 2026-02-28 | active |
| UAT | User acceptance testing migration | 2026-04-01 | 2026-05-31 | upcoming |
| PROD_W1 | Production wave 1 - critical apps | 2026-07-01 | 2026-08-31 | upcoming |
| PROD_W2 | Production wave 2 - standard apps | 2026-10-01 | 2026-11-30 | upcoming |
| PROD_W3 | Production wave 3 - remaining apps | 2027-01-05 | 2027-02-28 | upcoming |

---

### Prompt 5: "What EgressIPs change for auth-gateway?"

Compare old vs new egress IPs (important for firewall rules):

```cypher
MATCH (ns:Namespace {name: 'auth-gateway'})
OPTIONAL MATCH (ns)-[:HAS_SOURCE_EGRESS]->(src_ip:EgressIP)
OPTIONAL MATCH (ns)-[:HAS_DEST_EGRESS]->(dest_ip:EgressIP)
RETURN ns.name as namespace, 
       collect(DISTINCT src_ip.ip_address) as old_egress_ips,
       collect(DISTINCT dest_ip.ip_address) as new_egress_ips
```

**Expected:** Old `192.168.10.52` → New `10.100.50.12`

---

### Prompt 6: "What storage classes are available?"

View source and destination storage class options:

```cypher
MATCH (sc:StorageClass)
RETURN sc.name as storage_class, 
       sc.platform as platform,
       sc.provisioner as provisioner,
       sc.is_default as is_default,
       sc.notes as notes
ORDER BY sc.platform, sc.name
```

**Expected:**
| Storage Class | Platform | Default | Notes |
|---------------|----------|---------|-------|
| thin | source | No | Legacy vSphere - not available on BareMetal |
| thin-csi | source | Yes | vSphere CSI - not available on BareMetal |
| dell-csm-sc | destination | No | Dell CSM storage for BareMetal |
| sc-ontap-nas | destination | Yes | NetApp ONTAP NAS - default for BareMetal |

---

### Prompt 7: "Show cluster configuration for NAMOSESWD20D"

Get VIP, infra nodes, and SSO details:

```cypher
MATCH (dest:DestinationCluster {name: 'NAMOSESWD20D'})-[:HAS_CONFIG]->(cfg:ClusterConfig)
RETURN dest.name as cluster,
       dest.platform as platform,
       cfg.cluster_subnet as subnet,
       cfg.vip_name as vip_hostname,
       cfg.vip_ip_address as vip_ip,
       cfg.infra_node_ips as infra_nodes,
       cfg.sm_reghost_hostname as sso_registration_host
```

**Expected:**
- Subnet: `10.100.0.0/16`
- VIP: `N14536-vip.ecs.dyn.nsroot.net` (10.100.1.10)
- Infra Nodes: `10.100.2.1, 10.100.2.2, 10.100.2.3`
- SSO Host: `smpolicy01.nam.nsroot.net`

---

### Prompt 8: "List all namespaces owned by john.smith@vandelay.com"

Find namespaces by app manager:

```cypher
MATCH (ns:Namespace)
WHERE toLower(ns.app_manager) CONTAINS 'john.smith'
RETURN ns.name as namespace,
       ns.app_name as application,
       ns.env as environment,
       ns.sector as sector
ORDER BY ns.name
```

---

## Knowledge Graph Schema

```
┌─────────────┐     MIGRATES_FROM      ┌───────────────┐
│  Namespace  │───────────────────────▶│ SourceCluster │
│             │                        └───────┬───────┘
│  - name     │                                │
│  - app_id   │     MIGRATES_TO               │ MAPS_TO
│  - app_name │◀───────────────────┐          │
│  - env      │                    │          ▼
│  - sector   │              ┌─────┴─────────────────────┐
└──────┬──────┘              │   DestinationCluster      │
       │                     │                           │
       │ SCHEDULED_IN        │   - name                  │
       │                     │   - platform: BareMetal   │
       ▼                     └─────────────┬─────────────┘
┌──────────────┐                           │ HAS_CONFIG
│MigrationPhase│                           │
│              │                           ▼
│ - name       │                  ┌─────────────────┐
│ - start_date │                  │  ClusterConfig  │
│ - end_date   │                  │                 │
│ - status     │                  │  - vip_name     │
└──────────────┘                  │  - vip_ip       │
                                  │  - sso_host     │
┌──────────────┐                  │  - infra_nodes  │
│   EgressIP   │◀── HAS_DEST_     └─────────────────┘
│              │    EGRESS
│ - ip_address │
│ - ip_type    │◀── HAS_SOURCE_EGRESS ── Namespace
└──────────────┘
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
