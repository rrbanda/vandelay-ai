"""
Neo4j Constraints and Indexes for FSI Knowledge Graph.

This module defines the graph schema constraints and indexes
to ensure data integrity and query performance.

Schema Overview:
----------------

NODES:
  - Bank: id (key), name
  - Product: id (key), name, category
  - Feature: id (key), name
  - Fee: id (key), name
  - Reward: id (key), name
  - Requirement: id (key), name
  - Regulation: id (key), name, type
  - RegulatoryRequirement: id (key), name
  - RiskIndicator: id (key), name
  - Penalty: id (key), name
  - Risk: id (key), name, category
  - Portfolio: id (key), name
  - Counterparty: id (key), name
  - MitigationStrategy: id (key), name
  - RiskFactor: id (key), name
  - Document: id (key), name

RELATIONSHIPS:
  - (Bank)-[:OFFERS]->(Product)
  - (Bank)-[:COMPLIES_WITH]->(Regulation)
  - (Bank)-[:OWNS]->(Portfolio)
  - (Product)-[:HAS_FEE]->(Fee)
  - (Product)-[:HAS_FEATURE]->(Feature)
  - (Product)-[:HAS_REWARD]->(Reward)
  - (Product)-[:REQUIRES]->(Requirement)
  - (Regulation)-[:HAS_REQUIREMENT]->(RegulatoryRequirement)
  - (Regulation)-[:INDICATES_RISK]->(RiskIndicator)
  - (Regulation)-[:HAS_PENALTY]->(Penalty)
  - (Portfolio)-[:EXPOSED_TO]->(Risk)
  - (Portfolio)-[:HAS_COUNTERPARTY]->(Counterparty)
  - (Portfolio)-[:HAS_RISK_FACTOR]->(RiskFactor)
  - (Portfolio)-[:MITIGATED_BY]->(MitigationStrategy)
  - (Risk)-[:MITIGATED_BY]->(MitigationStrategy)
  - (*)-[:EXTRACTED_FROM]->(Document)
"""

from neo4j import GraphDatabase, RoutingControl
from typing import List


# =============================================================================
# Node Constraints
# =============================================================================

NODE_CONSTRAINTS = [
    # Core entities
    "CREATE CONSTRAINT bank_id IF NOT EXISTS FOR (n:Bank) REQUIRE (n.id) IS NODE KEY",
    "CREATE CONSTRAINT product_id IF NOT EXISTS FOR (n:Product) REQUIRE (n.id) IS NODE KEY",
    "CREATE CONSTRAINT regulation_id IF NOT EXISTS FOR (n:Regulation) REQUIRE (n.id) IS NODE KEY",
    "CREATE CONSTRAINT portfolio_id IF NOT EXISTS FOR (n:Portfolio) REQUIRE (n.id) IS NODE KEY",
    "CREATE CONSTRAINT counterparty_id IF NOT EXISTS FOR (n:Counterparty) REQUIRE (n.id) IS NODE KEY",
    "CREATE CONSTRAINT risk_id IF NOT EXISTS FOR (n:Risk) REQUIRE (n.id) IS NODE KEY",
    
    # Product components
    "CREATE CONSTRAINT feature_id IF NOT EXISTS FOR (n:Feature) REQUIRE (n.id) IS NODE KEY",
    "CREATE CONSTRAINT fee_id IF NOT EXISTS FOR (n:Fee) REQUIRE (n.id) IS NODE KEY",
    "CREATE CONSTRAINT reward_id IF NOT EXISTS FOR (n:Reward) REQUIRE (n.id) IS NODE KEY",
    "CREATE CONSTRAINT requirement_id IF NOT EXISTS FOR (n:Requirement) REQUIRE (n.id) IS NODE KEY",
    
    # Regulation components
    "CREATE CONSTRAINT regulatory_req_id IF NOT EXISTS FOR (n:RegulatoryRequirement) REQUIRE (n.id) IS NODE KEY",
    "CREATE CONSTRAINT risk_indicator_id IF NOT EXISTS FOR (n:RiskIndicator) REQUIRE (n.id) IS NODE KEY",
    "CREATE CONSTRAINT penalty_id IF NOT EXISTS FOR (n:Penalty) REQUIRE (n.id) IS NODE KEY",
    
    # Risk components
    "CREATE CONSTRAINT risk_factor_id IF NOT EXISTS FOR (n:RiskFactor) REQUIRE (n.id) IS NODE KEY",
    "CREATE CONSTRAINT mitigation_id IF NOT EXISTS FOR (n:MitigationStrategy) REQUIRE (n.id) IS NODE KEY",
    
    # Document provenance
    "CREATE CONSTRAINT document_id IF NOT EXISTS FOR (n:Document) REQUIRE (n.id) IS NODE KEY",
]


# =============================================================================
# Indexes for Query Performance
# =============================================================================

INDEXES = [
    # Name-based lookups
    "CREATE INDEX product_name IF NOT EXISTS FOR (n:Product) ON (n.name)",
    "CREATE INDEX product_category IF NOT EXISTS FOR (n:Product) ON (n.category)",
    "CREATE INDEX regulation_name IF NOT EXISTS FOR (n:Regulation) ON (n.name)",
    "CREATE INDEX regulation_type IF NOT EXISTS FOR (n:Regulation) ON (n.type)",
    "CREATE INDEX portfolio_name IF NOT EXISTS FOR (n:Portfolio) ON (n.name)",
    "CREATE INDEX counterparty_name IF NOT EXISTS FOR (n:Counterparty) ON (n.name)",
    "CREATE INDEX risk_name IF NOT EXISTS FOR (n:Risk) ON (n.name)",
    "CREATE INDEX risk_category IF NOT EXISTS FOR (n:Risk) ON (n.category)",
    
    # Document lookups
    "CREATE INDEX document_name IF NOT EXISTS FOR (n:Document) ON (n.name)",
]


# =============================================================================
# Utility Functions
# =============================================================================

def create_constraints(driver, verbose: bool = True) -> int:
    """
    Create all node constraints.
    
    Args:
        driver: Neo4j driver
        verbose: Whether to print progress
        
    Returns:
        Number of constraints created
    """
    if verbose:
        print("Creating node constraints...")
    
    created = 0
    for constraint in NODE_CONSTRAINTS:
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


def create_indexes(driver, verbose: bool = True) -> int:
    """
    Create all indexes.
    
    Args:
        driver: Neo4j driver
        verbose: Whether to print progress
        
    Returns:
        Number of indexes created
    """
    if verbose:
        print("Creating indexes...")
    
    created = 0
    for index in INDEXES:
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


def create_all_schema(driver, verbose: bool = True) -> None:
    """
    Create all constraints and indexes for the FSI Knowledge Graph.
    
    This is the main entry point for initializing the graph schema.
    
    Args:
        driver: Neo4j driver
        verbose: Whether to print progress
    """
    if verbose:
        print("=" * 50)
        print("Creating FSI Knowledge Graph Schema")
        print("=" * 50)
    
    create_constraints(driver, verbose)
    create_indexes(driver, verbose)
    
    if verbose:
        print("=" * 50)
        print("Schema creation complete!")
        print("=" * 50)


def clear_database(driver, verbose: bool = True) -> None:
    """
    Clear all data from the database.
    
    WARNING: This deletes ALL nodes and relationships!
    
    Args:
        driver: Neo4j driver
        verbose: Whether to print progress
    """
    if verbose:
        print("Clearing existing data...")
    
    driver.execute_query(
        "MATCH (n) DETACH DELETE n",
        routing_=RoutingControl.WRITE
    )
    
    if verbose:
        print("Database cleared.")


def drop_all_constraints(driver, verbose: bool = True) -> None:
    """
    Drop all constraints (for schema migration).
    
    Args:
        driver: Neo4j driver
        verbose: Whether to print progress
    """
    if verbose:
        print("Dropping all constraints...")
    
    result = driver.execute_query(
        "SHOW CONSTRAINTS",
        result_transformer_=lambda r: r.data()
    )
    
    for constraint in result:
        name = constraint.get('name')
        if name:
            try:
                driver.execute_query(
                    f"DROP CONSTRAINT {name}",
                    routing_=RoutingControl.WRITE
                )
                if verbose:
                    print(f"  Dropped: {name}")
            except Exception as e:
                if verbose:
                    print(f"  Error dropping {name}: {e}")
    
    if verbose:
        print("Constraints dropped.")


def get_schema_summary() -> str:
    """
    Get a human-readable summary of the FSI Knowledge Graph schema.
    
    Returns:
        Multi-line string describing the schema
    """
    return """
FSI Knowledge Graph Schema
==========================

Node Types:
-----------
- Bank: Financial institution (root entity)
- Product: Banking products (checking, savings, loans, cards)
- Fee: Fees associated with products
- Feature: Features of products
- Reward: Reward programs (credit cards)
- Requirement: Product requirements
- Regulation: Compliance regulations (Basel III, AML, KYC)
- RegulatoryRequirement: Specific requirements within regulations
- RiskIndicator: AML/KYC risk indicators
- Penalty: Penalties for non-compliance
- Risk: Risk categories
- Portfolio: Financial portfolios
- Counterparty: Entities with counterparty risk
- RiskFactor: Factors contributing to risk
- MitigationStrategy: Risk mitigation strategies
- Document: Source documents (provenance)

Relationships:
--------------
- (Bank)-[:OFFERS]->(Product)
- (Bank)-[:COMPLIES_WITH]->(Regulation)
- (Bank)-[:OWNS]->(Portfolio)
- (Product)-[:HAS_FEE]->(Fee)
- (Product)-[:HAS_FEATURE]->(Feature)
- (Product)-[:HAS_REWARD]->(Reward)
- (Product)-[:REQUIRES]->(Requirement)
- (Regulation)-[:HAS_REQUIREMENT]->(RegulatoryRequirement)
- (Regulation)-[:INDICATES_RISK]->(RiskIndicator)
- (Regulation)-[:HAS_PENALTY]->(Penalty)
- (Portfolio)-[:HAS_RISK_FACTOR]->(RiskFactor)
- (Portfolio)-[:MITIGATED_BY]->(MitigationStrategy)
- (*)-[:EXTRACTED_FROM]->(Document)
"""
