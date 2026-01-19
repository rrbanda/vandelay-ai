"""
Cypher Expert Tools
====================

Tools for custom Cypher queries on Neo4j.
Enhanced with MCP-style schema introspection, query validation, and caching.
"""

import json
import os
import re
import time
from typing import List, Dict, Any, Optional, Union

from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, SessionExpired, TransientError

# Try to import ToolContext for state tracking and caching (optional)
try:
    from google.adk.tools.tool_context import ToolContext
    HAS_TOOL_CONTEXT = True
except ImportError:
    HAS_TOOL_CONTEXT = False
    ToolContext = None


# Singleton driver pattern
_neo4j_driver = None


def _get_driver():
    """Get Neo4j driver from environment variables (singleton)."""
    global _neo4j_driver
    if _neo4j_driver is None:
        uri = os.environ.get('NEO4J_URI', 'bolt://localhost:7687')
        username = os.environ.get('NEO4J_USERNAME', 'neo4j')
        password = os.environ.get('NEO4J_PASSWORD', 'fsi-graphrag-2024')
        _neo4j_driver = GraphDatabase.driver(uri, auth=(username, password))
    return _neo4j_driver


# =============================================================================
# FSI Domain Constants (for LLM guidance)
# =============================================================================

# Standard node types in the FSI knowledge graph
FSI_NODE_TYPES = [
    "Bank", "Product", "Fee", "Feature", "Reward", "Requirement",
    "Regulation", "RegulatoryRequirement", "RiskIndicator", "Penalty",
    "Portfolio", "Counterparty", "RiskFactor", "MitigationStrategy",
    "Customer", "Account", "Transaction", "Document"
]

# Standard relationship types
FSI_RELATIONSHIP_TYPES = [
    "OFFERS", "COMPLIES_WITH", "OWNS", "HAS_FEE", "HAS_FEATURE",
    "HAS_REWARD", "REQUIRES", "HAS_REQUIREMENT", "INDICATES_RISK",
    "HAS_PENALTY", "HAS_RISK_FACTOR", "MITIGATED_BY", "HAS_TRANSACTION",
    "EXTRACTED_FROM"
]

# Properties that should NEVER be returned (large vectors)
EMBEDDING_PROPERTIES = ["embedding", "vector", "embeddings", "text_embedding"]


# =============================================================================
# Schema Caching
# =============================================================================

_cached_schema: Optional[List[Dict[str, Any]]] = None
_schema_cache_time: float = 0
SCHEMA_CACHE_TTL_SECONDS = 300  # 5 minutes


def _get_cached_schema(context: Optional[ToolContext] = None) -> Optional[List[Dict[str, Any]]]:
    """
    Get cached schema from session state or module cache.
    
    Args:
        context: Optional ToolContext for session state caching
        
    Returns:
        Cached schema or None if not available/expired
    """
    global _cached_schema, _schema_cache_time
    
    # Try session state first (if available)
    if context is not None and HAS_TOOL_CONTEXT:
        schema_json = context.state.get("cypher_schema_cache")
        if schema_json:
            try:
                return json.loads(schema_json)
            except (json.JSONDecodeError, TypeError):
                pass
    
    # Fall back to module-level cache
    if _cached_schema is not None:
        if time.time() - _schema_cache_time < SCHEMA_CACHE_TTL_SECONDS:
            return _cached_schema
    
    return None


def _set_cached_schema(
    schema: List[Dict[str, Any]], 
    context: Optional[ToolContext] = None
) -> None:
    """
    Cache schema in session state and module cache.
    
    Args:
        schema: The schema to cache
        context: Optional ToolContext for session state caching
    """
    global _cached_schema, _schema_cache_time
    
    # Cache in module
    _cached_schema = schema
    _schema_cache_time = time.time()
    
    # Cache in session state (if available)
    if context is not None and HAS_TOOL_CONTEXT:
        context.state["cypher_schema_cache"] = json.dumps(schema)


# =============================================================================
# Enhanced Schema Introspection (MCP-style)
# =============================================================================

def get_graph_schema(
    context: Optional[ToolContext] = None,
    use_cache: bool = True
) -> List[Dict[str, Any]]:
    """
    Get the Neo4j graph schema in MCP-style structured format.
    
    IMPORTANT: Call this FIRST before writing any custom Cypher queries!
    The schema shows all node labels, their properties, and relationships.
    
    Args:
        context: Optional ToolContext for caching in session state
        use_cache: Whether to use cached schema (default True)
    
    Returns:
        List of schema entries, each containing:
        - label: Node label name
        - attributes: Dict of property names to types (with 'indexed' suffix if indexed)
        - relationships: Dict of relationship types to target node labels
    
    Example output:
        [
            {
                "label": "Customer",
                "attributes": {"id": "STRING indexed", "name": "STRING", "risk_level": "STRING"},
                "relationships": {"OWNS": "Account", "HAS_TRANSACTION": "Transaction"}
            },
            ...
        ]
    """
    # Check cache first
    if use_cache:
        cached = _get_cached_schema(context)
        if cached is not None:
            return cached
    
    driver = _get_driver()
    
    # Get node type properties
    node_props = driver.execute_query(
        """
        CALL db.schema.nodeTypeProperties() 
        YIELD nodeType, propertyName, propertyTypes, mandatory
        RETURN nodeType, 
               collect({
                   name: propertyName, 
                   type: propertyTypes[0],
                   mandatory: mandatory
               }) as properties
        """,
        result_transformer_=lambda r: r.data()
    )
    
    # Get indexes to mark indexed properties
    indexes = driver.execute_query(
        """
        SHOW INDEXES YIELD labelsOrTypes, properties, type
        WHERE type IN ['RANGE', 'BTREE', 'TEXT', 'FULLTEXT', 'POINT']
        RETURN labelsOrTypes[0] as label, properties as indexed_props
        """,
        result_transformer_=lambda r: r.data()
    )
    
    # Build index lookup
    indexed_by_label: Dict[str, List[str]] = {}
    for idx in indexes:
        label = idx.get('label')
        props = idx.get('indexed_props', [])
        if label:
            indexed_by_label.setdefault(label, []).extend(props)
    
    # Get relationship patterns
    rel_patterns = driver.execute_query(
        """
        CALL db.schema.visualization() YIELD nodes, relationships
        UNWIND relationships as rel
        RETURN startNode(rel).name as from_label,
               type(rel) as rel_type,
               endNode(rel).name as to_label
        """,
        result_transformer_=lambda r: r.data()
    )
    
    # Build relationship lookup by source label
    rels_by_label: Dict[str, Dict[str, str]] = {}
    for rel in rel_patterns:
        from_label = rel.get('from_label')
        rel_type = rel.get('rel_type')
        to_label = rel.get('to_label')
        if from_label and rel_type and to_label:
            rels_by_label.setdefault(from_label, {})[rel_type] = to_label
    
    # Build MCP-style schema
    schema: List[Dict[str, Any]] = []
    
    for node in node_props:
        node_type = node.get('nodeType', '')
        # Extract label from nodeType format like ":`Label`"
        label = node_type.replace(':`', '').replace('`', '').strip(':')
        if not label:
            continue
        
        # Build attributes dict with indexed markers
        attributes: Dict[str, str] = {}
        indexed_props = indexed_by_label.get(label, [])
        
        for prop in node.get('properties', []):
            prop_name = prop.get('name', '')
            prop_type = prop.get('type', 'STRING')
            
            # Skip embedding properties
            if prop_name.lower() in [p.lower() for p in EMBEDDING_PROPERTIES]:
                continue
                
            if prop_name in indexed_props:
                attributes[prop_name] = f"{prop_type} indexed"
            else:
                attributes[prop_name] = prop_type
        
        # Get relationships for this label
        relationships = rels_by_label.get(label, {})
        
        schema.append({
            "label": label,
            "attributes": attributes,
            "relationships": relationships
        })
    
    # Cache the schema
    _set_cached_schema(schema, context)
    
    return schema


def get_graph_schema_text(context: Optional[ToolContext] = None) -> str:
    """
    Get the graph schema as a human-readable text format.
    
    This is a convenience wrapper around get_graph_schema() that returns
    a formatted text string instead of structured data.
    
    Args:
        context: Optional ToolContext for caching
        
    Returns:
        Schema as formatted text string
    """
    schema = get_graph_schema(context)
    
    lines = [
        "=== FSI KNOWLEDGE GRAPH SCHEMA ===",
        "",
        "Standard FSI Domain Values:",
        f"  Node Types: {', '.join(FSI_NODE_TYPES[:8])}...",
        f"  Relationships: {', '.join(FSI_RELATIONSHIP_TYPES[:6])}...",
        "",
        "=== NODE LABELS ==="
    ]
    
    for entry in schema:
        label = entry.get('label', 'Unknown')
        attrs = entry.get('attributes', {})
        rels = entry.get('relationships', {})
        
        # Format attributes
        attr_strs = [f"{k}: {v}" for k, v in attrs.items()]
        attr_line = ', '.join(attr_strs) if attr_strs else 'no properties'
        
        lines.append(f"\n{label}:")
        lines.append(f"  Properties: {attr_line}")
        
        if rels:
            rel_strs = [f"-[:{k}]->{v}" for k, v in rels.items()]
            lines.append(f"  Relationships: {', '.join(rel_strs)}")
    
    lines.extend([
        "",
        "=== IMPORTANT NOTES ===",
        "- NEVER return embedding/vector properties (they are large arrays)",
        "- Always use LIMIT to prevent huge results",
        "- Use parameterized queries with $paramName syntax"
    ])
    
    return '\n'.join(lines)


# =============================================================================
# Query Validation and Execution
# =============================================================================

def _validate_query(query: str) -> tuple[str, List[str]]:
    """
    Validate and potentially modify a Cypher query.
    
    Args:
        query: The Cypher query to validate
        
    Returns:
        Tuple of (modified_query, list_of_warnings)
    """
    warnings: List[str] = []
    modified_query = query.strip()
    
    # Check for embedding properties in RETURN clause
    query_lower = query.lower()
    for emb_prop in EMBEDDING_PROPERTIES:
        if emb_prop.lower() in query_lower:
            if 'return' in query_lower:
                return_idx = query_lower.find('return')
                return_clause = query_lower[return_idx:]
                if emb_prop.lower() in return_clause:
                    warnings.append(
                        f"WARNING: Query returns '{emb_prop}' property which is a large vector. "
                        "Consider removing it from the RETURN clause."
                    )
    
    # Check if LIMIT is missing for queries that return data
    if 'return' in query_lower and 'limit' not in query_lower:
        # Check if it's a count/aggregation query (these are fine without LIMIT)
        is_aggregation = any(
            agg in query_lower 
            for agg in ['count(', 'sum(', 'avg(', 'collect(', 'min(', 'max(']
        )
        if not is_aggregation:
            # Add a reasonable default LIMIT
            modified_query = modified_query.rstrip(';') + " LIMIT 100"
            warnings.append(
                "Added 'LIMIT 100' to query. Consider adding your own LIMIT for large result sets."
            )
    
    return modified_query, warnings


def run_cypher_query(
    query: str,
    context: Optional[ToolContext] = None,
    max_retries: int = 3,
    validate: bool = True
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Execute a custom Cypher query against the Neo4j database with validation and retries.
    
    IMPORTANT: 
    - Get schema first using get_graph_schema()
    - Never return embedding properties (they're large vectors)
    - Always use LIMIT to prevent huge results
    
    Args:
        query: A valid Cypher query string
        context: Optional ToolContext for tracking in session state
        max_retries: Number of retries for transient errors (default 3)
        validate: Whether to validate/modify the query (default True)
        
    Returns:
        Query results as a list of dictionaries, or error dict if failed
    
    Example:
        results = run_cypher_query(
            "MATCH (c:Customer) WHERE c.risk_level = 'High' RETURN c.name, c.id LIMIT 10"
        )
    """
    # Validate query
    warnings: List[str] = []
    if validate:
        query, warnings = _validate_query(query)
    
    driver = _get_driver()
    last_error = None
    
    for attempt in range(max_retries):
        try:
            result = driver.execute_query(
                query,
                result_transformer_=lambda r: r.data()
            )
            
            # Build response
            if result:
                if warnings:
                    return {
                        "results": result,
                        "warnings": warnings,
                        "count": len(result)
                    }
                return result
            else:
                return [{
                    "message": "Query returned no results",
                    "query": query,
                    "warnings": warnings if warnings else None
                }]
                
        except (ServiceUnavailable, SessionExpired, TransientError) as e:
            last_error = e
            if attempt < max_retries - 1:
                # Exponential backoff
                wait_time = (2 ** attempt) * 0.5
                time.sleep(wait_time)
                continue
            else:
                return {
                    "error": f"Transient error after {max_retries} retries: {str(e)}",
                    "query": query,
                    "hint": "The database may be temporarily unavailable. Try again later."
                }
                
        except Exception as e:
            error_msg = str(e)
            
            # Provide helpful hints for common errors
            hints = []
            if "Unknown" in error_msg and "label" in error_msg.lower():
                hints.append("Use get_graph_schema() to see available node labels.")
            if "Unknown" in error_msg and "relationship" in error_msg.lower():
                hints.append("Use get_graph_schema() to see available relationship types.")
            if "syntax" in error_msg.lower():
                hints.append("Check Cypher syntax. Use $paramName for parameters, not {paramName}.")
            if "property" in error_msg.lower():
                hints.append("Check property names against the schema.")
            
            return {
                "error": error_msg,
                "query": query,
                "hints": hints if hints else ["Try calling get_graph_schema() first."],
                "warnings": warnings if warnings else None
            }
    
    return {"error": f"Unexpected failure: {last_error}", "query": query}


# =============================================================================
# Convenience Functions
# =============================================================================

def run_read_query(query: str) -> List[Dict[str, Any]]:
    """
    Execute a read-only Cypher query (alias for run_cypher_query).
    
    This is provided for consistency with MCP's read_neo4j_cypher naming.
    
    Args:
        query: A valid Cypher query string
        
    Returns:
        Query results as a list of dictionaries
    """
    return run_cypher_query(query)


def get_node_count(label: str = None) -> Dict[str, Any]:
    """
    Get count of nodes, optionally filtered by label.
    
    Args:
        label: Optional node label to count (counts all if not provided)
        
    Returns:
        Dict with count and label
    """
    if label:
        query = f"MATCH (n:{label}) RETURN count(n) as count"
    else:
        query = "MATCH (n) RETURN count(n) as count"
    
    result = run_cypher_query(query, validate=False)
    
    if isinstance(result, list) and result:
        return {
            "label": label or "all nodes",
            "count": result[0].get("count", 0)
        }
    return result


# =============================================================================
# Export tools list
# =============================================================================

CYPHER_TOOLS = [
    get_graph_schema,        # MCP-style structured schema
    get_graph_schema_text,   # Human-readable schema text
    run_cypher_query,        # Execute any Cypher with validation
    run_read_query,          # Alias for MCP compatibility
    get_node_count,          # Quick node counting
]
