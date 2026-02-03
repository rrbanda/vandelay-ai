#!/usr/bin/env python3
"""
Test Migration Knowledge Graph Ingestion
=========================================

Run after ingestion to verify data was loaded correctly.

Usage:
    python test_ingestion.py --uri bolt://localhost:7687 --password YOUR_PASSWORD
"""

import argparse
import os
import sys

try:
    from neo4j import GraphDatabase
except ImportError:
    print("ERROR: neo4j package not installed. Run: pip install neo4j")
    sys.exit(1)


def run_tests(uri: str, username: str, password: str):
    """Run all verification tests."""
    
    print("=" * 60)
    print("MIGRATION KNOWLEDGE GRAPH - VERIFICATION TESTS")
    print("=" * 60)
    print(f"Neo4j URI: {uri}")
    print()
    
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    tests_passed = 0
    tests_failed = 0
    
    # Test 1: Node counts
    print("TEST 1: Node Counts")
    print("-" * 40)
    
    expected_counts = {
        'Namespace': 10,
        'SourceCluster': 2,
        'DestinationCluster': 2,
        'ClusterConfig': 2,
        'MigrationPhase': 5,
        'StorageClass': 4,
    }
    
    result = driver.execute_query(
        """
        MATCH (n)
        WHERE n:Namespace OR n:SourceCluster OR n:DestinationCluster 
              OR n:ClusterConfig OR n:EgressIP OR n:MigrationPhase OR n:StorageClass
        RETURN labels(n)[0] as label, count(*) as count
        ORDER BY label
        """,
        result_transformer_=lambda r: r.data()
    )
    
    actual_counts = {row['label']: row['count'] for row in result}
    
    for label, expected in expected_counts.items():
        actual = actual_counts.get(label, 0)
        status = "✓" if actual >= expected else "✗"
        print(f"  {status} {label}: {actual} (expected >= {expected})")
        if actual >= expected:
            tests_passed += 1
        else:
            tests_failed += 1
    
    # Test 2: Relationships
    print()
    print("TEST 2: Relationship Counts")
    print("-" * 40)
    
    expected_rels = {
        'MIGRATES_FROM': 10,
        'MIGRATES_TO': 10,
        'MAPS_TO': 2,
        'HAS_CONFIG': 2,
    }
    
    result = driver.execute_query(
        """
        MATCH ()-[r]->()
        WHERE type(r) IN ['MIGRATES_FROM', 'MIGRATES_TO', 'MAPS_TO', 'HAS_CONFIG',
                          'HAS_SOURCE_EGRESS', 'HAS_DEST_EGRESS', 'SCHEDULED_IN', 'HAS_STORAGE_CLASS']
        RETURN type(r) as type, count(*) as count
        ORDER BY type
        """,
        result_transformer_=lambda r: r.data()
    )
    
    actual_rels = {row['type']: row['count'] for row in result}
    
    for rel_type, expected in expected_rels.items():
        actual = actual_rels.get(rel_type, 0)
        status = "✓" if actual >= expected else "✗"
        print(f"  {status} {rel_type}: {actual} (expected >= {expected})")
        if actual >= expected:
            tests_passed += 1
        else:
            tests_failed += 1
    
    # Test 3: Sample namespace query
    print()
    print("TEST 3: Sample Namespace Query")
    print("-" * 40)
    
    result = driver.execute_query(
        """
        MATCH (ns:Namespace {name: 'payments-api'})-[:MIGRATES_FROM]->(src:SourceCluster)
        MATCH (ns)-[:MIGRATES_TO]->(dest:DestinationCluster)
        RETURN ns.name as namespace, ns.app_name as app, 
               src.name as source, dest.name as destination
        """,
        result_transformer_=lambda r: r.data()
    )
    
    if result and len(result) > 0:
        row = result[0]
        print(f"  ✓ Found: {row['namespace']} ({row['app']})")
        print(f"    Source: {row['source']} → Destination: {row['destination']}")
        tests_passed += 1
    else:
        print("  ✗ Namespace 'payments-api' not found")
        tests_failed += 1
    
    # Test 4: Cluster config query
    print()
    print("TEST 4: Cluster Config Query")
    print("-" * 40)
    
    result = driver.execute_query(
        """
        MATCH (dest:DestinationCluster)-[:HAS_CONFIG]->(cfg:ClusterConfig)
        RETURN dest.name as cluster, cfg.vip_name as vip, cfg.sm_reghost_hostname as sso_host
        LIMIT 1
        """,
        result_transformer_=lambda r: r.data()
    )
    
    if result and len(result) > 0:
        row = result[0]
        print(f"  ✓ Cluster: {row['cluster']}")
        print(f"    VIP: {row['vip']}")
        print(f"    SSO Host: {row['sso_host']}")
        tests_passed += 1
    else:
        print("  ✗ No cluster configs found")
        tests_failed += 1
    
    # Test 5: Migration phase query
    print()
    print("TEST 5: Migration Phases")
    print("-" * 40)
    
    result = driver.execute_query(
        """
        MATCH (p:MigrationPhase)
        RETURN p.name as phase, p.status as status, p.start_date as start
        ORDER BY p.start_date
        """,
        result_transformer_=lambda r: r.data()
    )
    
    if result and len(result) >= 5:
        for row in result:
            print(f"  ✓ {row['phase']}: {row['status']} (starts: {row['start']})")
        tests_passed += 1
    else:
        print(f"  ✗ Expected 5 phases, found {len(result)}")
        tests_failed += 1
    
    # Summary
    print()
    print("=" * 60)
    total = tests_passed + tests_failed
    if tests_failed == 0:
        print(f"ALL TESTS PASSED ({tests_passed}/{total})")
        print("=" * 60)
        print()
        print("✅ Ingestion verified successfully!")
    else:
        print(f"TESTS: {tests_passed} passed, {tests_failed} failed")
        print("=" * 60)
        print()
        print("❌ Some tests failed. Check if ingestion ran correctly.")
    
    driver.close()
    
    return tests_failed == 0


def main():
    parser = argparse.ArgumentParser(description="Test Migration Knowledge Graph Ingestion")
    parser.add_argument("--uri", type=str, default=os.environ.get('NEO4J_URI', 'bolt://localhost:7687'))
    parser.add_argument("--username", type=str, default=os.environ.get('NEO4J_USERNAME', 'neo4j'))
    parser.add_argument("--password", type=str, default=os.environ.get('NEO4J_PASSWORD', ''))
    
    args = parser.parse_args()
    
    if not args.password:
        print("ERROR: Neo4j password required. Use --password or set NEO4J_PASSWORD")
        sys.exit(1)
    
    success = run_tests(args.uri, args.username, args.password)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
