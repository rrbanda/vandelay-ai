# Agent Cypher Queries for Migration Knowledge Graph

These Cypher queries are designed to be used in agent instructions with a Neo4j MCP server.

---

## Flow Mapping to User Prompts

| User Prompt | Cypher Query Section |
|-------------|---------------------|
| "Is my application in scope?" | Query #1 - Check Application Scope |
| "What steps must my application follow to migrate?" | Query #2 - Get Migration Steps |
| "Pull cluster/migration details for my application" | Query #3 - Full Migration Details |
| "Need migration support" | Query #4 - Support Info (static response) |

---

# PROMPT 1: "Is my application in scope?"

## Query: Check Application Scope by CSI (app_id)

**Flow:** User submits CSI → Returns list of namespaces by wave with source + destination cluster and dates

```cypher
MATCH (ns:Namespace)-[:MIGRATES_FROM]->(src:SourceCluster)
MATCH (ns)-[:MIGRATES_TO]->(dest:DestinationCluster)
MATCH (ns)-[:SCHEDULED_IN]->(phase:MigrationPhase)
WHERE ns.app_id = $app_id
RETURN ns.name as namespace,
       ns.app_name as application,
       ns.app_id as app_id,
       ns.env as environment,
       src.name as source_cluster,
       dest.name as destination_cluster,
       phase.name as migration_wave,
       phase.start_date as wave_start_date,
       phase.end_date as wave_end_date,
       phase.status as wave_status
ORDER BY phase.start_date, ns.env
```

**Example prompt:** "Is APP-12345 in scope for migration?"

**Expected response format:**
```
Your application APP-12345 is IN SCOPE for migration:

| Namespace | Environment | Source | Destination | Wave | Dates |
|-----------|------------|--------|-------------|------|-------|
| payments-api | DEV | NAMOSESWD10D | NAMOSESWD20D | DEV | Jan 5 - Feb 28, 2026 |
```

---

# PROMPT 2: "What steps must my application follow to migrate?"

## Query: Get Migration Steps Based on Attributes

**Flow:** User provides namespace → Returns attributes → Agent determines required steps based on:
- `network_type` = 'dmz' → Requires Ping/SSO configuration
- EgressIP changes → Requires firewall requests
- Storage class change → Requires PVC updates

```cypher
MATCH (ns:Namespace)
WHERE toLower(ns.name) = toLower($namespace)
OPTIONAL MATCH (ns)-[:MIGRATES_FROM]->(src:SourceCluster)
OPTIONAL MATCH (ns)-[:MIGRATES_TO]->(dest:DestinationCluster)
OPTIONAL MATCH (dest)-[:HAS_CONFIG]->(cfg:ClusterConfig)
OPTIONAL MATCH (ns)-[:HAS_SOURCE_EGRESS]->(src_ip:EgressIP)
OPTIONAL MATCH (ns)-[:HAS_DEST_EGRESS]->(dest_ip:EgressIP)
RETURN ns.name as namespace,
       ns.app_name as application,
       ns.network_type as network_type,
       ns.cluster_type as cluster_type,
       src.name as source_cluster,
       dest.name as destination_cluster,
       cfg.vip_name as vip_hostname,
       cfg.sm_reghost_hostname as sso_host,
       collect(DISTINCT src_ip.ip_address) as source_egress_ips,
       collect(DISTINCT dest_ip.ip_address) as dest_egress_ips,
       CASE WHEN ns.network_type = 'dmz' THEN true ELSE false END as requires_sso,
       CASE WHEN ns.network_type = 'dmz' THEN true ELSE false END as requires_ping,
       CASE WHEN size(collect(DISTINCT dest_ip.ip_address)) > 0 THEN true ELSE false END as requires_firewall,
       true as requires_storage_class_change,
       true as requires_cd_pipeline_update
```

**Agent logic after query:**
```
Based on attributes, provide customized migration guide:

IF network_type = 'dmz':
  - ✅ SSO Configuration Required (update SM_REGHOST_HOSTNAME to: {sso_host})
  - ✅ Ping Access Registration Required
  - ✅ Vanity URL may need update

IF dest_egress_ips is not empty:
  - ✅ Firewall Request Required (new EgressIP: {dest_egress_ips})
  - Lead time: 14 days

ALWAYS:
  - ✅ Update CD pipeline (ArgoCD/FluxCD/Spinnaker)
  - ✅ Change storage class from thin/thin-csi to sc-ontap-nas
  - ✅ Update container registry references if needed
```

---

# PROMPT 3: "Pull cluster/migration details for my application"

## Query: Full Migration Details Table

**Flow:** User inputs CSI → Returns complete table of migration details

```cypher
MATCH (ns:Namespace)
WHERE ns.app_id = $app_id
OPTIONAL MATCH (ns)-[:MIGRATES_FROM]->(src:SourceCluster)
OPTIONAL MATCH (ns)-[:MIGRATES_TO]->(dest:DestinationCluster)
OPTIONAL MATCH (dest)-[:HAS_CONFIG]->(cfg:ClusterConfig)
OPTIONAL MATCH (ns)-[:HAS_SOURCE_EGRESS]->(src_ip:EgressIP)
OPTIONAL MATCH (ns)-[:HAS_DEST_EGRESS]->(dest_ip:EgressIP)
OPTIONAL MATCH (ns)-[:SCHEDULED_IN]->(phase:MigrationPhase)
RETURN ns.name as namespace,
       ns.app_id as app_id,
       ns.app_name as application,
       ns.env as environment,
       ns.sector as sector,
       ns.org as organization,
       ns.app_manager as app_manager,
       ns.support_manager as support_manager,
       ns.network_type as network_type,
       src.name as source_cluster,
       dest.name as destination_cluster,
       cfg.cluster_subnet as cluster_subnet,
       cfg.vip_name as vip_hostname,
       cfg.vip_ip_address as vip_ip,
       cfg.infra_node_ips as infra_nodes,
       cfg.sm_reghost_hostname as sso_registration_host,
       collect(DISTINCT src_ip.ip_address) as source_egress_ips,
       collect(DISTINCT dest_ip.ip_address) as destination_egress_ips,
       phase.name as migration_phase,
       phase.start_date as phase_start,
       phase.end_date as phase_end,
       phase.status as phase_status
ORDER BY ns.env
```

**Expected response format:**
```
Migration Details for APP-12345:

| Field | Value |
|-------|-------|
| Namespace | payments-api |
| Application | Payment Processing Service |
| Environment | DEV |
| Source Cluster | NAMOSESWD10D |
| Destination Cluster | NAMOSESWD20D |
| Cluster VIP | N14536-vip.ecs.dyn.nsroot.net (10.100.1.10) |
| SSO Host | smpolicy01.nam.nsroot.net |
| Current EgressIP | 192.168.10.50 |
| New EgressIP | 10.100.50.10 |
| Migration Wave | DEV |
| Wave Dates | Jan 5 - Feb 28, 2026 |
| App Manager | john.smith@vandelay.com |
```

---

# PROMPT 4: "Need migration support"

## Static Response (No Query Needed)

**Flow:** Provide support options

```
Migration Support Options:

**Option 1: Report an Issue**
→ Open a ServiceNow ticket: [SNOW Template Link]
→ Category: Infrastructure > OpenShift > Migration

**Option 2: Migration-Related Question**
→ Email: CTS-Global-OpenShift-Migrations@vandelay.com
→ Include: App ID, Namespace, Environment, Question

**Option 3: Self-Service Resources**
→ Migration SharePoint: [SharePoint Link]
→ Confluence Documentation: [Confluence Link]
→ FAQ: [FAQ Link]
```

---

# Additional Queries

## 1. Check if Application is in Scope

**User asks:** "Is my application in scope?" / "Is APP-12345 being migrated?"

```cypher
// By app_id
MATCH (ns:Namespace)-[:MIGRATES_TO]->(dest:DestinationCluster)
MATCH (ns)-[:SCHEDULED_IN]->(phase:MigrationPhase)
WHERE ns.app_id = $app_id
RETURN ns.name as namespace,
       ns.app_name as application,
       ns.env as environment,
       dest.name as destination_cluster,
       phase.name as migration_wave,
       phase.start_date as wave_start,
       phase.end_date as wave_end,
       phase.status as status
ORDER BY phase.start_date
```

```cypher
// By namespace name
MATCH (ns:Namespace)-[:MIGRATES_TO]->(dest:DestinationCluster)
MATCH (ns)-[:SCHEDULED_IN]->(phase:MigrationPhase)
WHERE toLower(ns.name) CONTAINS toLower($namespace_name)
RETURN ns.name as namespace,
       ns.app_name as application,
       ns.env as environment,
       dest.name as destination_cluster,
       phase.name as migration_wave,
       phase.start_date as wave_start,
       phase.status as status
```

---

## 2. Get Migration Details for Application

**User asks:** "What are the migration details for payments-api?"

```cypher
MATCH (ns:Namespace)
WHERE toLower(ns.name) = toLower($namespace)
OPTIONAL MATCH (ns)-[:MIGRATES_FROM]->(src:SourceCluster)
OPTIONAL MATCH (ns)-[:MIGRATES_TO]->(dest:DestinationCluster)
OPTIONAL MATCH (dest)-[:HAS_CONFIG]->(cfg:ClusterConfig)
OPTIONAL MATCH (ns)-[:HAS_SOURCE_EGRESS]->(src_ip:EgressIP)
OPTIONAL MATCH (ns)-[:HAS_DEST_EGRESS]->(dest_ip:EgressIP)
OPTIONAL MATCH (ns)-[:SCHEDULED_IN]->(phase:MigrationPhase)
RETURN ns.name as namespace,
       ns.app_id as app_id,
       ns.app_name as application,
       ns.env as environment,
       ns.app_manager as app_manager,
       ns.sector as sector,
       ns.org as organization,
       ns.network_type as network_type,
       src.name as source_cluster,
       dest.name as destination_cluster,
       cfg.vip_name as cluster_vip,
       cfg.vip_ip_address as vip_ip,
       cfg.sm_reghost_hostname as sso_host,
       cfg.cluster_subnet as cluster_subnet,
       collect(DISTINCT src_ip.ip_address) as source_egress_ips,
       collect(DISTINCT dest_ip.ip_address) as destination_egress_ips,
       phase.name as migration_phase,
       phase.start_date as phase_start,
       phase.end_date as phase_end
```

---

## 3. Get Cluster Configuration

**User asks:** "What is the VIP for NAMOSESWD20D?" / "Show cluster config"

```cypher
MATCH (dest:DestinationCluster)-[:HAS_CONFIG]->(cfg:ClusterConfig)
WHERE toLower(dest.name) = toLower($cluster_name)
RETURN dest.name as cluster,
       dest.platform as platform,
       cfg.cluster_subnet as subnet,
       cfg.vip_name as vip_hostname,
       cfg.vip_ip_address as vip_ip,
       cfg.infra_node_ips as infra_nodes,
       cfg.sm_reghost_hostname as sso_registration_host
```

---

## 4. Get EgressIP Changes (Firewall Planning)

**User asks:** "What firewall rules do I need?" / "What IPs change for my app?"

```cypher
MATCH (ns:Namespace)
WHERE toLower(ns.name) = toLower($namespace)
OPTIONAL MATCH (ns)-[:HAS_SOURCE_EGRESS]->(src_ip:EgressIP)
OPTIONAL MATCH (ns)-[:HAS_DEST_EGRESS]->(dest_ip:EgressIP)
RETURN ns.name as namespace,
       ns.app_name as application,
       collect(DISTINCT src_ip.ip_address) as current_egress_ips,
       collect(DISTINCT dest_ip.ip_address) as new_egress_ips,
       CASE WHEN size(collect(DISTINCT dest_ip.ip_address)) > 0 
            THEN 'Firewall rules needed for new EgressIPs' 
            ELSE 'No EgressIP change detected' END as action_required
```

---

## 5. List Namespaces by Destination Cluster

**User asks:** "What apps are migrating to NAMOSESWD20D?"

```cypher
MATCH (ns:Namespace)-[:MIGRATES_TO]->(dest:DestinationCluster)
WHERE toLower(dest.name) = toLower($cluster_name)
RETURN ns.name as namespace,
       ns.app_name as application,
       ns.app_id as app_id,
       ns.env as environment,
       ns.app_manager as owner,
       ns.sector as sector
ORDER BY ns.name
```

---

## 6. Get Migration Timeline / Phases

**User asks:** "What is the migration timeline?" / "When is PROD wave?"

```cypher
MATCH (p:MigrationPhase)
RETURN p.name as phase,
       p.description as description,
       p.start_date as start_date,
       p.end_date as end_date,
       p.status as status
ORDER BY p.start_date
```

---

## 7. List Namespaces by Owner/Manager

**User asks:** "Show all apps owned by john.smith@vandelay.com"

```cypher
MATCH (ns:Namespace)
WHERE toLower(ns.app_manager) CONTAINS toLower($manager_email)
OPTIONAL MATCH (ns)-[:MIGRATES_TO]->(dest:DestinationCluster)
OPTIONAL MATCH (ns)-[:SCHEDULED_IN]->(phase:MigrationPhase)
RETURN ns.name as namespace,
       ns.app_name as application,
       ns.app_id as app_id,
       ns.env as environment,
       ns.app_manager as app_manager,
       dest.name as destination_cluster,
       phase.name as migration_wave
ORDER BY ns.name
```

---

## 8. Get Storage Class Mapping

**User asks:** "What storage class should I use?" / "How do I migrate storage?"

```cypher
MATCH (sc:StorageClass)
RETURN sc.name as storage_class,
       sc.platform as platform,
       sc.provisioner as provisioner,
       sc.is_default as is_default,
       sc.notes as notes
ORDER BY sc.platform DESC, sc.is_default DESC
```

---

## 9. Find Cluster Mapping (Source to Destination)

**User asks:** "Where does NAMOSESWD10D map to?"

```cypher
MATCH (src:SourceCluster)-[:MAPS_TO]->(dest:DestinationCluster)
WHERE toLower(src.name) = toLower($source_cluster)
OPTIONAL MATCH (dest)-[:HAS_CONFIG]->(cfg:ClusterConfig)
RETURN src.name as source_cluster,
       src.platform as source_platform,
       dest.name as destination_cluster,
       dest.platform as destination_platform,
       cfg.vip_name as destination_vip,
       cfg.sm_reghost_hostname as sso_host
```

---

## 10. Count Summary (Dashboard)

**User asks:** "Show migration summary" / "How many apps are in scope?"

```cypher
MATCH (ns:Namespace)
WITH count(ns) as total_namespaces
MATCH (ns:Namespace)-[:SCHEDULED_IN]->(p:MigrationPhase)
WITH total_namespaces, p.name as phase, count(ns) as count
RETURN total_namespaces, collect({phase: phase, count: count}) as by_phase
```

---

## Agent Instruction Template

```
You are a migration assistant. Use these Cypher queries to answer user questions:

1. For "is my app in scope" questions:
   - Ask for app_id or namespace name
   - Query: MATCH (ns:Namespace)-[:MIGRATES_TO]->... WHERE ns.app_id = '{app_id}'

2. For migration details:
   - Query the full namespace details including cluster config
   
3. For EgressIP/firewall questions:
   - Always warn that firewall changes need 14 days lead time
   
4. For timeline questions:
   - Query MigrationPhase nodes

Always include:
- Source and destination clusters
- Migration phase/wave
- Key action items (storage class change, egress IP change, SSO update)
```

---

## Quick Reference - Node Labels

| Label | Description |
|-------|-------------|
| `Namespace` | Application namespace being migrated |
| `SourceCluster` | VCS 1.0 cluster (VMware) |
| `DestinationCluster` | Vandelay Cloud cluster (BareMetal) |
| `ClusterConfig` | VIP, SSO, infra node configuration |
| `EgressIP` | Egress IP addresses (source/destination) |
| `MigrationPhase` | Timeline phases (DEV, UAT, PROD waves) |
| `StorageClass` | Storage class mappings |

## Quick Reference - Relationships

| Relationship | Pattern |
|--------------|---------|
| `MIGRATES_FROM` | `(Namespace)-[:MIGRATES_FROM]->(SourceCluster)` |
| `MIGRATES_TO` | `(Namespace)-[:MIGRATES_TO]->(DestinationCluster)` |
| `SCHEDULED_IN` | `(Namespace)-[:SCHEDULED_IN]->(MigrationPhase)` |
| `HAS_CONFIG` | `(DestinationCluster)-[:HAS_CONFIG]->(ClusterConfig)` |
| `HAS_SOURCE_EGRESS` | `(Namespace)-[:HAS_SOURCE_EGRESS]->(EgressIP)` |
| `HAS_DEST_EGRESS` | `(Namespace)-[:HAS_DEST_EGRESS]->(EgressIP)` |
| `MAPS_TO` | `(SourceCluster)-[:MAPS_TO]->(DestinationCluster)` |
