"""
Graph Query Tools - FSI Knowledge Graph
=========================================

Tools for structured queries on the FSI knowledge graph.
Works with entities extracted from banking documents:
- Products (checking, savings, loans, credit cards)
- Regulations (Basel III, AML, KYC)
- Risk entities (portfolios, counterparties, risk factors)

Graph Schema:
- Bank -[:OFFERS]-> Product
- Bank -[:COMPLIES_WITH]-> Regulation
- Bank -[:OWNS]-> Portfolio
- Product -[:HAS_FEE]-> Fee
- Product -[:HAS_FEATURE]-> Feature
- Product -[:HAS_REWARD]-> Reward
- Product -[:REQUIRES]-> Requirement
- Regulation -[:HAS_REQUIREMENT]-> RegulatoryRequirement
- Regulation -[:INDICATES_RISK]-> RiskIndicator
- Regulation -[:HAS_PENALTY]-> Penalty
- Portfolio -[:HAS_RISK_FACTOR]-> RiskFactor
- Portfolio -[:MITIGATED_BY]-> MitigationStrategy
- * -[:EXTRACTED_FROM]-> Document

State Management:
- Tracks retrieval history in session state
- Supports ToolContext for state updates
"""

import json
import os
from datetime import date, datetime, time
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase

# Try to import ToolContext for state tracking (optional)
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
        password = os.environ.get('NEO4J_PASSWORD', '')
        _neo4j_driver = GraphDatabase.driver(uri, auth=(username, password))
    return _neo4j_driver


def _serialize_neo4j_value(value: Any) -> Any:
    """
    Convert Neo4j types to JSON-serializable Python types.
    
    Handles neo4j.time.Date, neo4j.time.DateTime, etc.
    """
    if value is None:
        return None
    
    # Handle Neo4j temporal types
    type_name = type(value).__name__
    if type_name in ('Date', 'DateTime', 'Time', 'Duration'):
        # Convert to ISO format string
        return str(value)
    
    # Handle Python datetime types
    if isinstance(value, (date, datetime, time)):
        return value.isoformat()
    
    # Handle lists
    if isinstance(value, list):
        return [_serialize_neo4j_value(item) for item in value]
    
    # Handle dicts
    if isinstance(value, dict):
        return {k: _serialize_neo4j_value(v) for k, v in value.items()}
    
    return value


def _serialize_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Serialize all Neo4j results to JSON-compatible format."""
    if not results:
        return results
    return [_serialize_neo4j_value(record) for record in results]


def _safe_execute_query(query: str, **params) -> tuple:
    """
    Execute a Neo4j query with consistent error handling.
    
    Args:
        query: Cypher query string
        **params: Query parameters
        
    Returns:
        Tuple of (results, error_dict) where error_dict is None on success
    """
    try:
        driver = _get_driver()
        result = driver.execute_query(
            query,
            result_transformer_=lambda r: r.data(),
            **params
        )
        # Serialize Neo4j types to JSON-compatible format
        return _serialize_results(result), None
    except Exception as e:
        error_type = type(e).__name__
        return None, {
            "error": str(e),
            "error_type": error_type,
            "message": f"Database query failed: {error_type}"
        }


def _track_graph_query(
    context: Optional[ToolContext],
    tool_name: str,
    query_params: Dict[str, Any],
    results: Any,
    has_error: bool = False,
) -> None:
    """
    Track a graph query in session state.
    
    Updates temp:retrieval_history with the query details.
    """
    if context is None or not HAS_TOOL_CONTEXT:
        return
    
    # Get current history
    history_json = context.state.get("temp:retrieval_history", "[]")
    try:
        history = json.loads(history_json)
    except (json.JSONDecodeError, TypeError):
        history = []
    
    # Add new entry
    result_count = len(results) if isinstance(results, list) else 1
    entry = {
        "tool": tool_name,
        "params": query_params,
        "result_count": result_count,
        "has_error": has_error,
    }
    history.append(entry)
    
    # Update state
    context.state["temp:retrieval_history"] = json.dumps(history)


# =============================================================================
# Product Tools
# =============================================================================

def get_all_products() -> List[Dict[str, Any]]:
    """
    Get all financial products offered by the bank.
    
    Returns:
        List of products with id, name, category, and description
    """
    result, error = _safe_execute_query(
        '''
        MATCH (p:Product)
        OPTIONAL MATCH (b:Bank)-[:OFFERS]->(p)
        RETURN p.id as id, p.name as name, p.category as category,
               p.subcategory as subcategory, p.description as description,
               p.interest_rate_apy as apy, p.interest_rate_apr as apr,
               p.minimum_balance as min_balance, p.annual_fee as annual_fee,
               p.best_for as best_for, b.name as bank
        ORDER BY p.category, p.name
        '''
    )
    
    if error:
        return [error]
    return result if result else [{"message": "No products found"}]


def get_products_by_category(category: str) -> List[Dict[str, Any]]:
    """
    Get products of a specific category.
    
    Args:
        category: Category like 'Checking', 'Savings', 'Mortgage', 'Credit Card'
        
    Returns:
        List of matching products with details
    """
    result, error = _safe_execute_query(
        '''
        MATCH (p:Product)
        WHERE toLower(p.category) CONTAINS toLower($category)
           OR toLower(p.subcategory) CONTAINS toLower($category)
        RETURN p.id as id, p.name as name, p.category as category,
               p.subcategory as subcategory, p.interest_rate_apy as apy,
               p.interest_rate_apr as apr, p.minimum_balance as min_balance,
               p.best_for as best_for
        ORDER BY p.name
        ''',
        category=category
    )
    
    if error:
        return [error]
    return result if result else [{"message": f"No {category} products found"}]


def get_product_details(product_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific product including fees, features, and rewards.
    
    Args:
        product_name: Name of the product to look up
        
    Returns:
        Product details with all related entities
    """
    result, error = _safe_execute_query(
        '''
        MATCH (p:Product)
        WHERE toLower(p.name) CONTAINS toLower($name)
        OPTIONAL MATCH (p)-[:HAS_FEE]->(f:Fee)
        OPTIONAL MATCH (p)-[:HAS_FEATURE]->(feat:Feature)
        OPTIONAL MATCH (p)-[:HAS_REWARD]->(r:Reward)
        OPTIONAL MATCH (p)-[:REQUIRES]->(req:Requirement)
        OPTIONAL MATCH (p)-[:EXTRACTED_FROM]->(d:Document)
        RETURN p {
            .id, .name, .category, .subcategory, .description,
            .interest_rate_apy, .interest_rate_apr, .interest_rate_range,
            .minimum_balance, .minimum_opening_deposit, .annual_fee,
            .term_months, .loan_amount_min, .loan_amount_max,
            .credit_limit_min, .credit_limit_max, .is_fdic_insured,
            .fdic_coverage, .best_for
        } as product,
        collect(DISTINCT f {.name, .type, .amount, .is_waivable, .waiver_condition}) as fees,
        collect(DISTINCT feat {.name, .description}) as features,
        collect(DISTINCT r {.name, .category, .rate, .rate_type}) as rewards,
        collect(DISTINCT req {.name, .type, .value}) as requirements,
        collect(DISTINCT d.name) as source_documents
        ''',
        name=product_name
    )

    if error:
        return error
    if result:
        return result[0]
    return {"error": f"Product '{product_name}' not found"}


def get_product_fees(product_name: str = None) -> List[Dict[str, Any]]:
    """
    Get fees associated with products.
    
    Args:
        product_name: Optional product name to filter (get all fees if not provided)
        
    Returns:
        List of fees with product associations
    """
    if product_name:
        result, error = _safe_execute_query(
            '''
            MATCH (p:Product)-[:HAS_FEE]->(f:Fee)
            WHERE toLower(p.name) CONTAINS toLower($name)
            RETURN p.name as product, f.name as fee, f.type as fee_type,
                   f.amount as amount, f.is_waivable as waivable,
                   f.waiver_condition as waiver_condition
            ORDER BY p.name, f.type
            ''',
            name=product_name
        )
    else:
        result, error = _safe_execute_query(
            '''
            MATCH (p:Product)-[:HAS_FEE]->(f:Fee)
            RETURN p.name as product, p.category as category, f.name as fee,
                   f.type as fee_type, f.amount as amount, f.is_waivable as waivable
            ORDER BY p.category, p.name, f.type
            '''
        )
    
    if error:
        return [error]
    return result if result else [{"message": "No fees found"}]


# =============================================================================
# Regulation Tools
# =============================================================================

def get_all_regulations() -> List[Dict[str, Any]]:
    """
    Get all financial regulations the bank complies with.
    
    Returns:
        List of regulations with type, jurisdiction, and description
    """
    result, error = _safe_execute_query(
        '''
        MATCH (r:Regulation)
        OPTIONAL MATCH (b:Bank)-[:COMPLIES_WITH]->(r)
        RETURN r.id as id, r.name as name, r.full_name as full_name,
               r.type as regulation_type, r.framework as framework,
               r.jurisdiction as jurisdiction, r.description as description,
               r.effective_date as effective_date, b.name as compliant_bank
        ORDER BY r.name
        '''
    )

    if error:
        return [error]
    return result if result else [{"message": "No regulations found"}]


def get_regulation_details(regulation_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific regulation including requirements and penalties.
    
    Args:
        regulation_name: Name of the regulation (e.g., 'Basel III', 'AML')
        
    Returns:
        Regulation details with requirements, risk indicators, and penalties
    """
    result, error = _safe_execute_query(
        '''
        MATCH (r:Regulation)
        WHERE toLower(r.name) CONTAINS toLower($name)
           OR toLower(r.full_name) CONTAINS toLower($name)
        OPTIONAL MATCH (r)-[:HAS_REQUIREMENT]->(req:RegulatoryRequirement)
        OPTIONAL MATCH (r)-[:INDICATES_RISK]->(ri:RiskIndicator)
        OPTIONAL MATCH (r)-[:HAS_PENALTY]->(p:Penalty)
        OPTIONAL MATCH (r)-[:EXTRACTED_FROM]->(d:Document)
        RETURN r {
            .id, .name, .full_name, .type, .framework, .jurisdiction,
            .description, .effective_date, .supersedes, .key_compliance_areas
        } as regulation,
        collect(DISTINCT req {.name, .category, .description, .threshold_value, .threshold_type, .applies_to}) as requirements,
        collect(DISTINCT ri {.name, .description, .threshold, .risk_level}) as risk_indicators,
        collect(DISTINCT p {.name, .type, .description, .amount, .severity}) as penalties,
        collect(DISTINCT d.name) as source_documents
        ''',
        name=regulation_name
    )

    if error:
        return error
    if result:
        return result[0]
    return {"error": f"Regulation '{regulation_name}' not found"}


def get_regulatory_requirements(regulation_name: str = None) -> List[Dict[str, Any]]:
    """
    Get regulatory requirements, optionally filtered by regulation.
    
    Args:
        regulation_name: Optional regulation name to filter
        
    Returns:
        List of regulatory requirements with thresholds
    """
    if regulation_name:
        result, error = _safe_execute_query(
            '''
            MATCH (r:Regulation)-[:HAS_REQUIREMENT]->(req:RegulatoryRequirement)
            WHERE toLower(r.name) CONTAINS toLower($name)
            RETURN r.name as regulation, req.name as requirement,
                   req.category as category, req.description as description,
                   req.threshold_value as threshold, req.threshold_type as threshold_type,
                   req.applies_to as applies_to
            ORDER BY req.category, req.name
            ''',
            name=regulation_name
        )
    else:
        result, error = _safe_execute_query(
            '''
            MATCH (r:Regulation)-[:HAS_REQUIREMENT]->(req:RegulatoryRequirement)
            RETURN r.name as regulation, req.name as requirement,
                   req.category as category, req.threshold_value as threshold,
                   req.threshold_type as threshold_type
            ORDER BY r.name, req.category
            '''
        )
    
    if error:
        return [error]
    return result if result else [{"message": "No regulatory requirements found"}]


def get_risk_indicators() -> List[Dict[str, Any]]:
    """
    Get all AML/KYC risk indicators defined in regulations.
    
    Returns:
        List of risk indicators with thresholds and severity
    """
    result, error = _safe_execute_query(
        '''
        MATCH (r:Regulation)-[:INDICATES_RISK]->(ri:RiskIndicator)
        RETURN r.name as regulation, ri.name as indicator,
               ri.description as description, ri.threshold as threshold,
               ri.risk_level as risk_level
        ORDER BY ri.risk_level DESC, ri.name
        '''
    )

    if error:
        return [error]
    return result if result else [{"message": "No risk indicators found"}]


def get_compliance_penalties() -> List[Dict[str, Any]]:
    """
    Get all penalties for regulatory non-compliance.
    
    Returns:
        List of penalties with severity and amounts
    """
    result, error = _safe_execute_query(
        '''
        MATCH (r:Regulation)-[:HAS_PENALTY]->(p:Penalty)
        RETURN r.name as regulation, p.name as penalty, p.type as penalty_type,
               p.description as description, p.amount as amount, p.severity as severity
        ORDER BY p.severity DESC, r.name
        '''
    )

    if error:
        return [error]
    return result if result else [{"message": "No penalties found"}]


# =============================================================================
# Risk & Portfolio Tools
# =============================================================================

def get_all_portfolios() -> List[Dict[str, Any]]:
    """
    Get all financial portfolios managed by the bank.
    
    Returns:
        List of portfolios with risk scores and values
    """
    result, error = _safe_execute_query(
        '''
        MATCH (p:Portfolio)
        OPTIONAL MATCH (b:Bank)-[:OWNS]->(p)
        RETURN p.id as id, p.name as name, p.type as portfolio_type,
               p.asset_class as asset_class, p.total_value as total_value,
               p.current_exposure as exposure, p.risk_score as risk_score,
               p.risk_rating as risk_rating, b.name as owner
        ORDER BY p.risk_score DESC
        '''
    )

    if error:
        return [error]
    return result if result else [{"message": "No portfolios found"}]


def get_portfolio_details(portfolio_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a portfolio including risk factors and mitigation strategies.
    
    Args:
        portfolio_name: Name of the portfolio
        
    Returns:
        Portfolio details with risk factors and mitigations
    """
    result, error = _safe_execute_query(
        '''
        MATCH (p:Portfolio)
        WHERE toLower(p.name) CONTAINS toLower($name)
        OPTIONAL MATCH (p)-[:HAS_RISK_FACTOR]->(rf:RiskFactor)
        OPTIONAL MATCH (p)-[:MITIGATED_BY]->(ms:MitigationStrategy)
        OPTIONAL MATCH (p)-[:EXTRACTED_FROM]->(d:Document)
        RETURN p {
            .id, .name, .type, .asset_class, .total_value, .current_exposure,
            .primary_risk, .risk_score, .risk_rating, .owner
        } as portfolio,
        collect(DISTINCT rf {.name, .description, .severity}) as risk_factors,
        collect(DISTINCT ms {.name, .description, .target_risk, .priority, .implementation_status}) as mitigation_strategies,
        collect(DISTINCT d.name) as source_documents
        ''',
        name=portfolio_name
    )

    if error:
        return error
    if result:
        return result[0]
    return {"error": f"Portfolio '{portfolio_name}' not found"}


def get_high_risk_portfolios() -> List[Dict[str, Any]]:
    """
    Get portfolios with high risk scores or ratings.
    
    Returns:
        List of high-risk portfolios with their risk factors
    """
    result, error = _safe_execute_query(
        '''
        MATCH (p:Portfolio)
        WHERE p.risk_rating = 'High' OR p.risk_rating = 'Critical' OR p.risk_score >= 60
        OPTIONAL MATCH (p)-[:HAS_RISK_FACTOR]->(rf:RiskFactor)
        RETURN p.name as portfolio, p.type as type, p.total_value as value,
               p.risk_score as score, p.risk_rating as rating,
               collect(rf.name) as risk_factors
        ORDER BY p.risk_score DESC
        '''
    )
    
    if error:
        return [error]
    return result if result else [{"message": "No high-risk portfolios found"}]


def get_all_counterparties() -> List[Dict[str, Any]]:
    """
    Get all counterparties the bank has exposure to.
    
    Returns:
        List of counterparties with credit ratings and exposure
    """
    result, error = _safe_execute_query(
        '''
        MATCH (c:Counterparty)
        RETURN c.id as id, c.name as name, c.type as counterparty_type,
               c.industry as industry, c.country as country,
               c.credit_rating as credit_rating, c.total_exposure as exposure,
               c.risk_assessment as risk_level
        ORDER BY c.total_exposure DESC
        '''
    )

    if error:
        return [error]
    return result if result else [{"message": "No counterparties found"}]


def get_all_customers() -> List[Dict[str, Any]]:
    """
    Get all customers in the system.
    
    Returns:
        List of customers with risk level and KYC status
    """
    result, error = _safe_execute_query(
        '''
        MATCH (c:Customer)
        OPTIONAL MATCH (c)-[:OWNS]->(a:Account)
        RETURN c.id as id, c.name as name, c.type as customer_type,
               c.risk_level as risk_level, c.kyc_status as kyc_status,
               collect(DISTINCT a.id) as accounts
        ORDER BY c.name
        '''
    )

    if error:
        return [error]
    return result if result else [{"message": "No customers found"}]


def get_high_risk_customers() -> List[Dict[str, Any]]:
    """
    Get customers with high risk level.
    
    SPECIALIZED RETRIEVER - optimized for high-risk customer queries.
    Use when user asks about high-risk customers or risky clients.
    
    Returns:
        List of high-risk customers with details
    """
    result, error = _safe_execute_query(
        '''
        MATCH (c:Customer)
        WHERE c.risk_level IN ['High', 'Critical', 'high', 'critical']
        OPTIONAL MATCH (c)-[:OWNS]->(a:Account)
        OPTIONAL MATCH (c)-[:HAS_TRANSACTION]->(t:Transaction)
        RETURN c.id as id, c.name as name, c.type as customer_type,
               c.risk_level as risk_level, c.kyc_status as kyc_status,
               collect(DISTINCT a.id) as accounts,
               count(DISTINCT t) as transaction_count
        ORDER BY c.risk_level DESC, c.name
        '''
    )
    
    if error:
        return [error]
    return result if result else [{"message": "No high-risk customers found"}]


def get_customer_details(customer_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a specific customer.
    
    Args:
        customer_name: Name of the customer to look up
        
    Returns:
        Customer details with accounts and transactions
    """
    result, error = _safe_execute_query(
        '''
        MATCH (c:Customer)
        WHERE toLower(c.name) CONTAINS toLower($name)
        OPTIONAL MATCH (c)-[:OWNS]->(a:Account)
        OPTIONAL MATCH (c)-[:HAS_TRANSACTION]->(t:Transaction)
        RETURN c {.id, .name, .type, .risk_level, .kyc_status} as customer,
               collect(DISTINCT a {.id, .type, .balance}) as accounts,
               collect(DISTINCT t {.id, .type, .amount, .date}) as transactions
        ''',
        name=customer_name
    )

    if error:
        return error
    if result:
        return result[0]
    return {"error": f"Customer '{customer_name}' not found"}


def get_mitigation_strategies() -> List[Dict[str, Any]]:
    """
    Get all risk mitigation strategies in place.
    
    Returns:
        List of mitigation strategies with targets and priorities
    """
    result, error = _safe_execute_query(
        '''
        MATCH (p:Portfolio)-[:MITIGATED_BY]->(ms:MitigationStrategy)
        RETURN ms.name as strategy, ms.description as description,
               ms.target_risk as target_risk, ms.priority as priority,
               ms.implementation_status as status, p.name as portfolio
        ORDER BY ms.priority, p.name
        '''
    )

    if error:
        return [error]
    return result if result else [{"message": "No mitigation strategies found"}]


# =============================================================================
# Document Provenance Tools
# =============================================================================

def get_source_documents() -> List[Dict[str, Any]]:
    """
    Get all source documents that entities were extracted from.
    
    Returns:
        List of documents with entity counts
    """
    result, error = _safe_execute_query(
        '''
        MATCH (d:Document)
        OPTIONAL MATCH (e)-[:EXTRACTED_FROM]->(d)
        RETURN d.id as id, d.name as name, count(e) as entity_count
        ORDER BY d.name
        '''
    )

    if error:
        return [error]
    return result if result else [{"message": "No documents found"}]


def get_entities_from_document(document_name: str) -> Dict[str, Any]:
    """
    Get all entities extracted from a specific document.
    
    Args:
        document_name: Name of the source document
        
    Returns:
        Dict with products, regulations, portfolios, etc. from the document
    """
    result, error = _safe_execute_query(
        '''
        MATCH (d:Document)
        WHERE toLower(d.name) CONTAINS toLower($name)
        OPTIONAL MATCH (p:Product)-[:EXTRACTED_FROM]->(d)
        OPTIONAL MATCH (r:Regulation)-[:EXTRACTED_FROM]->(d)
        OPTIONAL MATCH (port:Portfolio)-[:EXTRACTED_FROM]->(d)
        OPTIONAL MATCH (c:Counterparty)-[:EXTRACTED_FROM]->(d)
        RETURN d.name as document,
               collect(DISTINCT p.name) as products,
               collect(DISTINCT r.name) as regulations,
               collect(DISTINCT port.name) as portfolios,
               collect(DISTINCT c.name) as counterparties
        ''',
        name=document_name
    )

    if error:
        return error
    if result:
        return result[0]
    return {"error": f"Document '{document_name}' not found"}


# =============================================================================
# General Query Tools
# =============================================================================

def run_cypher_query(query: str) -> List[Dict[str, Any]]:
    """
    Execute a custom Cypher query.
    
    Args:
        query: The Cypher query to execute
        
    Returns:
        Query results as list of dictionaries
    """
    result, error = _safe_execute_query(query)
    
    if error:
        return [error]
    return result if result else [{"message": "Query returned no results"}]


def get_graph_schema() -> Dict[str, Any]:
    """
    Get the schema of the knowledge graph.
    
    Returns:
        Node labels, relationship types, and counts
    """
    # Get node labels and counts
    labels_result, labels_error = _safe_execute_query(
        '''
        MATCH (n)
        RETURN labels(n)[0] as label, count(*) as count
        ORDER BY count DESC
        '''
    )
    
    # Get relationship types
    rels_result, rels_error = _safe_execute_query(
        '''
        MATCH ()-[r]->()
        RETURN type(r) as relationship, count(*) as count
        ORDER BY count DESC
        '''
    )

    if labels_error or rels_error:
        return {"error": labels_error or rels_error}
    
    return {
        "node_labels": labels_result,
        "relationships": rels_result,
        "description": "FSI Knowledge Graph - Products, Regulations, Portfolios, Risk"
    }


# =============================================================================
# Specialized Tools (Hardcoded Cypher from config.yaml)
# =============================================================================
# These execute pre-defined Cypher templates for common patterns
# More reliable than text2cypher for frequent query types

def execute_specialized_query(tool_name: str, **params) -> List[Dict[str, Any]]:
    """
    Execute a specialized query from config.yaml.
    
    Args:
        tool_name: Name of the specialized tool
        **params: Parameters for the query
        
    Returns:
        Query results
    """
    from ...config_loader import get_specialized_tool
    
    tool_config = get_specialized_tool(tool_name)
    if not tool_config:
        return [{"error": f"Specialized tool '{tool_name}' not found in config"}]
    
    cypher = tool_config.get('cypher', '')
    if not cypher:
        return [{"error": f"No Cypher template for '{tool_name}'"}]
    
    result, error = _safe_execute_query(cypher, **params)
    
    if error:
        return [error]
    return result if result else [{"message": "Query returned no results"}]


def get_product_with_fees(product_name: str) -> Dict[str, Any]:
    """
    Get full product details including fees, features, and requirements.
    
    SPECIALIZED RETRIEVER - optimized for product detail queries.
    Use instead of get_product_details when you need fee information.
    
    Args:
        product_name: Name of the product (partial match supported)
        
    Returns:
        Product with all related entities (fees, features, rewards, requirements)
    """
    return execute_specialized_query('get_product_with_fees', product_name=product_name)


def get_high_risk_items() -> Dict[str, Any]:
    """
    Get all high-risk portfolios, counterparties, and customers in one query.
    
    SPECIALIZED RETRIEVER - optimized for risk overview.
    Use when user asks about high-risk exposures, high-risk customers, or risk summary.
    
    Returns:
        Dict with high_risk_portfolios, high_risk_counterparties, and high_risk_customers
    """
    # Query all high-risk entities directly (more reliable than config-based template)
    result, error = _safe_execute_query(
        '''
        // High-risk portfolios
        OPTIONAL MATCH (p:Portfolio)
        WHERE p.risk_rating IN ['High', 'Critical'] OR p.risk_score >= 60
        WITH collect(p {.name, .risk_score, .risk_rating}) as portfolios
        
        // High-risk counterparties
        OPTIONAL MATCH (cp:Counterparty)
        WHERE cp.risk_assessment IN ['High', 'Critical']
        WITH portfolios, collect(cp {.name, .total_exposure, .risk_assessment}) as counterparties
        
        // High-risk customers
        OPTIONAL MATCH (c:Customer)
        WHERE c.risk_level IN ['High', 'Critical', 'high', 'critical']
        RETURN portfolios, counterparties, 
               collect(c {.id, .name, .type, .risk_level, .kyc_status}) as customers
        '''
    )
    
    if error:
        return {"error": error}
    
    if result and len(result) > 0:
        data = result[0]
        return {
            "high_risk_portfolios": data.get("portfolios", []),
            "high_risk_counterparties": data.get("counterparties", []),
            "high_risk_customers": data.get("customers", [])
        }
    return {"high_risk_portfolios": [], "high_risk_counterparties": [], "high_risk_customers": []}


def get_counterparty_exposure(name: str = None) -> List[Dict[str, Any]]:
    """
    Get counterparty exposure information.
    
    SPECIALIZED RETRIEVER - optimized for counterparty queries.
    
    Args:
        name: Optional counterparty name filter
        
    Returns:
        List of counterparties with exposure details
    """
    return execute_specialized_query('get_counterparty_exposure', name=name)


def get_compliance_status() -> Dict[str, Any]:
    """
    Get bank's compliance status with all regulations.
    
    SPECIALIZED RETRIEVER - optimized for compliance overview.
    
    Returns:
        Bank compliance status with regulation counts
    """
    result = execute_specialized_query('get_compliance_status')
    if result and len(result) > 0:
        return result[0]
    return {"message": "No compliance information found"}


# Export tools list for FSI domain
GRAPH_TOOLS = [
    # Products
    get_all_products,
    get_products_by_category,
    get_product_details,
    get_product_fees,
    get_product_with_fees,  # SPECIALIZED
    
    # Regulations
    get_all_regulations,
    get_regulation_details,
    get_regulatory_requirements,
    get_risk_indicators,
    get_compliance_penalties,
    get_compliance_status,  # SPECIALIZED
    
    # Portfolios & Risk
    get_all_portfolios,
    get_portfolio_details,
    get_high_risk_portfolios,
    get_high_risk_items,  # SPECIALIZED (now includes customers)
    get_all_counterparties,
    get_counterparty_exposure,  # SPECIALIZED
    get_mitigation_strategies,
    
    # Customers
    get_all_customers,
    get_high_risk_customers,  # SPECIALIZED
    get_customer_details,
    
    # Documents
    get_source_documents,
    get_entities_from_document,
    
    # General
    run_cypher_query,
    get_graph_schema,
]
