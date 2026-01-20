"""
Migration Knowledge Graph Loader.

This module provides functions to load migration data from CSV files into Neo4j.

Data Sources (CSV files matching portal export):
- namespaces.csv: Application namespaces with cluster mappings and metadata
- cluster_mappings.csv: Source VCS to Destination Vandelay Cloud cluster mappings
- cluster_configs.csv: VIP, infra nodes, SSO configuration
- migration_phases.csv: Timeline phases (DEV, UAT, PROD waves) - static
- storage_classes.csv: Storage provisioner mappings - static

Column names match exactly what's exported from the migration portal.

Usage:
    from data_ingestion.loaders.migration_loader import MigrationGraphLoader
    
    loader = MigrationGraphLoader()
    loader.initialize_schema(clear_first=True)
    loader.load_from_csv("data/migration_csv")
    loader.print_summary()
"""

import csv
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, RoutingControl

from data_ingestion.config_loader import get_neo4j_config
from .migration_schema import create_migration_schema, clear_migration_data


# =============================================================================
# Configuration
# =============================================================================

def get_driver():
    """Get Neo4j driver from config.yaml (with env var overrides)."""
    config = get_neo4j_config()
    return GraphDatabase.driver(
        config['uri'],
        auth=(config['username'], config['password'])
    )


# =============================================================================
# Migration Graph Loader
# =============================================================================

class MigrationGraphLoader:
    """
    Load migration data from CSV files into Neo4j knowledge graph.
    
    CSV column names match exactly what's exported from the migration portal.
    """
    
    def __init__(self, driver=None):
        """
        Initialize the loader.
        
        Args:
            driver: Neo4j driver (creates one if not provided)
        """
        self.driver = driver or get_driver()
        
        self._stats = {
            'namespaces': 0,
            'source_clusters': 0,
            'destination_clusters': 0,
            'cluster_configs': 0,
            'egress_ips': 0,
            'migration_phases': 0,
            'storage_classes': 0,
            'relationships': 0,
        }
        
        # Track unique entities to avoid duplicates
        self._seen_source_clusters = set()
        self._seen_dest_clusters = set()
        self._seen_egress_ips = set()
    
    def close(self):
        """Close the Neo4j driver."""
        if self.driver:
            self.driver.close()
    
    def initialize_schema(self, clear_first: bool = False, verbose: bool = True):
        """
        Initialize the database schema.
        
        Args:
            clear_first: Whether to clear existing migration data first
            verbose: Whether to print progress
        """
        if clear_first:
            clear_migration_data(self.driver, verbose)
        create_migration_schema(self.driver, verbose)
    
    # =========================================================================
    # CSV Reading Utilities
    # =========================================================================
    
    def _read_csv(self, filepath: str) -> List[Dict[str, str]]:
        """
        Read a CSV file and return list of dicts.
        
        Args:
            filepath: Path to CSV file
            
        Returns:
            List of row dicts
        """
        rows = []
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Strip whitespace from keys and values
                cleaned = {k.strip(): v.strip() if v else '' for k, v in row.items()}
                rows.append(cleaned)
        return rows
    
    def _parse_list(self, value: str) -> List[str]:
        """Parse a comma-separated string into a list."""
        if not value:
            return []
        return [item.strip() for item in value.split(',') if item.strip()]
    
    def _parse_bool(self, value: str) -> bool:
        """Parse a string to boolean."""
        return value.lower() in ('true', 'yes', '1', 't', 'y')
    
    # =========================================================================
    # Cluster Mapping Loading
    # =========================================================================
    
    def load_cluster_mappings(self, filepath: str, verbose: bool = True):
        """
        Load cluster mappings from CSV file.
        
        Creates both SourceCluster and DestinationCluster nodes.
        
        CSV columns (from portal):
        - source_vcs_cluster
        - destination_vandelay_cluster
        
        Args:
            filepath: Path to cluster_mappings.csv
            verbose: Whether to print progress
        """
        if verbose:
            print(f"Loading cluster mappings from {filepath}...")
        
        rows = self._read_csv(filepath)
        
        for row in rows:
            source_cluster = row['source_vcs_cluster']
            dest_cluster = row['destination_vandelay_cluster']
            
            # Create SourceCluster if not seen
            if source_cluster and source_cluster not in self._seen_source_clusters:
                self.driver.execute_query(
                    """
                    MERGE (c:SourceCluster {id: $id})
                    SET c.name = $name,
                        c.cluster_type = 'VCS 1.0',
                        c.platform = 'VMware'
                    """,
                    id=source_cluster,
                    name=source_cluster,
                    routing_=RoutingControl.WRITE
                )
                self._seen_source_clusters.add(source_cluster)
                self._stats['source_clusters'] += 1
            
            # Create DestinationCluster if not seen
            if dest_cluster and dest_cluster not in self._seen_dest_clusters:
                self.driver.execute_query(
                    """
                    MERGE (c:DestinationCluster {id: $id})
                    SET c.name = $name,
                        c.cluster_type = 'Vandelay Cloud',
                        c.platform = 'BareMetal'
                    """,
                    id=dest_cluster,
                    name=dest_cluster,
                    routing_=RoutingControl.WRITE
                )
                self._seen_dest_clusters.add(dest_cluster)
                self._stats['destination_clusters'] += 1
            
            # Create MAPS_TO relationship
            if source_cluster and dest_cluster:
                self.driver.execute_query(
                    """
                    MATCH (src:SourceCluster {id: $src_id})
                    MATCH (dest:DestinationCluster {id: $dest_id})
                    MERGE (src)-[:MAPS_TO]->(dest)
                    """,
                    src_id=source_cluster,
                    dest_id=dest_cluster,
                    routing_=RoutingControl.WRITE
                )
                self._stats['relationships'] += 1
        
        if verbose:
            print(f"  [ok] Loaded {self._stats['source_clusters']} source clusters")
            print(f"  [ok] Loaded {self._stats['destination_clusters']} destination clusters")
    
    # =========================================================================
    # Cluster Config Loading
    # =========================================================================
    
    def load_cluster_configs(self, filepath: str, verbose: bool = True):
        """
        Load cluster configurations from CSV file.
        
        CSV columns (from Confluence VIP table):
        - vandelay_cluster (or Vandelay Cluster)
        - cluster_subnet
        - cluster_vip_name
        - cluster_vip_ip_address
        - infra_node_ips
        - sm_reghost_hostname
        - sso_shared_secret
        
        Args:
            filepath: Path to cluster_configs.csv
            verbose: Whether to print progress
        """
        if verbose:
            print(f"Loading cluster configs from {filepath}...")
        
        rows = self._read_csv(filepath)
        
        for row in rows:
            # Handle column name variations
            cluster_id = row.get('vandelay_cluster') or row.get('cluster_id', '')
            config_id = f"CFG-{cluster_id}"
            
            # Parse infra node IPs as list
            infra_nodes = self._parse_list(row.get('infra_node_ips', ''))
            
            # Create ClusterConfig node
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
            self._stats['cluster_configs'] += 1
            
            # Ensure DestinationCluster exists
            if cluster_id not in self._seen_dest_clusters:
                self.driver.execute_query(
                    """
                    MERGE (c:DestinationCluster {id: $id})
                    SET c.name = $name,
                        c.cluster_type = 'Vandelay Cloud',
                        c.platform = 'BareMetal'
                    """,
                    id=cluster_id,
                    name=cluster_id,
                    routing_=RoutingControl.WRITE
                )
                self._seen_dest_clusters.add(cluster_id)
                self._stats['destination_clusters'] += 1
            
            # Link to DestinationCluster
            self.driver.execute_query(
                """
                MATCH (c:DestinationCluster {id: $cluster_id})
                MATCH (cfg:ClusterConfig {id: $config_id})
                MERGE (c)-[:HAS_CONFIG]->(cfg)
                """,
                cluster_id=cluster_id,
                config_id=config_id,
                routing_=RoutingControl.WRITE
            )
            self._stats['relationships'] += 1
        
        if verbose:
            print(f"  [ok] Loaded {self._stats['cluster_configs']} cluster configs")
    
    # =========================================================================
    # Migration Phase Loading
    # =========================================================================
    
    def load_migration_phases(self, filepath: str, verbose: bool = True):
        """
        Load migration phases from CSV file.
        
        Args:
            filepath: Path to migration_phases.csv
            verbose: Whether to print progress
        """
        if verbose:
            print(f"Loading migration phases from {filepath}...")
        
        rows = self._read_csv(filepath)
        
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
            self._stats['migration_phases'] += 1
        
        if verbose:
            print(f"  [ok] Loaded {self._stats['migration_phases']} migration phases")
    
    # =========================================================================
    # Storage Class Loading
    # =========================================================================
    
    def load_storage_classes(self, filepath: str, verbose: bool = True):
        """
        Load storage classes from CSV file.
        
        Args:
            filepath: Path to storage_classes.csv
            verbose: Whether to print progress
        """
        if verbose:
            print(f"Loading storage classes from {filepath}...")
        
        rows = self._read_csv(filepath)
        
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
                is_default=self._parse_bool(row['is_default']),
                notes=row['notes'],
                routing_=RoutingControl.WRITE
            )
            self._stats['storage_classes'] += 1
        
        # Link storage classes to clusters
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
            print(f"  [ok] Loaded {self._stats['storage_classes']} storage classes")
    
    # =========================================================================
    # Namespace Loading (Main Data)
    # =========================================================================
    
    def load_namespaces(self, filepath: str, verbose: bool = True):
        """
        Load namespaces from CSV file.
        
        This is the main data file from the migration portal export.
        
        CSV columns (from portal - exact names):
        - namespace
        - app_id
        - app_name
        - source_vcs
        - destination_cluster
        - cluster_type
        - data_center
        - env
        - sector
        - region
        - app_m (app manager)
        - support_manag (support manager)
        - org
        - l3, l3_head, l4, l4_head, l5, l5_head
        - l6_business, l6_tech
        - source_egress_ip
        - destination_egress_ip
        - network_type
        
        Args:
            filepath: Path to namespaces.csv
            verbose: Whether to print progress
        """
        if verbose:
            print(f"Loading namespaces from {filepath}...")
        
        rows = self._read_csv(filepath)
        
        for row in rows:
            namespace_name = row['namespace']
            env = row['env']
            namespace_id = f"NS-{namespace_name}-{env}"
            
            # Create Namespace node with exact column names from portal
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
            self._stats['namespaces'] += 1
            
            # Ensure source cluster exists and link
            source_cluster = row.get('source_vcs', '')
            if source_cluster:
                if source_cluster not in self._seen_source_clusters:
                    self.driver.execute_query(
                        """
                        MERGE (c:SourceCluster {id: $id})
                        SET c.name = $name,
                            c.cluster_type = 'VCS 1.0',
                            c.platform = 'VMware'
                        """,
                        id=source_cluster,
                        name=source_cluster,
                        routing_=RoutingControl.WRITE
                    )
                    self._seen_source_clusters.add(source_cluster)
                    self._stats['source_clusters'] += 1
                
                self.driver.execute_query(
                    """
                    MATCH (ns:Namespace {id: $ns_id})
                    MATCH (src:SourceCluster {id: $src_id})
                    MERGE (ns)-[:MIGRATES_FROM]->(src)
                    """,
                    ns_id=namespace_id,
                    src_id=source_cluster,
                    routing_=RoutingControl.WRITE
                )
                self._stats['relationships'] += 1
            
            # Ensure destination cluster exists and link
            dest_cluster = row.get('destination_cluster', '')
            if dest_cluster:
                if dest_cluster not in self._seen_dest_clusters:
                    self.driver.execute_query(
                        """
                        MERGE (c:DestinationCluster {id: $id})
                        SET c.name = $name,
                            c.cluster_type = 'Vandelay Cloud',
                            c.platform = 'BareMetal'
                        """,
                        id=dest_cluster,
                        name=dest_cluster,
                        routing_=RoutingControl.WRITE
                    )
                    self._seen_dest_clusters.add(dest_cluster)
                    self._stats['destination_clusters'] += 1
                
                self.driver.execute_query(
                    """
                    MATCH (ns:Namespace {id: $ns_id})
                    MATCH (dest:DestinationCluster {id: $dest_id})
                    MERGE (ns)-[:MIGRATES_TO]->(dest)
                    """,
                    ns_id=namespace_id,
                    dest_id=dest_cluster,
                    routing_=RoutingControl.WRITE
                )
                self._stats['relationships'] += 1
            
            # Create and link source EgressIP
            source_egress = row.get('source_egress_ip', '')
            if source_egress and source_egress not in self._seen_egress_ips:
                self.driver.execute_query(
                    """
                    MERGE (ip:EgressIP {id: $id})
                    SET ip.ip_address = $ip_address,
                        ip.ip_type = 'source'
                    """,
                    id=f"EGRESS-{source_egress}",
                    ip_address=source_egress,
                    routing_=RoutingControl.WRITE
                )
                self._seen_egress_ips.add(source_egress)
                self._stats['egress_ips'] += 1
            
            if source_egress:
                self.driver.execute_query(
                    """
                    MATCH (ns:Namespace {id: $ns_id})
                    MATCH (ip:EgressIP {id: $ip_id})
                    MERGE (ns)-[:HAS_SOURCE_EGRESS]->(ip)
                    """,
                    ns_id=namespace_id,
                    ip_id=f"EGRESS-{source_egress}",
                    routing_=RoutingControl.WRITE
                )
                self._stats['relationships'] += 1
            
            # Create and link destination EgressIP
            dest_egress = row.get('destination_egress_ip', '')
            if dest_egress and dest_egress not in self._seen_egress_ips:
                self.driver.execute_query(
                    """
                    MERGE (ip:EgressIP {id: $id})
                    SET ip.ip_address = $ip_address,
                        ip.ip_type = 'destination'
                    """,
                    id=f"EGRESS-{dest_egress}",
                    ip_address=dest_egress,
                    routing_=RoutingControl.WRITE
                )
                self._seen_egress_ips.add(dest_egress)
                self._stats['egress_ips'] += 1
            
            if dest_egress:
                self.driver.execute_query(
                    """
                    MATCH (ns:Namespace {id: $ns_id})
                    MATCH (ip:EgressIP {id: $ip_id})
                    MERGE (ns)-[:HAS_DEST_EGRESS]->(ip)
                    """,
                    ns_id=namespace_id,
                    ip_id=f"EGRESS-{dest_egress}",
                    routing_=RoutingControl.WRITE
                )
                self._stats['relationships'] += 1
            
            # Link to migration phase based on env
            phase_map = {
                'DEV': 'PHASE-DEV',
                'UAT': 'PHASE-UAT',
                'PROD': 'PHASE-PROD-W1',
            }
            phase_id = phase_map.get(env.upper(), 'PHASE-DEV')
            self.driver.execute_query(
                """
                MATCH (ns:Namespace {id: $ns_id})
                MATCH (p:MigrationPhase {id: $phase_id})
                MERGE (ns)-[:SCHEDULED_IN]->(p)
                """,
                ns_id=namespace_id,
                phase_id=phase_id,
                routing_=RoutingControl.WRITE
            )
            self._stats['relationships'] += 1
        
        if verbose:
            print(f"  [ok] Loaded {self._stats['namespaces']} namespaces")
            print(f"  [ok] Created {self._stats['egress_ips']} egress IPs")
    
    # =========================================================================
    # Create Derived Relationships
    # =========================================================================
    
    def create_cluster_mappings_from_namespaces(self, verbose: bool = True):
        """
        Create MAPS_TO relationships between clusters based on namespace data.
        """
        if verbose:
            print("Creating cluster mappings from namespace data...")
        
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
        
        mappings = result['mappings'] if result else 0
        
        if verbose:
            print(f"  [ok] Created {mappings} cluster mappings")
    
    # =========================================================================
    # Main Load Method
    # =========================================================================
    
    def load_from_csv(self, csv_directory: str, verbose: bool = True):
        """
        Load all migration data from CSV files in directory.
        
        Args:
            csv_directory: Path to directory containing CSV files
            verbose: Whether to print progress
        """
        csv_dir = Path(csv_directory)
        
        if not csv_dir.exists():
            raise FileNotFoundError(f"CSV directory not found: {csv_directory}")
        
        if verbose:
            print("\n" + "=" * 60)
            print("Loading Migration Data from CSV Files")
            print("=" * 60)
        
        # Load in dependency order
        
        # 1. Migration phases (static reference data)
        phases_file = csv_dir / "migration_phases.csv"
        if phases_file.exists():
            self.load_migration_phases(str(phases_file), verbose)
        else:
            if verbose:
                print("  [skip] migration_phases.csv not found")
        
        # 2. Storage classes (static reference data)
        storage_file = csv_dir / "storage_classes.csv"
        if storage_file.exists():
            self.load_storage_classes(str(storage_file), verbose)
        else:
            if verbose:
                print("  [skip] storage_classes.csv not found")
        
        # 3. Cluster mappings (if separate file exists)
        mappings_file = csv_dir / "cluster_mappings.csv"
        if mappings_file.exists():
            self.load_cluster_mappings(str(mappings_file), verbose)
        
        # 4. Cluster configs (VIP, infra nodes, SSO)
        configs_file = csv_dir / "cluster_configs.csv"
        if configs_file.exists():
            self.load_cluster_configs(str(configs_file), verbose)
        else:
            if verbose:
                print("  [skip] cluster_configs.csv not found")
        
        # 5. Namespaces (main data, creates clusters if not already created)
        namespaces_file = csv_dir / "namespaces.csv"
        if namespaces_file.exists():
            self.load_namespaces(str(namespaces_file), verbose)
        else:
            raise FileNotFoundError(f"Required file not found: {namespaces_file}")
        
        # 6. Create derived cluster mappings from namespace data
        self.create_cluster_mappings_from_namespaces(verbose)
        
        if verbose:
            print("\n" + "=" * 60)
            print("CSV Loading Complete")
            print("=" * 60)
    
    # =========================================================================
    # Summary
    # =========================================================================
    
    def print_summary(self):
        """Print a summary of the loaded data."""
        print("\n" + "=" * 50)
        print("Migration Knowledge Graph Loading Summary")
        print("=" * 50)
        
        # Count nodes by label
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
        
        # Count relationships
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
        
        # Sample namespaces
        result = self.driver.execute_query(
            """
            MATCH (ns:Namespace)-[:MIGRATES_TO]->(dest:DestinationCluster)
            RETURN ns.name as namespace, ns.app_name as application, 
                   dest.name as destination, ns.env as env
            LIMIT 5
            """,
            result_transformer_=lambda r: r.data()
        )
        
        if result:
            print("\nSample namespaces:")
            for row in result:
                print(f"  {row['namespace']} ({row['application']}) → {row['destination']} [{row['env']}]")
    
    def get_stats(self) -> Dict[str, int]:
        """Get loading statistics."""
        return self._stats.copy()
