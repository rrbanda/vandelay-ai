#!/usr/bin/env python3
"""Quick Neo4j connection and data verification."""

import argparse
import os
import sys

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: pip install neo4j")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri", default=os.environ.get('NEO4J_URI', 'bolt://localhost:7687'))
    parser.add_argument("--username", default=os.environ.get('NEO4J_USERNAME', 'neo4j'))
    parser.add_argument("--password", default=os.environ.get('NEO4J_PASSWORD', ''))
    args = parser.parse_args()

    print(f"Connecting to: {args.uri}")
    
    try:
        driver = GraphDatabase.driver(args.uri, auth=(args.username, args.password))
        driver.verify_connectivity()
        print("✅ Connected to Neo4j\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

    # Check node counts
    result = driver.execute_query(
        "MATCH (n) RETURN labels(n)[0] as label, count(*) as count ORDER BY label",
        result_transformer_=lambda r: r.data()
    )
    
    if result:
        print("Node counts:")
        for row in result:
            print(f"  {row['label']}: {row['count']}")
    else:
        print("⚠️  No nodes found in database")

    # Sample query
    result = driver.execute_query(
        "MATCH (ns:Namespace) RETURN ns.name as name LIMIT 3",
        result_transformer_=lambda r: r.data()
    )
    
    if result:
        print("\nSample namespaces:")
        for row in result:
            print(f"  - {row['name']}")
    else:
        print("\n⚠️  No Namespace nodes found")

    driver.close()

if __name__ == "__main__":
    main()
