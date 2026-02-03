"""
Neo4j Constraints and Indexes for Migration Knowledge Graph.

This module defines the graph schema for VCS to Vandelay Cloud (BareMetal OpenShift)
migration data. It provides constraints and indexes for:

- Namespace and cluster mappings
- Cluster configurations (VIPs, infra nodes, SSO)
- EgressIP mappings (source/destination)
- Migration phases and timelines
- Storage class mappings

Schema Overview:
----------------

NODES:
  - Namespace: Application namespace being migrated
  - SourceCluster: VCS 1.0 cluster (VMware-based source)
  - DestinationCluster: Vandelay Cloud cluster (BareMetal target)
  - ClusterConfig: VIP, infra nodes, SSO configuration for destination
  - EgressIP: IP address for egress traffic (source or destination)
  - MigrationPhase: Timeline phase (DEV, UAT, PROD waves)
  - StorageClass: Storage provisioner (source or destination)

RELATIONSHIPS:
  - (Namespace)-[:MIGRATES_FROM]->(SourceCluster)
  - (Namespace)-[:MIGRATES_TO]->(DestinationCluster)
  - (Namespace)-[:HAS_SOURCE_EGRESS]->(EgressIP)
  - (Namespace)-[:HAS_DEST_EGRESS]->(EgressIP)
  - (Namespace)-[:SCHEDULED_IN]->(MigrationPhase)
  - (SourceCluster)-[:MAPS_TO]->(DestinationCluster)
  - (DestinationCluster)-[:HAS_CONFIG]->(ClusterConfig)
  - (SourceCluster)-[:HAS_STORAGE_CLASS]->(StorageClass)
  - (DestinationCluster)-[:HAS_STORAGE_CLASS]->(StorageClass)

Data Sources:
-------------
  - Namespaces: Excel export from migration portal
  - Clusters: Derived from namespace mappings
  - ClusterConfig: Confluence table (VIPs, Infra Nodes, SSO)
  - MigrationPhases: Static timeline from migration documentation
  - StorageClasses: Static reference from platform documentation
"""

from neo4j import GraphDatabase, RoutingControl
from typing import List


# =============================================================================
# Node Constraints
# =============================================================================

# Using UNIQUE constraints (Community Edition compatible)
# NODE KEY constraints require Enterprise Edition
MIGRATION_NODE_CONSTRAINTS = [
    # Core migration entities
    "CREATE CONSTRAINT namespace_id IF NOT EXISTS FOR (n:Namespace) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT source_cluster_id IF NOT EXISTS FOR (n:SourceCluster) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT dest_cluster_id IF NOT EXISTS FOR (n:DestinationCluster) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT cluster_config_id IF NOT EXISTS FOR (n:ClusterConfig) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT egress_ip_id IF NOT EXISTS FOR (n:EgressIP) REQUIRE n.id IS UNIQUE",
    
    # Migration timeline
    "CREATE CONSTRAINT migration_phase_id IF NOT EXISTS FOR (n:MigrationPhase) REQUIRE n.id IS UNIQUE",
    
    # Storage reference
    "CREATE CONSTRAINT storage_class_id IF NOT EXISTS FOR (n:StorageClass) REQUIRE n.id IS UNIQUE",
]


# =============================================================================
# Indexes for Query Performance
# =============================================================================

MIGRATION_INDEXES = [
    # Namespace lookups
    "CREATE INDEX namespace_name IF NOT EXISTS FOR (n:Namespace) ON (n.name)",
    "CREATE INDEX namespace_env IF NOT EXISTS FOR (n:Namespace) ON (n.env)",
    "CREATE INDEX namespace_app_id IF NOT EXISTS FOR (n:Namespace) ON (n.app_id)",
    "CREATE INDEX namespace_sector IF NOT EXISTS FOR (n:Namespace) ON (n.sector)",
    "CREATE INDEX namespace_region IF NOT EXISTS FOR (n:Namespace) ON (n.region)",
    "CREATE INDEX namespace_org IF NOT EXISTS FOR (n:Namespace) ON (n.org)",
    "CREATE INDEX namespace_app_manager IF NOT EXISTS FOR (n:Namespace) ON (n.app_manager)",
    
    # Cluster lookups
    "CREATE INDEX source_cluster_name IF NOT EXISTS FOR (n:SourceCluster) ON (n.name)",
    "CREATE INDEX source_cluster_dc IF NOT EXISTS FOR (n:SourceCluster) ON (n.data_center)",
    "CREATE INDEX dest_cluster_name IF NOT EXISTS FOR (n:DestinationCluster) ON (n.name)",
    "CREATE INDEX dest_cluster_dc IF NOT EXISTS FOR (n:DestinationCluster) ON (n.data_center)",
    
    # EgressIP lookups
    "CREATE INDEX egress_ip_type IF NOT EXISTS FOR (n:EgressIP) ON (n.ip_type)",
    "CREATE INDEX egress_ip_address IF NOT EXISTS FOR (n:EgressIP) ON (n.ip_address)",
    
    # Migration phase lookups
    "CREATE INDEX phase_name IF NOT EXISTS FOR (n:MigrationPhase) ON (n.name)",
    "CREATE INDEX phase_status IF NOT EXISTS FOR (n:MigrationPhase) ON (n.status)",
    
    # Storage class lookups
    "CREATE INDEX storage_class_name IF NOT EXISTS FOR (n:StorageClass) ON (n.name)",
    "CREATE INDEX storage_class_platform IF NOT EXISTS FOR (n:StorageClass) ON (n.platform)",
]


# =============================================================================
# Utility Functions
# =============================================================================

def create_migration_constraints(driver, verbose: bool = True) -> int:
    """
    Create all node constraints for migration knowledge graph.
    
    Args:
        driver: Neo4j driver
        verbose: Whether to print progress
        
    Returns:
        Number of constraints created
    """
    if verbose:
        print("Creating migration node constraints...")
    
    created = 0
    for constraint in MIGRATION_NODE_CONSTRAINTS:
        try:
            driver.execute_query(constraint, routing_=RoutingControl.WRITE)
            created += 1
            if verbose:
                # Extract constraint name
                name = constraint.split('IF NOT EXISTS')[0].split()[-1]
                print(f"  [ok] {name}")
        except Exception as e:
            if "already exists" not in str(e).lower():
                if verbose:
                    print(f"  [warn] Constraint error: {e}")
    
    if verbose:
        print(f"Created {created} constraints.")
    
    return created


def create_migration_indexes(driver, verbose: bool = True) -> int:
    """
    Create all indexes for migration knowledge graph.
    
    Args:
        driver: Neo4j driver
        verbose: Whether to print progress
        
    Returns:
        Number of indexes created
    """
    if verbose:
        print("Creating migration indexes...")
    
    created = 0
    for index in MIGRATION_INDEXES:
        try:
            driver.execute_query(index, routing_=RoutingControl.WRITE)
            created += 1
            if verbose:
                # Extract index name
                name = index.split('IF NOT EXISTS')[0].split()[-1]
                print(f"  [ok] {name}")
        except Exception as e:
            if "already exists" not in str(e).lower():
                if verbose:
                    print(f"  [warn] Index error: {e}")
    
    if verbose:
        print(f"Created {created} indexes.")
    
    return created


def create_migration_schema(driver, verbose: bool = True) -> None:
    """
    Create all constraints and indexes for the Migration Knowledge Graph.
    
    This is the main entry point for initializing the migration graph schema.
    
    Args:
        driver: Neo4j driver
        verbose: Whether to print progress
    """
    if verbose:
        print("=" * 60)
        print("Creating Migration Knowledge Graph Schema")
        print("VCS 1.0 → Vandelay Cloud (BareMetal OpenShift)")
        print("=" * 60)
    
    create_migration_constraints(driver, verbose)
    create_migration_indexes(driver, verbose)
    
    if verbose:
        print("=" * 60)
        print("Migration schema creation complete!")
        print("=" * 60)


def clear_migration_data(driver, verbose: bool = True) -> None:
    """
    Clear all migration-related nodes from the database.
    
    WARNING: This deletes all migration nodes but preserves FSI data!
    
    Args:
        driver: Neo4j driver
        verbose: Whether to print progress
    """
    if verbose:
        print("Clearing existing migration data...")
    
    # Delete migration-specific node types (preserves FSI data)
    migration_labels = [
        'Namespace', 'SourceCluster', 'DestinationCluster', 'ClusterConfig',
        'EgressIP', 'MigrationPhase', 'StorageClass'
    ]
    
    for label in migration_labels:
        driver.execute_query(
            f"MATCH (n:{label}) DETACH DELETE n",
            routing_=RoutingControl.WRITE
        )
        if verbose:
            print(f"  Deleted all {label} nodes")
    
    if verbose:
        print("Migration data cleared.")


def get_migration_schema_summary() -> str:
    """
    Get a human-readable summary of the Migration Knowledge Graph schema.
    
    Returns:
        Multi-line string describing the schema
    """
    return """
Migration Knowledge Graph Schema
================================

Purpose: Support VCS 1.0 to Vandelay Cloud (BareMetal OpenShift) migration

Data Sources (CSV files from portal exports):
---------------------------------------------
- namespaces.csv: Excel export with App_ID, Namespace, App_Name, Source_ECS,
                  Destination_Cluster, Cluster_Type, Data_Center, ENV, Sector,
                  Region, App_M, SupportManag, Org, L3-L6 hierarchy,
                  Source/Dest Egress IPs, Network_Type
- cluster_mappings.csv: Source VCS Cluster to Destination Vandelay Cloud Cluster
- cluster_configs.csv: Vandelay Cluster, Cluster Subnet, VIP Name, VIP IP,
                       Infra node IPs, SM_REGHOST_HOSTNAME, SSO_SHARED_SECRET
- migration_phases.csv: Static timeline (DEV, UAT, PROD waves)
- storage_classes.csv: Static storage class reference

Node Types:
-----------
- Namespace: Application namespace being migrated
  Properties: id, name, app_name, app_id, env, sector, region, data_center,
              network_type, cluster_type, app_manager, support_manager,
              org, l3, l3_head, l4, l4_head, l5, l5_head, l6_business, l6_tech

- SourceCluster: VCS 1.0 cluster (migration source)
  Properties: id, name, cluster_type, platform

- DestinationCluster: Vandelay Cloud cluster (migration target)
  Properties: id, name, cluster_type, platform

- ClusterConfig: Configuration for destination cluster
  Properties: id, cluster_id, cluster_subnet, vip_name, vip_ip_address,
              infra_node_ips, sm_reghost_hostname, sso_shared_secret

- EgressIP: IP address for egress traffic
  Properties: id, ip_address, ip_type (source|destination)

- MigrationPhase: Timeline phase (DEV, UAT, PROD waves)
  Properties: id, name, description, start_date, end_date, status

- StorageClass: Storage provisioner configuration
  Properties: id, name, provisioner, platform, is_default, notes

Relationships:
--------------
- (Namespace)-[:MIGRATES_FROM]->(SourceCluster)
- (Namespace)-[:MIGRATES_TO]->(DestinationCluster)
- (Namespace)-[:HAS_SOURCE_EGRESS]->(EgressIP)
- (Namespace)-[:HAS_DEST_EGRESS]->(EgressIP)
- (Namespace)-[:SCHEDULED_IN]->(MigrationPhase)
- (SourceCluster)-[:MAPS_TO]->(DestinationCluster)
- (DestinationCluster)-[:HAS_CONFIG]->(ClusterConfig)
- (SourceCluster)-[:HAS_STORAGE_CLASS]->(StorageClass)
- (DestinationCluster)-[:HAS_STORAGE_CLASS]->(StorageClass)
"""
