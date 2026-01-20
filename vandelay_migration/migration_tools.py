"""
Migration Tools - VCS to Vandelay Cloud (BareMetal OpenShift)
==============================================================

Tools for querying migration knowledge graph and documentation.

GraphRAG Patterns Implemented (per Neo4j GraphRAG Pattern Catalog):
- Cypher Templates: Pre-defined queries for migration data lookups
- Graph-Enhanced Vector Search: search_migration_docs_with_graph_context()
- Basic Retriever: Direct graph traversal for namespaces, clusters, etc.
- Pattern Matching: Cypher MATCH patterns throughout

Reference: https://graphrag.com/concepts/intro-to-graphrag/

Categories:
1. Graph Query Tools - Structured data (namespaces, clusters, EgressIPs)
2. Vector Search Tools - Procedural documentation (with GraphRAG enrichment)
3. Service Request Tools - Infrastructure change requests (via MCP server)

Graph Schema (Migration):
- Namespace -[:MIGRATES_FROM]-> SourceCluster
- Namespace -[:MIGRATES_TO]-> DestinationCluster
- Namespace -[:HAS_SOURCE_EGRESS]-> EgressIP
- Namespace -[:HAS_DEST_EGRESS]-> EgressIP
- Namespace -[:SCHEDULED_IN]-> MigrationPhase
- DestinationCluster -[:HAS_CONFIG]-> ClusterConfig
- SourceCluster -[:MAPS_TO]-> DestinationCluster
- SourceCluster -[:HAS_STORAGE_CLASS]-> StorageClass
- DestinationCluster -[:HAS_STORAGE_CLASS]-> StorageClass

Data Sources:
- Namespaces: Excel export from migration portal
- Clusters: Derived from namespace mappings
- ClusterConfig: Confluence table (VIPs, Infra Nodes, SSO)
- MigrationPhases: Static timeline from documentation
- StorageClasses: Platform reference data
"""

import os
from datetime import date, datetime, time
from typing import List, Dict, Any

import httpx
from neo4j import GraphDatabase

# Relative imports within the package
from .config_loader import (
    load_config,
    get_vector_store_config,
    get_graphrag_config,
    get_entity_patterns,
)

# Import service request tools from MCP server
from mcp_servers.service_request.server import ServiceRequestTools


# =============================================================================
# Neo4j Connection
# =============================================================================

_neo4j_driver = None


def _get_driver():
    """Get Neo4j driver from environment variables (singleton)."""
    global _neo4j_driver
    if _neo4j_driver is None:
        uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
        username = os.environ.get('NEO4J_USERNAME', 'neo4j')
        password = os.environ.get('NEO4J_PASSWORD', '')
        _neo4j_driver = GraphDatabase.driver(uri, auth=(username, password))
    return _neo4j_driver


def _serialize_neo4j_value(value: Any) -> Any:
    """Convert Neo4j types to JSON-serializable Python types."""
    if value is None:
        return None
    
    type_name = type(value).__name__
    if type_name in ('Date', 'DateTime', 'Time', 'Duration'):
        return str(value)
    
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    
    if isinstance(value, list):
        return [_serialize_neo4j_value(item) for item in value]
    
    if isinstance(value, dict):
        return {k: _serialize_neo4j_value(v) for k, v in value.items()}
    
    return value


def _serialize_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Serialize all Neo4j results to JSON-compatible format."""
    if not results:
        return results
    return [_serialize_neo4j_value(record) for record in results]


def _safe_execute_query(query: str, **params) -> tuple:
    """Execute a Neo4j query with consistent error handling."""
    try:
        driver = _get_driver()
        result = driver.execute_query(
            query,
            result_transformer_=lambda r: r.data(),
            **params
        )
        return _serialize_results(result), None
    except Exception as e:
        error_type = type(e).__name__
        return None, {
            "error": str(e),
            "error_type": error_type,
            "message": f"Database query failed: {error_type}"
        }


# =============================================================================
# Graph Query Tools - Migration Data
# =============================================================================

def get_migration_path(namespace: str) -> Dict[str, Any]:
    """
    Get source and destination cluster for a namespace migration.
    
    Use this to find where a namespace is migrating from and to.
    
    Args:
        namespace: The namespace name (e.g., 'payments-api')
        
    Returns:
        Migration path with source cluster, destination cluster, and environment
    """
    result, error = _safe_execute_query(
        '''
        MATCH (ns:Namespace)-[:MIGRATES_FROM]->(src:SourceCluster)
        MATCH (ns)-[:MIGRATES_TO]->(dest:DestinationCluster)
        WHERE toLower(ns.name) = toLower($namespace)
        RETURN ns.name as namespace, ns.app_name as application,
               ns.app_id as app_id,
               src.name as source_cluster, src.cluster_type as source_type,
               dest.name as destination_cluster, dest.cluster_type as destination_type,
               ns.env as environment
        ''',
        namespace=namespace
    )
    
    if error:
        return error
    if result:
        return result[0]
    return {"message": f"Namespace '{namespace}' not found in migration data"}


def get_namespace_details(namespace: str) -> Dict[str, Any]:
    """
    Get full details about a namespace including management hierarchy.
    
    Args:
        namespace: The namespace name
        
    Returns:
        Comprehensive namespace information including owners and org structure
    """
    result, error = _safe_execute_query(
        '''
        MATCH (ns:Namespace)
        WHERE toLower(ns.name) = toLower($namespace)
        OPTIONAL MATCH (ns)-[:MIGRATES_FROM]->(src:SourceCluster)
        OPTIONAL MATCH (ns)-[:MIGRATES_TO]->(dest:DestinationCluster)
        OPTIONAL MATCH (ns)-[:SCHEDULED_IN]->(phase:MigrationPhase)
        RETURN ns.name as namespace,
               ns.app_id as app_id,
               ns.app_name as app_name,
               ns.env as environment,
               ns.sector as sector,
               ns.region as region,
               ns.data_center as data_center,
               ns.network_type as network_type,
               ns.app_manager as app_manager,
               ns.support_manager as support_manager,
               ns.org as org,
               ns.l3 as l3,
               ns.l3_head as l3_head,
               ns.l4 as l4,
               ns.l4_head as l4_head,
               ns.l5 as l5,
               ns.l5_head as l5_head,
               ns.l6_business as l6_business,
               ns.l6_tech as l6_tech,
               src.name as source_cluster,
               dest.name as destination_cluster,
               phase.name as migration_phase
        ''',
        namespace=namespace
    )
    
    if error:
        return error
    if result:
        return result[0]
    return {"message": f"Namespace '{namespace}' not found"}


def get_cluster_config(cluster: str) -> Dict[str, Any]:
    """
    Get VIP, infra nodes, and SSO configuration for a destination cluster.
    
    Use this to get the infrastructure details needed for migration.
    
    Args:
        cluster: The destination cluster name (e.g., 'NAMOSESWD20D')
        
    Returns:
        Cluster configuration with VIP, infra nodes, SSO host, proxy port
    """
    result, error = _safe_execute_query(
        '''
        MATCH (c:DestinationCluster)-[:HAS_CONFIG]->(cfg:ClusterConfig)
        WHERE toLower(c.name) = toLower($cluster)
        RETURN c.name as cluster, 
               c.cluster_type as type, 
               c.data_center as data_center,
               c.region as region,
               cfg.cluster_subnet as cluster_subnet,
               cfg.vip_name as vip_hostname, 
               cfg.vip_ip_address as vip_ip,
               cfg.infra_node_ips as infra_nodes,
               cfg.sm_reghost_hostname as sm_reghost_hostname,
               cfg.proxy_port as proxy_port
        ''',
        cluster=cluster
    )
    
    if error:
        return error
    if result:
        data = result[0]
        # Add helpful notes
        data["notes"] = {
            "proxy_port": "All BareMetal clusters use port 17777 (changed from 9999/7777)",
            "sm_reghost_hostname": "Update this in your application's environment variables for SiteMinder"
        }
        return data
    return {"message": f"Cluster '{cluster}' not found or has no configuration"}


def get_egress_ips(namespace: str) -> Dict[str, Any]:
    """
    Get source and destination EgressIP addresses for a namespace.
    
    IMPORTANT: EgressIP changes during migration. New firewall rules are needed
    for internal system connections (SFTP, databases, MQ, etc.)
    
    Args:
        namespace: The namespace name
        
    Returns:
        Source EgressIPs (VCS) and Destination EgressIPs (Vandelay Cloud)
    """
    result, error = _safe_execute_query(
        '''
        MATCH (ns:Namespace)
        WHERE toLower(ns.name) = toLower($namespace)
        OPTIONAL MATCH (ns)-[:HAS_SOURCE_EGRESS]->(src_ip:EgressIP)
        OPTIONAL MATCH (ns)-[:HAS_DEST_EGRESS]->(dest_ip:EgressIP)
        RETURN ns.name as namespace,
               collect(DISTINCT src_ip.ip_address) as source_egress_ips,
               collect(DISTINCT dest_ip.ip_address) as destination_egress_ips
        ''',
        namespace=namespace
    )
    
    if error:
        return error
    if result:
        data = result[0]
        has_new_ip = len(data.get("destination_egress_ips", [])) > 0
        data["action_required"] = has_new_ip
        data["important_notes"] = [
            "Your EgressIP WILL CHANGE after migration",
            "Submit firewall requests for internal systems (SFTP, databases, MQ, mainframes)",
            "Lead time: 14 days minimum for firewall changes",
            "Internet-bound traffic is handled automatically by Platform Ops"
        ]
        return data
    return {"message": f"Namespace '{namespace}' not found"}


def get_storage_class_mapping() -> Dict[str, Any]:
    """
    Get source to destination storage class mapping.
    
    VMware storage classes (thin, thin-csi) are NOT available on BareMetal.
    
    Returns:
        Source and destination storage classes with recommendations
    """
    result, error = _safe_execute_query(
        '''
        MATCH (src_sc:StorageClass {platform: 'source'})
        WITH collect(DISTINCT {name: src_sc.name, provisioner: src_sc.provisioner, 
                               notes: src_sc.notes}) as source_classes
        MATCH (dest_sc:StorageClass {platform: 'destination'})
        RETURN source_classes,
               collect(DISTINCT {name: dest_sc.name, provisioner: dest_sc.provisioner,
                                is_default: dest_sc.is_default, notes: dest_sc.notes}) as destination_classes
        '''
    )
    
    if error:
        return error
    if result:
        data = result[0]
        return {
            "source_storage_classes": data.get("source_classes", []),
            "destination_storage_classes": data.get("destination_classes", []),
            "migration_action": {
                "thin": "Change to sc-ontap-nas (recommended) or dell-csm-sc",
                "thin-csi": "Change to sc-ontap-nas (recommended) or dell-csm-sc"
            },
            "recommendation": "Update PVC definitions from thin/thin-csi to sc-ontap-nas (default) or dell-csm-sc"
        }
    return {"message": "No storage class mappings found"}


def list_migration_namespaces(
    env: str = None, 
    sector: str = None, 
    destination_cluster: str = None
) -> List[Dict[str, Any]]:
    """
    List namespaces in migration scope with optional filters.
    
    Args:
        env: Optional filter by environment (DEV, UAT, PROD)
        sector: Optional filter by business sector
        destination_cluster: Optional filter by destination cluster
        
    Returns:
        List of namespaces with migration details
    """
    # Build query with optional filters
    where_clauses = []
    params = {}
    
    if env:
        where_clauses.append("toLower(ns.env) = toLower($env)")
        params['env'] = env
    
    if sector:
        where_clauses.append("toLower(ns.sector) = toLower($sector)")
        params['sector'] = sector
    
    if destination_cluster:
        where_clauses.append("toLower(dest.name) = toLower($dest_cluster)")
        params['dest_cluster'] = destination_cluster
    
    where_clause = " AND ".join(where_clauses) if where_clauses else "true"
    
    query = f'''
        MATCH (ns:Namespace)
        OPTIONAL MATCH (ns)-[:MIGRATES_TO]->(dest:DestinationCluster)
        WHERE {where_clause}
        RETURN ns.name as namespace, 
               ns.app_name as application,
               ns.app_id as app_id,
               ns.env as environment, 
               ns.sector as sector,
               ns.app_manager as app_manager,
               dest.name as destination_cluster
        ORDER BY ns.name
    '''
    
    result, error = _safe_execute_query(query, **params)
    
    if error:
        return [error]
    return result if result else [{"message": "No namespaces found matching criteria"}]


def get_migration_phase_info(phase: str = None) -> Dict[str, Any]:
    """
    Get migration phase timeline information.
    
    Args:
        phase: Optional specific phase (DEV, UAT, PROD_W1, PROD_W2, PROD_W3)
        
    Returns:
        Phase details including dates and status
    """
    if phase:
        result, error = _safe_execute_query(
            '''
            MATCH (p:MigrationPhase)
            WHERE toLower(p.name) = toLower($phase)
            RETURN p.name as phase, p.description as description,
                   p.start_date as start_date, p.end_date as end_date,
                   p.status as status
            ''',
            phase=phase
        )
    else:
        result, error = _safe_execute_query(
            '''
            MATCH (p:MigrationPhase)
            RETURN p.name as phase, p.description as description,
                   p.start_date as start_date, p.end_date as end_date,
                   p.status as status
            ORDER BY p.start_date
            '''
        )
    
    if error:
        return error
    if result:
        if phase:
            return result[0]
        return {"phases": result}
    return {"message": f"Phase '{phase}' not found" if phase else "No phases found"}


def list_namespaces_by_owner(app_manager: str = None, org: str = None) -> List[Dict[str, Any]]:
    """
    List namespaces by owner or organization.
    
    Args:
        app_manager: Filter by application manager email
        org: Filter by organization (e.g., ICG, GCB)
        
    Returns:
        List of namespaces with ownership details
    """
    where_clauses = []
    params = {}
    
    if app_manager:
        where_clauses.append("toLower(ns.app_manager) CONTAINS toLower($app_manager)")
        params['app_manager'] = app_manager
    
    if org:
        where_clauses.append("toLower(ns.org) = toLower($org)")
        params['org'] = org
    
    if not where_clauses:
        return [{"message": "Please provide app_manager or org filter"}]
    
    where_clause = " AND ".join(where_clauses)
    
    query = f'''
        MATCH (ns:Namespace)
        WHERE {where_clause}
        RETURN ns.name as namespace,
               ns.app_name as application,
               ns.app_manager as app_manager,
               ns.support_manager as support_manager,
               ns.org as org,
               ns.sector as sector,
               ns.migration_status as status
        ORDER BY ns.name
    '''
    
    result, error = _safe_execute_query(query, **params)
    
    if error:
        return [error]
    return result if result else [{"message": "No namespaces found for specified owner/org"}]


# =============================================================================
# Vector Search Tools - Migration Documentation
# =============================================================================

def search_migration_docs(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Search migration documentation using hybrid search (vector + keyword).
    
    Use this for "how to" questions about migration procedures.
    
    Supports three search modes (configured in config.yaml):
    - 'vector': Pure semantic similarity search
    - 'keyword': Traditional keyword-based search for exact matches
    - 'hybrid': Combines both for optimal results
    
    Args:
        query: The search query (e.g., "how to update CD pipeline")
        top_k: Number of results to return
        
    Returns:
        Relevant document chunks with content
    """
    vs_config = get_vector_store_config()
    
    base_url = vs_config.get('base_url', '')
    vector_store_id = vs_config.get('vector_store_id', 'migration_docs_store')
    verify_ssl = vs_config.get('verify_ssl', False)
    search_mode = vs_config.get('search_mode', 'vector')
    ranker_type = vs_config.get('ranker_type', 'weighted')
    ranking_alpha = vs_config.get('ranking_alpha', 0.7)
    
    if not base_url:
        return {"error": "Vector store not configured"}
    
    search_url = f"{base_url.rstrip('/')}/v1/vector-io/query"
    
    # Build payload with hybrid search parameters
    payload = {
        "vector_db_id": vector_store_id,
        "query": query,
        "params": {
            "max_chunks": top_k
        }
    }
    
    # Add hybrid search parameters if not using basic vector search
    if search_mode in ("hybrid", "keyword"):
        payload["search_mode"] = search_mode
        
        # Add ranking options for hybrid search
        if search_mode == "hybrid" and ranker_type:
            payload["ranking_options"] = {
                "ranker": {
                    "type": ranker_type,
                }
            }
            if ranker_type == "weighted":
                payload["ranking_options"]["ranker"]["alpha"] = ranking_alpha
    
    print(f"---MIGRATION DOCS SEARCH ({search_mode}): '{query}' (top_k={top_k})---")
    
    try:
        with httpx.Client(timeout=30.0, verify=verify_ssl) as client:
            response = client.post(search_url, json=payload)
            response.raise_for_status()
            result = response.json()
            
            chunks = result.get('chunks', [])
            
            formatted_results = []
            for chunk in chunks:
                formatted_results.append({
                    "content": chunk.get('content', ''),
                    "score": chunk.get('score', 0),
                    "metadata": chunk.get('metadata', {}),
                })
            
            if search_mode != "vector":
                print(f"  (search_mode={search_mode}, alpha={ranking_alpha})")
            print(f"  Found {len(formatted_results)} results")
            
            return {
                "found": len(formatted_results) > 0,
                "count": len(formatted_results),
                "results": formatted_results,
                "search_mode": search_mode
            }
            
    except httpx.HTTPStatusError as e:
        # If hybrid search fails with 400, fall back to basic vector search
        if search_mode != "vector" and e.response.status_code == 400:
            print(f"Hybrid search returned 400, falling back to vector search")
            # Retry with basic vector search
            payload_basic = {
                "vector_db_id": vector_store_id,
                "query": query,
                "params": {"max_chunks": top_k}
            }
            try:
                with httpx.Client(timeout=30.0, verify=verify_ssl) as client:
                    response = client.post(search_url, json=payload_basic)
                    response.raise_for_status()
                    result = response.json()
                    chunks = result.get('chunks', [])
                    formatted_results = []
                    for chunk in chunks:
                        formatted_results.append({
                            "content": chunk.get('content', ''),
                            "score": chunk.get('score', 0),
                            "metadata": chunk.get('metadata', {}),
                        })
                    return {
                        "found": len(formatted_results) > 0,
                        "count": len(formatted_results),
                        "results": formatted_results,
                        "search_mode": "vector"  # Fallback mode
                    }
            except Exception as fallback_error:
                return {"error": str(fallback_error)}
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# GraphRAG Helper Functions - Hybrid Vector-Graph Retrieval
# =============================================================================

def _extract_entity_mentions(
    search_results: Dict[str, Any],
    entity_patterns: Dict[str, List[str]]
) -> Dict[str, List[str]]:
    """
    Extract entity mentions from vector search results using configured patterns.
    
    Args:
        search_results: Results from search_migration_docs
        entity_patterns: Dict mapping category -> list of patterns from config
        
    Returns:
        Dict mapping category -> list of found entities
    """
    found_entities: Dict[str, List[str]] = {}
    
    results = search_results.get('results', [])
    if not results:
        return found_entities
    
    # Combine all content from results
    combined_text = ""
    for result in results:
        content = result.get('content', '')
        combined_text += f" {content} "
    
    combined_lower = combined_text.lower()
    
    # Search for each pattern category
    for category, patterns in entity_patterns.items():
        matches = []
        for pattern in patterns:
            if pattern.lower() in combined_lower:
                if pattern not in matches:
                    matches.append(pattern)
        if matches:
            found_entities[category] = matches
    
    return found_entities


def _fetch_migration_graph_context(
    entity_mentions: Dict[str, List[str]],
    max_lookups: int = 10,
    max_connections: int = 5
) -> List[Dict[str, Any]]:
    """
    Fetch graph context for mentioned entities from migration knowledge graph.
    
    Uses different queries based on entity type:
    - namespaces: Fetch migration path, cluster, egress IPs
    - cd_tools: Fetch namespaces using that CD tool
    - storage_classes: Fetch storage class details and mappings
    - phases: Fetch phase timeline info
    - infrastructure/sso_terms: Fetch related cluster configs
    
    Args:
        entity_mentions: Dict from _extract_entity_mentions
        max_lookups: Maximum total entity lookups
        max_connections: Maximum connections per entity
        
    Returns:
        List of graph context records
    """
    graph_context = []
    lookup_count = 0
    
    driver = _get_driver()
    
    # Process namespace mentions - most common case
    namespaces = entity_mentions.get('namespaces', [])
    for ns_name in namespaces:
        if lookup_count >= max_lookups:
            break
        
        try:
            result, error = _safe_execute_query(
                '''
                MATCH (ns:Namespace)
                WHERE toLower(ns.name) = toLower($name)
                OPTIONAL MATCH (ns)-[:MIGRATES_FROM]->(src:SourceCluster)
                OPTIONAL MATCH (ns)-[:MIGRATES_TO]->(dest:DestinationCluster)
                OPTIONAL MATCH (ns)-[:HAS_DEST_EGRESS]->(egress:EgressIP)
                OPTIONAL MATCH (ns)-[:SCHEDULED_IN]->(phase:MigrationPhase)
                RETURN ns.name as namespace,
                       ns.app_name as application,
                       ns.env as environment,
                       src.name as source_cluster,
                       dest.name as destination_cluster,
                       collect(DISTINCT egress.ip_address)[0..$max_conn] as dest_egress_ips,
                       phase.name as migration_phase
                LIMIT 1
                ''',
                name=ns_name,
                max_conn=max_connections
            )
            
            if not error and result:
                graph_context.append({
                    "entity_type": "namespace",
                    "entity": ns_name,
                    "data": result[0]
                })
                lookup_count += 1
                
        except Exception:
            pass
    
    # Process storage class mentions
    storage_classes = entity_mentions.get('storage_classes', [])
    for sc_name in storage_classes:
        if lookup_count >= max_lookups:
            break
        
        try:
            result, error = _safe_execute_query(
                '''
                MATCH (sc:StorageClass)
                WHERE toLower(sc.name) CONTAINS toLower($name)
                RETURN sc.name as storage_class,
                       sc.platform as platform,
                       sc.provisioner as provisioner,
                       sc.is_default as is_default,
                       sc.notes as notes
                LIMIT $max_conn
                ''',
                name=sc_name,
                max_conn=max_connections
            )
            
            if not error and result:
                graph_context.append({
                    "entity_type": "storage_class",
                    "entity": sc_name,
                    "data": result
                })
                lookup_count += 1
                
        except Exception:
            pass
    
    # Process phase mentions
    phases = entity_mentions.get('phases', [])
    for phase_name in phases:
        if lookup_count >= max_lookups:
            break
        
        try:
            result, error = _safe_execute_query(
                '''
                MATCH (p:MigrationPhase)
                WHERE toLower(p.name) CONTAINS toLower($name)
                   OR toLower(p.description) CONTAINS toLower($name)
                RETURN p.name as phase,
                       p.description as description,
                       p.start_date as start_date,
                       p.end_date as end_date,
                       p.status as status
                LIMIT 1
                ''',
                name=phase_name
            )
            
            if not error and result:
                graph_context.append({
                    "entity_type": "migration_phase",
                    "entity": phase_name,
                    "data": result[0]
                })
                lookup_count += 1
                
        except Exception:
            pass
    
    # Process infrastructure/SSO terms - look for cluster configs
    infra_terms = entity_mentions.get('infrastructure', []) + entity_mentions.get('sso_terms', [])
    if infra_terms and lookup_count < max_lookups:
        try:
            result, error = _safe_execute_query(
                '''
                MATCH (dest:DestinationCluster)-[:HAS_CONFIG]->(cfg:ClusterConfig)
                RETURN dest.name as cluster,
                       cfg.vip_name as vip_hostname,
                       cfg.vip_ip_address as vip_ip,
                       cfg.sm_reghost_hostname as sso_host,
                       cfg.proxy_port as proxy_port
                LIMIT $max_conn
                ''',
                max_conn=max_connections
            )
            
            if not error and result:
                graph_context.append({
                    "entity_type": "cluster_config",
                    "entity": "infrastructure",
                    "data": result
                })
                lookup_count += 1
                
        except Exception:
            pass
    
    return graph_context


def search_migration_docs_with_graph_context(
    query: str,
    top_k: int = 5,
    include_graph_context: bool = True
) -> Dict[str, Any]:
    """
    Search migration docs with GraphRAG: vector search + graph context enrichment.
    
    This is the preferred tool for migration documentation queries because it:
    1. Performs semantic search on migration documentation
    2. Extracts entity mentions (namespaces, CD tools, storage classes, etc.)
    3. Fetches related context from the migration knowledge graph
    4. Returns combined results for comprehensive answers
    
    Use this for questions like:
    - "How do I migrate payments-api to the new cluster?"
    - "What are the steps for updating ArgoCD pipelines?"
    - "How do I handle storage class changes?"
    
    Args:
        query: The search query
        top_k: Number of document results to return
        include_graph_context: Whether to enrich with graph context (default True)
        
    Returns:
        Dict with:
        - documents: Vector search results
        - entities_mentioned: Entities found in the documents
        - graph_context: Related data from the migration knowledge graph
        - graphrag_enabled: Whether graph enrichment was performed
    """
    # Step 1: Perform vector search
    doc_results = search_migration_docs(query, top_k=top_k)
    
    result = {
        "documents": doc_results,
        "entities_mentioned": {},
        "graph_context": [],
        "graphrag_enabled": False
    }
    
    # Check if we got valid results and should do graph enrichment
    if not include_graph_context:
        return result
    
    if not doc_results.get('found', False):
        return result
    
    # Step 2: Get GraphRAG configuration
    graphrag_config = get_graphrag_config()
    if not graphrag_config.get('enable_graph_context', True):
        return result
    
    entity_patterns = get_entity_patterns()
    if not entity_patterns:
        return result
    
    # Step 3: Extract entity mentions from documents
    entities = _extract_entity_mentions(doc_results, entity_patterns)
    result["entities_mentioned"] = entities
    
    if not entities:
        return result
    
    # Step 4: Fetch graph context for mentioned entities
    max_lookups = graphrag_config.get('max_entity_lookups', 10)
    max_connections = graphrag_config.get('max_connections_per_entity', 5)
    
    graph_context = _fetch_migration_graph_context(
        entities,
        max_lookups=max_lookups,
        max_connections=max_connections
    )
    
    result["graph_context"] = graph_context
    result["graphrag_enabled"] = len(graph_context) > 0
    
    return result


# =============================================================================
# Service Request Tools - MCP Server Integration
# =============================================================================

_service_request_tools = None


def _get_service_request_tools() -> ServiceRequestTools:
    """Get or create service request tools instance."""
    global _service_request_tools
    if _service_request_tools is None:
        _service_request_tools = ServiceRequestTools()
    return _service_request_tools


def submit_firewall_request(
    namespace: str,
    source_egress_ips: List[str],
    destination_hosts: List[str],
    destination_ports: List[str],
    protocol: str = "TCP",
    justification: str = ""
) -> Dict[str, Any]:
    """
    Submit a firewall rule request for new EgressIP whitelisting.
    
    Lead time: 14 days
    
    Args:
        namespace: Namespace requiring the rule
        source_egress_ips: New Vandelay Cloud EgressIP addresses
        destination_hosts: Target hosts that need access
        destination_ports: Target ports
        protocol: TCP or UDP
        justification: Business justification
    """
    return _get_service_request_tools().submit_firewall_request(
        namespace=namespace,
        source_egress_ips=source_egress_ips,
        destination_hosts=destination_hosts,
        destination_ports=destination_ports,
        protocol=protocol,
        justification=justification
    )


def submit_certificate_request(
    namespace: str,
    common_name: str,
    san_list: List[str],
    certificate_type: str = "server",
    justification: str = ""
) -> Dict[str, Any]:
    """
    Submit a certificate request for migration.
    
    Lead time: 7 days
    
    Only needed if cluster-based routes are in certificate SAN list.
    Not needed if using only Vanity URLs.
    
    Args:
        namespace: Namespace requiring the certificate
        common_name: Primary hostname
        san_list: Subject Alternative Names
        certificate_type: Type of certificate
        justification: Business justification
    """
    return _get_service_request_tools().submit_certificate_request(
        namespace=namespace,
        common_name=common_name,
        san_list=san_list,
        certificate_type=certificate_type,
        justification=justification
    )


def submit_dns_request(
    namespace: str,
    vanity_url: str,
    target_vip: str,
    target_vip_ip: str,
    request_type: str = "create",
    justification: str = ""
) -> Dict[str, Any]:
    """
    Submit a DNS/Vanity URL request.
    
    Lead time: 3 days
    
    Args:
        namespace: Associated namespace
        vanity_url: The vanity URL
        target_vip: Destination cluster VIP hostname
        target_vip_ip: Destination cluster VIP IP
        request_type: create, modify, or delete
        justification: Business justification
    """
    return _get_service_request_tools().submit_dns_request(
        namespace=namespace,
        vanity_url=vanity_url,
        target_vip=target_vip,
        target_vip_ip=target_vip_ip,
        request_type=request_type,
        justification=justification
    )


def submit_sso_request(
    namespace: str,
    application_id: str,
    sso_provider: str,
    base_url: str,
    new_sso_host: str,
    request_type: str = "registration",
    justification: str = ""
) -> Dict[str, Any]:
    """
    Submit an SSO configuration request.
    
    Lead time: 7 days
    
    Args:
        namespace: Namespace for the application
        application_id: Application identifier
        sso_provider: ping_access or siteminder
        base_url: Application base URL
        new_sso_host: New SSO registration hostname (SM_REGHOST_HOSTNAME)
        request_type: registration, modification, or removal
        justification: Business justification
    """
    return _get_service_request_tools().submit_sso_request(
        namespace=namespace,
        application_id=application_id,
        sso_provider=sso_provider,
        base_url=base_url,
        new_sso_host=new_sso_host,
        request_type=request_type,
        justification=justification
    )


def submit_operator_request(
    namespace: str,
    operator_name: str,
    operator_config: Dict[str, Any],
    destination_cluster: str,
    justification: str = ""
) -> Dict[str, Any]:
    """
    Submit an operator installation request to Platform Ops.
    
    Lead time: 5 days
    
    Args:
        namespace: Target namespace
        operator_name: redis, couchbase, service_mesh, or other
        operator_config: Resource requirements (cpu, memory, storage)
        destination_cluster: Vandelay Cloud cluster name
        justification: Business justification
    """
    return _get_service_request_tools().submit_operator_request(
        namespace=namespace,
        operator_name=operator_name,
        operator_config=operator_config,
        destination_cluster=destination_cluster,
        justification=justification
    )


def submit_cleanup_request(
    namespace: str,
    source_cluster: str,
    environment: str,
    confirmation: str,
    justification: str = ""
) -> Dict[str, Any]:
    """
    Submit cleanup request to delete project from source VCS cluster.
    
    WARNING: This is irreversible! Deleted projects cannot be restored.
    
    Lead time: 3 days (DEV via incident, UAT/PROD via change)
    
    Args:
        namespace: Namespace to delete
        source_cluster: VCS cluster to delete from
        environment: DEV, UAT, or PROD
        confirmation: Must be 'I_CONFIRM_DELETION'
        justification: Business justification
    """
    return _get_service_request_tools().submit_cleanup_request(
        namespace=namespace,
        source_cluster=source_cluster,
        environment=environment,
        confirmation=confirmation,
        justification=justification
    )


def check_request_status(ticket_id: str) -> Dict[str, Any]:
    """
    Check the status of a service request.
    
    Args:
        ticket_id: The ticket ID (e.g., FW-1001, CERT-1002)
        
    Returns:
        Current status and request details
    """
    return _get_service_request_tools().check_request_status(ticket_id)


def list_open_requests(namespace: str = None, request_type: str = None) -> Dict[str, Any]:
    """
    List all open service requests.
    
    Args:
        namespace: Optional filter by namespace
        request_type: Optional filter (firewall, certificate, dns, sso)
        
    Returns:
        List of open requests
    """
    return _get_service_request_tools().list_open_requests(
        namespace=namespace,
        request_type=request_type
    )


# =============================================================================
# Export Tools List
# =============================================================================

MIGRATION_TOOLS = [
    # Graph Query Tools
    get_migration_path,
    get_namespace_details,
    get_cluster_config,
    get_egress_ips,
    get_storage_class_mapping,
    list_migration_namespaces,
    get_migration_phase_info,
    list_namespaces_by_owner,
    
    # Vector Search Tools (GraphRAG hybrid preferred)
    search_migration_docs_with_graph_context,  # Preferred: hybrid vector + graph
    search_migration_docs,                      # Fallback: vector only
    
    # Service Request Tools (MCP)
    submit_firewall_request,
    submit_certificate_request,
    submit_dns_request,
    submit_sso_request,
    submit_operator_request,
    submit_cleanup_request,
    check_request_status,
    list_open_requests,
]
