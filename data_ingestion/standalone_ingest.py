#!/usr/bin/env python3
"""
Standalone Migration Knowledge Graph Ingestion Script
======================================================

Self-contained script to ingest migration data into Neo4j.
Copy this file along with the 'migration_csv' folder to any machine with Python 3.9+.

Requirements:
    pip install neo4j

Usage:
    # Set environment variables
    export NEO4J_URI="bolt://your-neo4j-host:7687"
    export NEO4J_USERNAME="neo4j"
    export NEO4J_PASSWORD="your-password"
    
    # Run ingestion
    python standalone_ingest.py
    
    # Or with command line args
    python standalone_ingest.py --uri bolt://host:7687 --username neo4j --password pass --csv-dir ./migration_csv
"""

import argparse
import csv
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

try:
    from neo4j import GraphDatabase, RoutingControl
    from neo4j.exceptions import ServiceUnavailable, AuthError
except ImportError:
    print("ERROR: neo4j package not installed. Run: pip install neo4j")
    sys.exit(1)


# =============================================================================
# Schema Definitions
# =============================================================================

# Using UNIQUE constraints (Community Edition compatible)
# NODE KEY constraints require Enterprise Edition
MIGRATION_NODE_CONSTRAINTS = [
    "CREATE CONSTRAINT namespace_id IF NOT EXISTS FOR (n:Namespace) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT source_cluster_id IF NOT EXISTS FOR (n:SourceCluster) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT dest_cluster_id IF NOT EXISTS FOR (n:DestinationCluster) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT cluster_config_id IF NOT EXISTS FOR (n:ClusterConfig) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT egress_ip_id IF NOT EXISTS FOR (n:EgressIP) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT migration_phase_id IF NOT EXISTS FOR (n:MigrationPhase) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT storage_class_id IF NOT EXISTS FOR (n:StorageClass) REQUIRE n.id IS UNIQUE",
]

MIGRATION_INDEXES = [
    "CREATE INDEX namespace_name IF NOT EXISTS FOR (n:Namespace) ON (n.name)",
    "CREATE INDEX namespace_env IF NOT EXISTS FOR (n:Namespace) ON (n.env)",
    "CREATE INDEX namespace_app_id IF NOT EXISTS FOR (n:Namespace) ON (n.app_id)",
    "CREATE INDEX namespace_sector IF NOT EXISTS FOR (n:Namespace) ON (n.sector)",
    "CREATE INDEX namespace_region IF NOT EXISTS FOR (n:Namespace) ON (n.region)",
    "CREATE INDEX namespace_org IF NOT EXISTS FOR (n:Namespace) ON (n.org)",
    "CREATE INDEX namespace_app_manager IF NOT EXISTS FOR (n:Namespace) ON (n.app_manager)",
    "CREATE INDEX source_cluster_name IF NOT EXISTS FOR (n:SourceCluster) ON (n.name)",
    "CREATE INDEX dest_cluster_name IF NOT EXISTS FOR (n:DestinationCluster) ON (n.name)",
    "CREATE INDEX egress_ip_address IF NOT EXISTS FOR (n:EgressIP) ON (n.ip_address)",
    "CREATE INDEX phase_name IF NOT EXISTS FOR (n:MigrationPhase) ON (n.name)",
    "CREATE INDEX storage_class_name IF NOT EXISTS FOR (n:StorageClass) ON (n.name)",
]

MIGRATION_LABELS = [
    'Namespace', 'SourceCluster', 'DestinationCluster', 'ClusterConfig',
    'EgressIP', 'MigrationPhase', 'StorageClass'
]


# =============================================================================
# Helper Functions
# =============================================================================

def wait_for_neo4j(uri: str, username: str, password: str, max_retries: int = 10) -> bool:
    """Wait for Neo4j to be available."""
    print(f"Connecting to Neo4j at {uri}...")
    
    for attempt in range(max_retries):
        try:
            driver = GraphDatabase.driver(uri, auth=(username, password))
            driver.verify_connectivity()
            driver.close()
            print(f"  [OK] Connected to Neo4j")
            return True
        except (ServiceUnavailable, AuthError) as e:
            if attempt < max_retries - 1:
                print(f"  Attempt {attempt + 1}/{max_retries}: {type(e).__name__}")
                time.sleep(2)
            else:
                print(f"  [ERROR] Cannot connect: {e}")
                return False
        except Exception as e:
            print(f"  [ERROR] Unexpected error: {e}")
            return False
    return False


def read_csv(filepath: str) -> List[Dict[str, str]]:
    """Read a CSV file and return list of dicts."""
    rows = []
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cleaned = {k.strip(): v.strip() if v else '' for k, v in row.items()}
            rows.append(cleaned)
    return rows


def parse_list(value: str) -> List[str]:
    """Parse a comma-separated string into a list."""
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def parse_bool(value: str) -> bool:
    """Parse a string to boolean."""
    return value.lower() in ('true', 'yes', '1', 't', 'y')


# =============================================================================
# Schema Operations
# =============================================================================

def create_schema(driver, verbose: bool = True):
    """Create constraints and indexes."""
    if verbose:
        print("\n" + "=" * 60)
        print("Creating Migration Knowledge Graph Schema")
        print("=" * 60)
    
    # Create constraints
    if verbose:
        print("\nCreating constraints...")
    for constraint in MIGRATION_NODE_CONSTRAINTS:
        try:
            driver.execute_query(constraint, routing_=RoutingControl.WRITE)
            if verbose:
                name = constraint.split('IF NOT EXISTS')[0].split()[-1]
                print(f"  [OK] {name}")
        except Exception as e:
            if "already exists" not in str(e).lower():
                if verbose:
                    print(f"  [WARN] {e}")
    
    # Create indexes
    if verbose:
        print("\nCreating indexes...")
    for index in MIGRATION_INDEXES:
        try:
            driver.execute_query(index, routing_=RoutingControl.WRITE)
            if verbose:
                name = index.split('IF NOT EXISTS')[0].split()[-1]
                print(f"  [OK] {name}")
        except Exception as e:
            if "already exists" not in str(e).lower():
                if verbose:
                    print(f"  [WARN] {e}")


def clear_data(driver, verbose: bool = True):
    """Clear all migration-related nodes."""
    if verbose:
        print("\nClearing existing migration data...")
    
    for label in MIGRATION_LABELS:
        driver.execute_query(
            f"MATCH (n:{label}) DETACH DELETE n",
            routing_=RoutingControl.WRITE
        )
        if verbose:
            print(f"  Deleted all {label} nodes")


# =============================================================================
# Data Loading Functions
# =============================================================================

class MigrationLoader:
    """Load migration data from CSV files into Neo4j."""
    
    def __init__(self, driver):
        self.driver = driver
        self.stats = {
            'namespaces': 0,
            'source_clusters': 0,
            'destination_clusters': 0,
            'cluster_configs': 0,
            'egress_ips': 0,
            'migration_phases': 0,
            'storage_classes': 0,
            'relationships': 0,
        }
        self._seen_source_clusters = set()
        self._seen_dest_clusters = set()
        self._seen_egress_ips = set()
    
    def load_migration_phases(self, filepath: str, verbose: bool = True):
        """Load migration phases."""
        if verbose:
            print(f"\nLoading migration phases from {filepath}...")
        
        rows = read_csv(filepath)
        for row in rows:
            self.driver.execute_query(
                """
                MERGE (p:MigrationPhase {id: $id})
                SET p.name = $name,
                    p.description = $description,
                    p.start_date = date($start_date),
                    p.end_date = date($end_date),
                    p.status = $status
                """,
                id=row['phase_id'],
                name=row['name'],
                description=row['description'],
                start_date=row['start_date'],
                end_date=row['end_date'],
                status=row['status'],
                routing_=RoutingControl.WRITE
            )
            self.stats['migration_phases'] += 1
        
        if verbose:
            print(f"  [OK] Loaded {self.stats['migration_phases']} migration phases")
    
    def load_storage_classes(self, filepath: str, verbose: bool = True):
        """Load storage classes."""
        if verbose:
            print(f"\nLoading storage classes from {filepath}...")
        
        rows = read_csv(filepath)
        for row in rows:
            self.driver.execute_query(
                """
                MERGE (sc:StorageClass {id: $id})
                SET sc.name = $name,
                    sc.provisioner = $provisioner,
                    sc.platform = $platform,
                    sc.is_default = $is_default,
                    sc.notes = $notes
                """,
                id=row['storage_class_id'],
                name=row['name'],
                provisioner=row['provisioner'],
                platform=row['platform'],
                is_default=parse_bool(row['is_default']),
                notes=row['notes'],
                routing_=RoutingControl.WRITE
            )
            self.stats['storage_classes'] += 1
        
        if verbose:
            print(f"  [OK] Loaded {self.stats['storage_classes']} storage classes")
    
    def load_cluster_mappings(self, filepath: str, verbose: bool = True):
        """Load cluster mappings."""
        if verbose:
            print(f"\nLoading cluster mappings from {filepath}...")
        
        rows = read_csv(filepath)
        for row in rows:
            source_cluster = row['source_vcs_cluster']
            dest_cluster = row['destination_vandelay_cluster']
            
            if source_cluster and source_cluster not in self._seen_source_clusters:
                self.driver.execute_query(
                    """
                    MERGE (c:SourceCluster {id: $id})
                    SET c.name = $name, c.cluster_type = 'VCS 1.0', c.platform = 'VMware'
                    """,
                    id=source_cluster, name=source_cluster,
                    routing_=RoutingControl.WRITE
                )
                self._seen_source_clusters.add(source_cluster)
                self.stats['source_clusters'] += 1
            
            if dest_cluster and dest_cluster not in self._seen_dest_clusters:
                self.driver.execute_query(
                    """
                    MERGE (c:DestinationCluster {id: $id})
                    SET c.name = $name, c.cluster_type = 'Vandelay Cloud', c.platform = 'BareMetal'
                    """,
                    id=dest_cluster, name=dest_cluster,
                    routing_=RoutingControl.WRITE
                )
                self._seen_dest_clusters.add(dest_cluster)
                self.stats['destination_clusters'] += 1
            
            if source_cluster and dest_cluster:
                self.driver.execute_query(
                    """
                    MATCH (src:SourceCluster {id: $src_id})
                    MATCH (dest:DestinationCluster {id: $dest_id})
                    MERGE (src)-[:MAPS_TO]->(dest)
                    """,
                    src_id=source_cluster, dest_id=dest_cluster,
                    routing_=RoutingControl.WRITE
                )
                self.stats['relationships'] += 1
        
        if verbose:
            print(f"  [OK] Loaded {self.stats['source_clusters']} source clusters")
            print(f"  [OK] Loaded {self.stats['destination_clusters']} destination clusters")
    
    def load_cluster_configs(self, filepath: str, verbose: bool = True):
        """Load cluster configurations."""
        if verbose:
            print(f"\nLoading cluster configs from {filepath}...")
        
        rows = read_csv(filepath)
        for row in rows:
            cluster_id = row.get('vandelay_cluster') or row.get('cluster_id', '')
            config_id = f"CFG-{cluster_id}"
            infra_nodes = parse_list(row.get('infra_node_ips', ''))
            
            self.driver.execute_query(
                """
                MERGE (cfg:ClusterConfig {id: $id})
                SET cfg.cluster_id = $cluster_id,
                    cfg.cluster_subnet = $cluster_subnet,
                    cfg.vip_name = $vip_name,
                    cfg.vip_ip_address = $vip_ip_address,
                    cfg.infra_node_ips = $infra_node_ips,
                    cfg.sm_reghost_hostname = $sm_reghost_hostname,
                    cfg.sso_shared_secret = $sso_shared_secret
                """,
                id=config_id,
                cluster_id=cluster_id,
                cluster_subnet=row.get('cluster_subnet', ''),
                vip_name=row.get('cluster_vip_name', ''),
                vip_ip_address=row.get('cluster_vip_ip_address', ''),
                infra_node_ips=infra_nodes,
                sm_reghost_hostname=row.get('sm_reghost_hostname', ''),
                sso_shared_secret=row.get('sso_shared_secret', ''),
                routing_=RoutingControl.WRITE
            )
            self.stats['cluster_configs'] += 1
            
            # Ensure cluster exists
            if cluster_id not in self._seen_dest_clusters:
                self.driver.execute_query(
                    """
                    MERGE (c:DestinationCluster {id: $id})
                    SET c.name = $name, c.cluster_type = 'Vandelay Cloud', c.platform = 'BareMetal'
                    """,
                    id=cluster_id, name=cluster_id,
                    routing_=RoutingControl.WRITE
                )
                self._seen_dest_clusters.add(cluster_id)
                self.stats['destination_clusters'] += 1
            
            # Link config to cluster
            self.driver.execute_query(
                """
                MATCH (c:DestinationCluster {id: $cluster_id})
                MATCH (cfg:ClusterConfig {id: $config_id})
                MERGE (c)-[:HAS_CONFIG]->(cfg)
                """,
                cluster_id=cluster_id, config_id=config_id,
                routing_=RoutingControl.WRITE
            )
            self.stats['relationships'] += 1
        
        if verbose:
            print(f"  [OK] Loaded {self.stats['cluster_configs']} cluster configs")
    
    def load_namespaces(self, filepath: str, verbose: bool = True):
        """Load namespaces - main data file."""
        if verbose:
            print(f"\nLoading namespaces from {filepath}...")
        
        rows = read_csv(filepath)
        for row in rows:
            namespace_name = row['namespace']
            env = row['env']
            namespace_id = f"NS-{namespace_name}-{env}"
            
            # Create Namespace
            self.driver.execute_query(
                """
                MERGE (ns:Namespace {id: $id})
                SET ns.name = $name,
                    ns.app_id = $app_id,
                    ns.app_name = $app_name,
                    ns.cluster_type = $cluster_type,
                    ns.data_center = $data_center,
                    ns.env = $env,
                    ns.sector = $sector,
                    ns.region = $region,
                    ns.network_type = $network_type,
                    ns.app_manager = $app_m,
                    ns.support_manager = $support_manag,
                    ns.org = $org,
                    ns.l3 = $l3,
                    ns.l3_head = $l3_head,
                    ns.l4 = $l4,
                    ns.l4_head = $l4_head,
                    ns.l5 = $l5,
                    ns.l5_head = $l5_head,
                    ns.l6_business = $l6_business,
                    ns.l6_tech = $l6_tech
                """,
                id=namespace_id,
                name=namespace_name,
                app_id=row.get('app_id', ''),
                app_name=row.get('app_name', ''),
                cluster_type=row.get('cluster_type', ''),
                data_center=row.get('data_center', ''),
                env=env,
                sector=row.get('sector', ''),
                region=row.get('region', ''),
                network_type=row.get('network_type', ''),
                app_m=row.get('app_m', ''),
                support_manag=row.get('support_manag', ''),
                org=row.get('org', ''),
                l3=row.get('l3', ''),
                l3_head=row.get('l3_head', ''),
                l4=row.get('l4', ''),
                l4_head=row.get('l4_head', ''),
                l5=row.get('l5', ''),
                l5_head=row.get('l5_head', ''),
                l6_business=row.get('l6_business', ''),
                l6_tech=row.get('l6_tech', ''),
                routing_=RoutingControl.WRITE
            )
            self.stats['namespaces'] += 1
            
            # Source cluster
            source_cluster = row.get('source_vcs', '')
            if source_cluster:
                if source_cluster not in self._seen_source_clusters:
                    self.driver.execute_query(
                        """
                        MERGE (c:SourceCluster {id: $id})
                        SET c.name = $name, c.cluster_type = 'VCS 1.0', c.platform = 'VMware'
                        """,
                        id=source_cluster, name=source_cluster,
                        routing_=RoutingControl.WRITE
                    )
                    self._seen_source_clusters.add(source_cluster)
                    self.stats['source_clusters'] += 1
                
                self.driver.execute_query(
                    """
                    MATCH (ns:Namespace {id: $ns_id})
                    MATCH (src:SourceCluster {id: $src_id})
                    MERGE (ns)-[:MIGRATES_FROM]->(src)
                    """,
                    ns_id=namespace_id, src_id=source_cluster,
                    routing_=RoutingControl.WRITE
                )
                self.stats['relationships'] += 1
            
            # Destination cluster
            dest_cluster = row.get('destination_cluster', '')
            if dest_cluster:
                if dest_cluster not in self._seen_dest_clusters:
                    self.driver.execute_query(
                        """
                        MERGE (c:DestinationCluster {id: $id})
                        SET c.name = $name, c.cluster_type = 'Vandelay Cloud', c.platform = 'BareMetal'
                        """,
                        id=dest_cluster, name=dest_cluster,
                        routing_=RoutingControl.WRITE
                    )
                    self._seen_dest_clusters.add(dest_cluster)
                    self.stats['destination_clusters'] += 1
                
                self.driver.execute_query(
                    """
                    MATCH (ns:Namespace {id: $ns_id})
                    MATCH (dest:DestinationCluster {id: $dest_id})
                    MERGE (ns)-[:MIGRATES_TO]->(dest)
                    """,
                    ns_id=namespace_id, dest_id=dest_cluster,
                    routing_=RoutingControl.WRITE
                )
                self.stats['relationships'] += 1
            
            # Source EgressIP
            source_egress = row.get('source_egress_ip', '')
            if source_egress:
                if source_egress not in self._seen_egress_ips:
                    self.driver.execute_query(
                        """
                        MERGE (ip:EgressIP {id: $id})
                        SET ip.ip_address = $ip_address, ip.ip_type = 'source'
                        """,
                        id=f"EGRESS-{source_egress}", ip_address=source_egress,
                        routing_=RoutingControl.WRITE
                    )
                    self._seen_egress_ips.add(source_egress)
                    self.stats['egress_ips'] += 1
                
                self.driver.execute_query(
                    """
                    MATCH (ns:Namespace {id: $ns_id})
                    MATCH (ip:EgressIP {id: $ip_id})
                    MERGE (ns)-[:HAS_SOURCE_EGRESS]->(ip)
                    """,
                    ns_id=namespace_id, ip_id=f"EGRESS-{source_egress}",
                    routing_=RoutingControl.WRITE
                )
                self.stats['relationships'] += 1
            
            # Destination EgressIP
            dest_egress = row.get('destination_egress_ip', '')
            if dest_egress:
                if dest_egress not in self._seen_egress_ips:
                    self.driver.execute_query(
                        """
                        MERGE (ip:EgressIP {id: $id})
                        SET ip.ip_address = $ip_address, ip.ip_type = 'destination'
                        """,
                        id=f"EGRESS-{dest_egress}", ip_address=dest_egress,
                        routing_=RoutingControl.WRITE
                    )
                    self._seen_egress_ips.add(dest_egress)
                    self.stats['egress_ips'] += 1
                
                self.driver.execute_query(
                    """
                    MATCH (ns:Namespace {id: $ns_id})
                    MATCH (ip:EgressIP {id: $ip_id})
                    MERGE (ns)-[:HAS_DEST_EGRESS]->(ip)
                    """,
                    ns_id=namespace_id, ip_id=f"EGRESS-{dest_egress}",
                    routing_=RoutingControl.WRITE
                )
                self.stats['relationships'] += 1
            
            # Link to migration phase
            phase_map = {'DEV': 'PHASE-DEV', 'UAT': 'PHASE-UAT', 'PROD': 'PHASE-PROD-W1'}
            phase_id = phase_map.get(env.upper(), 'PHASE-DEV')
            self.driver.execute_query(
                """
                MATCH (ns:Namespace {id: $ns_id})
                MATCH (p:MigrationPhase {id: $phase_id})
                MERGE (ns)-[:SCHEDULED_IN]->(p)
                """,
                ns_id=namespace_id, phase_id=phase_id,
                routing_=RoutingControl.WRITE
            )
            self.stats['relationships'] += 1
        
        if verbose:
            print(f"  [OK] Loaded {self.stats['namespaces']} namespaces")
            print(f"  [OK] Created {self.stats['egress_ips']} egress IPs")
    
    def link_storage_classes(self, verbose: bool = True):
        """Link storage classes to clusters."""
        if verbose:
            print("\nLinking storage classes to clusters...")
        
        self.driver.execute_query(
            """
            MATCH (src:SourceCluster)
            MATCH (sc:StorageClass {platform: 'source'})
            MERGE (src)-[:HAS_STORAGE_CLASS]->(sc)
            """,
            routing_=RoutingControl.WRITE
        )
        
        self.driver.execute_query(
            """
            MATCH (dest:DestinationCluster)
            MATCH (sc:StorageClass {platform: 'destination'})
            MERGE (dest)-[:HAS_STORAGE_CLASS]->(sc)
            """,
            routing_=RoutingControl.WRITE
        )
        
        if verbose:
            print("  [OK] Linked storage classes")
    
    def create_cluster_mappings_from_namespaces(self, verbose: bool = True):
        """Create MAPS_TO relationships from namespace data."""
        if verbose:
            print("\nCreating cluster mappings from namespace data...")
        
        result = self.driver.execute_query(
            """
            MATCH (ns:Namespace)-[:MIGRATES_FROM]->(src:SourceCluster)
            MATCH (ns)-[:MIGRATES_TO]->(dest:DestinationCluster)
            WITH DISTINCT src, dest
            MERGE (src)-[:MAPS_TO]->(dest)
            RETURN count(*) as mappings
            """,
            routing_=RoutingControl.WRITE,
            result_transformer_=lambda r: r.single()
        )
        
        if verbose:
            mappings = result['mappings'] if result else 0
            print(f"  [OK] Created {mappings} cluster mappings")
    
    def print_summary(self):
        """Print loading summary."""
        print("\n" + "=" * 60)
        print("MIGRATION KNOWLEDGE GRAPH - LOADING SUMMARY")
        print("=" * 60)
        
        result = self.driver.execute_query(
            """
            MATCH (n)
            WHERE n:Namespace OR n:SourceCluster OR n:DestinationCluster 
                  OR n:ClusterConfig OR n:EgressIP OR n:MigrationPhase OR n:StorageClass
            RETURN labels(n)[0] as label, count(*) as count
            ORDER BY label
            """,
            result_transformer_=lambda r: r.data()
        )
        
        print("\nNode counts:")
        total_nodes = 0
        for row in result:
            print(f"  {row['label']}: {row['count']}")
            total_nodes += row['count']
        print(f"  TOTAL: {total_nodes}")
        
        result = self.driver.execute_query(
            """
            MATCH ()-[r]->()
            WHERE type(r) IN [
                'MIGRATES_FROM', 'MIGRATES_TO', 'HAS_SOURCE_EGRESS', 'HAS_DEST_EGRESS',
                'SCHEDULED_IN', 'MAPS_TO', 'HAS_CONFIG', 'HAS_STORAGE_CLASS'
            ]
            RETURN type(r) as type, count(*) as count
            ORDER BY type
            """,
            result_transformer_=lambda r: r.data()
        )
        
        print("\nRelationship counts:")
        total_rels = 0
        for row in result:
            print(f"  {row['type']}: {row['count']}")
            total_rels += row['count']
        print(f"  TOTAL: {total_rels}")
        
        # Sample data
        result = self.driver.execute_query(
            """
            MATCH (ns:Namespace)-[:MIGRATES_TO]->(dest:DestinationCluster)
            RETURN ns.name as namespace, ns.app_name as app, dest.name as dest, ns.env as env
            LIMIT 5
            """,
            result_transformer_=lambda r: r.data()
        )
        
        if result:
            print("\nSample namespaces:")
            for row in result:
                print(f"  {row['namespace']} ({row['app']}) -> {row['dest']} [{row['env']}]")


# =============================================================================
# Main Entry Point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Standalone Migration Knowledge Graph Ingestion"
    )
    parser.add_argument("--uri", type=str, default=os.environ.get('NEO4J_URI', 'bolt://localhost:7687'),
                        help="Neo4j URI (default: $NEO4J_URI or bolt://localhost:7687)")
    parser.add_argument("--username", type=str, default=os.environ.get('NEO4J_USERNAME', 'neo4j'),
                        help="Neo4j username (default: $NEO4J_USERNAME or neo4j)")
    parser.add_argument("--password", type=str, default=os.environ.get('NEO4J_PASSWORD', ''),
                        help="Neo4j password (default: $NEO4J_PASSWORD)")
    parser.add_argument("--csv-dir", type=str, default="./data/migration_csv",
                        help="Directory containing CSV files (default: ./data/migration_csv)")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before loading")
    parser.add_argument("--quiet", action="store_true", help="Reduce output")
    
    args = parser.parse_args()
    
    verbose = not args.quiet
    
    print("=" * 60)
    print("MIGRATION KNOWLEDGE GRAPH INGESTION")
    print("VCS 1.0 -> Vandelay Cloud (BareMetal OpenShift)")
    print("=" * 60)
    print(f"\nNeo4j URI: {args.uri}")
    print(f"CSV Directory: {args.csv_dir}")
    print(f"Clear first: {args.clear}")
    
    # Verify CSV directory
    csv_dir = Path(args.csv_dir)
    if not csv_dir.exists():
        print(f"\n[ERROR] CSV directory not found: {csv_dir}")
        sys.exit(1)
    
    # Check required files
    required_files = ['namespaces.csv']
    for fname in required_files:
        if not (csv_dir / fname).exists():
            print(f"\n[ERROR] Required file not found: {csv_dir / fname}")
            sys.exit(1)
    
    # Connect to Neo4j
    if not wait_for_neo4j(args.uri, args.username, args.password):
        sys.exit(1)
    
    driver = GraphDatabase.driver(args.uri, auth=(args.username, args.password))
    
    try:
        # Clear if requested
        if args.clear:
            clear_data(driver, verbose)
        
        # Create schema
        create_schema(driver, verbose)
        
        # Load data
        loader = MigrationLoader(driver)
        
        # 1. Migration phases
        phases_file = csv_dir / "migration_phases.csv"
        if phases_file.exists():
            loader.load_migration_phases(str(phases_file), verbose)
        
        # 2. Storage classes
        storage_file = csv_dir / "storage_classes.csv"
        if storage_file.exists():
            loader.load_storage_classes(str(storage_file), verbose)
        
        # 3. Cluster mappings
        mappings_file = csv_dir / "cluster_mappings.csv"
        if mappings_file.exists():
            loader.load_cluster_mappings(str(mappings_file), verbose)
        
        # 4. Cluster configs
        configs_file = csv_dir / "cluster_configs.csv"
        if configs_file.exists():
            loader.load_cluster_configs(str(configs_file), verbose)
        
        # 5. Namespaces (main data)
        loader.load_namespaces(str(csv_dir / "namespaces.csv"), verbose)
        
        # 6. Link storage classes
        loader.link_storage_classes(verbose)
        
        # 7. Create derived cluster mappings
        loader.create_cluster_mappings_from_namespaces(verbose)
        
        # Print summary
        loader.print_summary()
        
        print("\n" + "=" * 60)
        print("INGESTION COMPLETE!")
        print("=" * 60)
        
    finally:
        driver.close()


if __name__ == "__main__":
    main()
