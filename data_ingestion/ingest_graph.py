#!/usr/bin/env python3
"""
Neo4j Graph Ingestion Script
=============================

Standalone script to ingest FSI data into Neo4j Knowledge Graph.

Features:
- Clears existing data before ingestion (optional)
- Supports data from git repository URL or local files
- Loads sample Cypher data directly (no LLM extraction needed)
- Can run on container startup

Usage:
    # Use local data (default)
    python -m data_ingestion.ingest_graph
    
    # Use data from git URL
    python -m data_ingestion.ingest_graph --git-url https://github.com/user/repo.git
    
    # Clear existing data first
    python -m data_ingestion.ingest_graph --clear
    
    # Specify cypher file path
    python -m data_ingestion.ingest_graph --cypher-file data/fsi_sample_data.cypher

Environment Variables:
    NEO4J_URI: Neo4j connection URI (default: bolt://localhost:7687)
    NEO4J_USERNAME: Neo4j username (default: neo4j)
    NEO4J_PASSWORD: Neo4j password
    DATA_GIT_URL: Git repository URL for data source
    DATA_GIT_BRANCH: Git branch (default: main)
"""

import argparse
import os
import sys
import time
from pathlib import Path

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

from data_ingestion.config_loader import get_neo4j_config
from data_ingestion.git_data_source import get_data_source, GitDataSource


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


def clear_database(driver, verbose: bool = True) -> int:
    """
    Clear all data from Neo4j database.
    
    Args:
        driver: Neo4j driver
        verbose: Print progress
        
    Returns:
        Number of nodes deleted
    """
    if verbose:
        print("Clearing existing data...")
    
    result = driver.execute_query(
        "MATCH (n) DETACH DELETE n RETURN count(n) as deleted",
        result_transformer_=lambda r: r.single()
    )
    
    deleted = result["deleted"] if result else 0
    
    if verbose:
        print(f"[ok] Deleted {deleted} nodes")
    
    return deleted


def load_cypher_file(driver, cypher_content: str, verbose: bool = True, log_queries: bool = False) -> bool:
    """
    Load Cypher statements from content string.
    
    Args:
        driver: Neo4j driver
        cypher_content: Cypher statements as string
        verbose: Print progress
        log_queries: Print each query being executed
        
    Returns:
        True if successful
    """
    if verbose:
        print("Loading Cypher data...")
    
    # Split into individual statements
    # Remove comments and empty lines for counting
    statements = []
    current_statement = []
    
    for line in cypher_content.split('\n'):
        stripped = line.strip()
        
        # Skip comments and empty lines
        if not stripped or stripped.startswith('//'):
            continue
        
        current_statement.append(line)
        
        # Check if statement ends with semicolon
        if stripped.endswith(';'):
            statement = '\n'.join(current_statement)
            statements.append(statement.rstrip(';'))
            current_statement = []
    
    # Add any remaining statement
    if current_statement:
        statements.append('\n'.join(current_statement))
    
    if verbose:
        print(f"  Found {len(statements)} statements")
    
    # Execute statements
    success_count = 0
    error_count = 0
    
    for i, statement in enumerate(statements):
        try:
            if log_queries:
                # Print the query before execution
                stmt_preview = statement.replace('\n', ' ').strip()
                if len(stmt_preview) > 120:
                    stmt_preview = stmt_preview[:117] + "..."
                print(f"  [{i+1:3d}] {stmt_preview}")
            
            driver.execute_query(statement)
            success_count += 1
        except Exception as e:
            error_count += 1
            if verbose:
                # Only show first 100 chars of statement
                stmt_preview = statement[:100].replace('\n', ' ')
                print(f"  [warn] Statement {i+1} failed: {str(e)[:50]}...")
    
    if verbose:
        print(f"[ok] Executed {success_count} statements")
        if error_count > 0:
            print(f"[warn] {error_count} statements failed")
    
    return error_count == 0


def verify_data(driver, verbose: bool = True) -> dict:
    """
    Verify loaded data and return statistics.
    
    Args:
        driver: Neo4j driver
        verbose: Print summary
        
    Returns:
        Dict with node and relationship counts
    """
    # Count nodes by label
    node_result = driver.execute_query(
        """
        MATCH (n)
        RETURN labels(n)[0] as label, count(*) as count
        ORDER BY count DESC
        """,
        result_transformer_=lambda r: r.data()
    )
    
    # Count relationships
    rel_result = driver.execute_query(
        """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(*) as count
        ORDER BY count DESC
        """,
        result_transformer_=lambda r: r.data()
    )
    
    stats = {
        'nodes': {row['label']: row['count'] for row in node_result},
        'relationships': {row['type']: row['count'] for row in rel_result},
        'total_nodes': sum(row['count'] for row in node_result),
        'total_relationships': sum(row['count'] for row in rel_result),
    }
    
    if verbose:
        print("\n" + "=" * 50)
        print("Graph Database Summary")
        print("=" * 50)
        print(f"Total nodes: {stats['total_nodes']}")
        print(f"Total relationships: {stats['total_relationships']}")
        print("\nNodes by type:")
        for label, count in stats['nodes'].items():
            print(f"  {label}: {count}")
        print("\nRelationships by type:")
        for rel_type, count in stats['relationships'].items():
            print(f"  {rel_type}: {count}")
    
    return stats


def run_graph_ingestion(
    git_url: str = None,
    git_branch: str = "main",
    cypher_file: str = "data/fsi_sample_data.cypher",
    clear_first: bool = True,
    wait_for_db: bool = True,
    verbose: bool = True,
    log_queries: bool = False,
) -> dict:
    """
    Run the graph ingestion pipeline.
    
    Args:
        git_url: Git repository URL for data source (None for local)
        git_branch: Git branch to use
        cypher_file: Path to cypher file within data source
        clear_first: Clear existing data before loading
        wait_for_db: Wait for Neo4j to be available
        verbose: Print progress
        log_queries: Print each Cypher query being executed
        
    Returns:
        Dict with ingestion results
    """
    if verbose:
        print("=" * 60)
        print("NEO4J GRAPH INGESTION")
        print("=" * 60)
    
    # Get Neo4j config
    neo4j_config = get_neo4j_config()
    uri = neo4j_config['uri']
    username = neo4j_config['username']
    password = neo4j_config['password']
    
    if verbose:
        print(f"Neo4j URI: {uri}")
        print(f"Data source: {git_url or 'local'}")
        print(f"Cypher file: {cypher_file}")
        print(f"Clear first: {clear_first}")
        print()
    
    # Wait for Neo4j if needed
    if wait_for_db:
        if not wait_for_neo4j(uri, username, password):
            return {'success': False, 'error': 'Neo4j not available'}
    
    # Connect to Neo4j
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
    except Exception as e:
        return {'success': False, 'error': f'Failed to connect: {e}'}
    
    try:
        # Get data source
        data_source = get_data_source(git_url, git_branch)
        
        # Load cypher content
        if verbose:
            print(f"\nLoading data from: {cypher_file}")
        
        cypher_content = data_source.fetch_cypher_file(cypher_file)
        
        # Clear if requested
        if clear_first:
            clear_database(driver, verbose)
        
        # Load data
        load_cypher_file(driver, cypher_content, verbose, log_queries)
        
        # Verify
        stats = verify_data(driver, verbose)
        
        # Cleanup data source
        data_source.cleanup()
        
        if verbose:
            print("\n" + "=" * 60)
            print("GRAPH INGESTION COMPLETE!")
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
        driver.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Neo4j Graph Ingestion - Load FSI data into Knowledge Graph"
    )
    
    parser.add_argument(
        "--git-url",
        type=str,
        default=os.environ.get('DATA_GIT_URL'),
        help="Git repository URL for data source"
    )
    parser.add_argument(
        "--git-branch",
        type=str,
        default=os.environ.get('DATA_GIT_BRANCH', 'main'),
        help="Git branch to use (default: main)"
    )
    parser.add_argument(
        "--cypher-file",
        type=str,
        default="data/fsi_sample_data.cypher",
        help="Path to Cypher file within data source"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        default=True,
        help="Clear existing data before loading (default: True)"
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Don't clear existing data"
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
    parser.add_argument(
        "--log-queries",
        action="store_true",
        help="Log each Cypher query being executed (useful for debugging)"
    )
    
    args = parser.parse_args()
    
    # Handle clear flag
    clear_first = not args.no_clear
    
    result = run_graph_ingestion(
        git_url=args.git_url,
        git_branch=args.git_branch,
        cypher_file=args.cypher_file,
        clear_first=clear_first,
        wait_for_db=not args.no_wait,
        verbose=not args.quiet,
        log_queries=args.log_queries,
    )
    
    if not result['success']:
        print(f"\n[ERROR] Ingestion failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
