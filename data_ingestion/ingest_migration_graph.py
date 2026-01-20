#!/usr/bin/env python3
"""
Migration Knowledge Graph Ingestion Script
============================================

Standalone script to ingest VCS to Vandelay Cloud migration data
into Neo4j Knowledge Graph from CSV files.

This script handles migration-specific data including:
- Namespaces and cluster mappings
- EgressIP configurations
- Migration phases and timeline
- Cluster configurations (VIP, infra nodes, SSO)
- Storage class mappings

Data Sources:
- namespaces.csv: Excel export from migration portal
- clusters.csv: Derived cluster information
- cluster_configs.csv: Confluence VIP/SSO table
- migration_phases.csv: Timeline from documentation
- storage_classes.csv: Platform reference data

Usage:
    # Load from local CSV files (default)
    python -m data_ingestion.ingest_migration_graph
    
    # Clear migration data first
    python -m data_ingestion.ingest_migration_graph --clear
    
    # Specify custom CSV directory
    python -m data_ingestion.ingest_migration_graph --csv-dir path/to/csvs

Environment Variables:
    NEO4J_URI: Neo4j connection URI (default: bolt://localhost:7687)
    NEO4J_USERNAME: Neo4j username (default: neo4j)
    NEO4J_PASSWORD: Neo4j password
"""

import argparse
import os
import sys
import time
from pathlib import Path

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

from data_ingestion.config_loader import get_neo4j_config
from data_ingestion.loaders.migration_loader import MigrationGraphLoader
from data_ingestion.loaders.migration_schema import clear_migration_data


# Default CSV directory relative to this file
DEFAULT_CSV_DIR = Path(__file__).parent / "data" / "migration_csv"


def wait_for_neo4j(uri: str, username: str, password: str, max_retries: int = 30, delay: int = 2) -> bool:
    """
    Wait for Neo4j to be available.
    
    Args:
        uri: Neo4j URI
        username: Neo4j username
        password: Neo4j password
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        True if Neo4j is available, False otherwise
    """
    print(f"Waiting for Neo4j at {uri}...")
    
    for attempt in range(max_retries):
        try:
            driver = GraphDatabase.driver(uri, auth=(username, password))
            driver.verify_connectivity()
            driver.close()
            print(f"[ok] Neo4j is available (attempt {attempt + 1})")
            return True
        except (ServiceUnavailable, AuthError) as e:
            if attempt < max_retries - 1:
                print(f"  Attempt {attempt + 1}/{max_retries}: {type(e).__name__}")
                time.sleep(delay)
            else:
                print(f"[error] Neo4j not available after {max_retries} attempts")
                return False
        except Exception as e:
            print(f"  Unexpected error: {e}")
            time.sleep(delay)
    
    return False


def run_migration_graph_ingestion(
    csv_directory: str = None,
    clear_first: bool = True,
    wait_for_db: bool = True,
    verbose: bool = True,
) -> dict:
    """
    Run the migration graph ingestion pipeline.
    
    Args:
        csv_directory: Path to directory containing CSV files
        clear_first: Clear migration data before loading
        wait_for_db: Wait for Neo4j to be available
        verbose: Print progress
        
    Returns:
        Dict with ingestion results
    """
    if verbose:
        print("=" * 60)
        print("MIGRATION KNOWLEDGE GRAPH INGESTION")
        print("VCS 1.0 → Vandelay Cloud (BareMetal OpenShift)")
        print("=" * 60)
    
    # Resolve CSV directory
    if csv_directory is None:
        csv_directory = str(DEFAULT_CSV_DIR)
    
    csv_path = Path(csv_directory)
    if not csv_path.is_absolute():
        # Make relative to data_ingestion directory
        csv_path = Path(__file__).parent / csv_directory
    
    # Get Neo4j config
    neo4j_config = get_neo4j_config()
    uri = neo4j_config['uri']
    username = neo4j_config['username']
    password = neo4j_config['password']
    
    if verbose:
        print(f"Neo4j URI: {uri}")
        print(f"CSV Directory: {csv_path}")
        print(f"Clear first: {clear_first}")
        print()
    
    # Check CSV directory exists
    if not csv_path.exists():
        return {'success': False, 'error': f'CSV directory not found: {csv_path}'}
    
    # List CSV files
    csv_files = list(csv_path.glob("*.csv"))
    if not csv_files:
        return {'success': False, 'error': f'No CSV files found in: {csv_path}'}
    
    if verbose:
        print(f"Found {len(csv_files)} CSV files:")
        for f in csv_files:
            print(f"  - {f.name}")
        print()
    
    # Wait for Neo4j if needed
    if wait_for_db:
        if not wait_for_neo4j(uri, username, password):
            return {'success': False, 'error': 'Neo4j not available'}
    
    # Create loader and run
    loader = None
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        loader = MigrationGraphLoader(driver)
        
        # Initialize schema (optionally clear first)
        loader.initialize_schema(clear_first=clear_first, verbose=verbose)
        
        # Load data from CSV files
        loader.load_from_csv(str(csv_path), verbose=verbose)
        
        # Print summary
        loader.print_summary()
        
        stats = loader.get_stats()
        
        if verbose:
            print("\n" + "=" * 60)
            print("MIGRATION GRAPH INGESTION COMPLETE!")
            print("=" * 60)
        
        return {
            'success': True,
            'stats': stats,
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}
    
    finally:
        if loader:
            loader.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migration Graph Ingestion - Load migration data from CSV into Neo4j"
    )
    
    parser.add_argument(
        "--csv-dir",
        type=str,
        default=None,
        help=f"Directory containing CSV files (default: {DEFAULT_CSV_DIR})"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        default=False,
        help="Clear migration data before loading"
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for Neo4j to be available"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Reduce output verbosity"
    )
    
    args = parser.parse_args()
    
    result = run_migration_graph_ingestion(
        csv_directory=args.csv_dir,
        clear_first=args.clear,
        wait_for_db=not args.no_wait,
        verbose=not args.quiet,
    )
    
    if not result['success']:
        print(f"\n[ERROR] Ingestion failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
