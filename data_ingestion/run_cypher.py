#!/usr/bin/env python3
"""
Run Cypher queries against Neo4j.

Usage:
    python run_cypher.py --password YOUR_PASSWORD
    python run_cypher.py --password YOUR_PASSWORD --query "MATCH (n) RETURN count(n)"
"""

import argparse
import os
import sys

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: pip install neo4j")
    sys.exit(1)


DEFAULT_QUERIES = [
    ("Database info", "CALL dbms.components() YIELD name, versions RETURN name, versions"),
    ("Total nodes", "MATCH (n) RETURN count(n) as total_nodes"),
    ("Nodes by label", "MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY count DESC"),
    ("Total relationships", "MATCH ()-[r]->() RETURN count(r) as total_relationships"),
    ("Sample namespaces", "MATCH (ns:Namespace) RETURN ns.name as namespace, ns.app_name as app LIMIT 5"),
    ("Migration paths", """
        MATCH (ns:Namespace)-[:MIGRATES_FROM]->(src:SourceCluster)
        MATCH (ns)-[:MIGRATES_TO]->(dest:DestinationCluster)
        RETURN ns.name as namespace, src.name as source, dest.name as destination
        LIMIT 5
    """),
]


def run_query(driver, query: str, title: str = None):
    """Run a single Cypher query and print results."""
    if title:
        print(f"\n{'='*50}")
        print(f"  {title}")
        print(f"{'='*50}")
    
    try:
        result = driver.execute_query(query, result_transformer_=lambda r: r.data())
        
        if not result:
            print("  (no results)")
            return
        
        # Print results
        for i, row in enumerate(result):
            if i == 0:
                # Print header
                print("  " + " | ".join(str(k) for k in row.keys()))
                print("  " + "-" * 40)
            print("  " + " | ".join(str(v) for v in row.values()))
            
    except Exception as e:
        print(f"  ERROR: {e}")


def main():
    parser = argparse.ArgumentParser(description="Run Cypher queries against Neo4j")
    parser.add_argument("--uri", default=os.environ.get('NEO4J_URI', 'bolt://localhost:7687'))
    parser.add_argument("--username", default=os.environ.get('NEO4J_USERNAME', 'neo4j'))
    parser.add_argument("--password", default=os.environ.get('NEO4J_PASSWORD', ''))
    parser.add_argument("--query", "-q", help="Custom Cypher query to run")
    args = parser.parse_args()

    if not args.password:
        print("ERROR: --password required")
        sys.exit(1)

    print(f"Connecting to: {args.uri}")
    
    try:
        driver = GraphDatabase.driver(args.uri, auth=(args.username, args.password))
        driver.verify_connectivity()
        print("✅ Connected to Neo4j")
    except Exception as e:
        print(f"❌ Connection FAILED: {e}")
        sys.exit(1)

    if args.query:
        # Run custom query
        run_query(driver, args.query, "Custom Query")
    else:
        # Run default queries
        for title, query in DEFAULT_QUERIES:
            run_query(driver, query, title)

    driver.close()
    print("\n✅ Done")


if __name__ == "__main__":
    main()
