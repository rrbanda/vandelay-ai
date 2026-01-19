"""
FSI Knowledge Graph Loader.

This module provides functions to load extracted FSI entities into Neo4j.

All configuration comes from config.yaml - no hardcoding.

Based on patterns from:
- tmp/load_employee_graph.py
- Essential GraphRAG, Chapter 7

Usage:
    from data_ingestion.loaders import FSIGraphLoader
    
    loader = FSIGraphLoader()
    loader.load_products(products_data)
    loader.load_regulations(regulations_data)
    loader.load_risks(risks_data)
    loader.print_summary()
"""

import os
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, RoutingControl

from data_ingestion.config_loader import get_neo4j_config, get_loading_config
from .schema import create_all_schema, clear_database


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
# FSI Graph Loader
# =============================================================================

class FSIGraphLoader:
    """
    Load FSI entities into Neo4j knowledge graph.
    
    Handles products, regulations, and risk-related entities.
    All configuration comes from config.yaml.
    """
    
    def __init__(self, driver=None, bank_name: str = None):
        """
        Initialize the loader.
        
        Args:
            driver: Neo4j driver (creates one if not provided)
            bank_name: Name of the bank (loaded from config.yaml if not provided)
        """
        # Load bank name from config if not provided
        if bank_name is None:
            loading_config = get_loading_config()
            bank_name = loading_config.get('bank_name', 'Vandelay Financial Corporation')
        
        self.driver = driver or get_driver()
        self.bank_name = bank_name
        self.bank_id = bank_name.lower().replace(" ", "_")
        
        self._stats = {
            'products': 0,
            'fees': 0,
            'features': 0,
            'rewards': 0,
            'requirements': 0,
            'regulations': 0,
            'regulatory_requirements': 0,
            'risk_indicators': 0,
            'penalties': 0,
            'risks': 0,
            'portfolios': 0,
            'counterparties': 0,
            'risk_factors': 0,
            'mitigation_strategies': 0,
            'documents': 0,
        }
    
    def close(self):
        """Close the Neo4j driver."""
        if self.driver:
            self.driver.close()
    
    def initialize_schema(self, clear_first: bool = False, verbose: bool = True):
        """
        Initialize the database schema.
        
        Args:
            clear_first: Whether to clear existing data first
            verbose: Whether to print progress
        """
        if clear_first:
            clear_database(self.driver, verbose)
        create_all_schema(self.driver, verbose)
        
        # Create the Bank node
        self._ensure_bank()
    
    def _ensure_bank(self):
        """Ensure the Bank node exists."""
        self.driver.execute_query(
            """
            MERGE (b:Bank {id: $id})
            SET b.name = $name
            """,
            id=self.bank_id,
            name=self.bank_name,
            routing_=RoutingControl.WRITE
        )
    
    def _ensure_document(self, doc_name: str) -> str:
        """
        Ensure a Document node exists and return its ID.
        
        Args:
            doc_name: Name of the source document
            
        Returns:
            Document ID
        """
        doc_id = doc_name.lower().replace(" ", "_").replace(".", "_")
        
        self.driver.execute_query(
            """
            MERGE (d:Document {id: $id})
            SET d.name = $name
            """,
            id=doc_id,
            name=doc_name,
            routing_=RoutingControl.WRITE
        )
        
        self._stats['documents'] += 1
        return doc_id
    
    # =========================================================================
    # Product Loading
    # =========================================================================
    
    def load_product(self, product: Dict[str, Any], verbose: bool = False):
        """
        Load a single product and its related entities.
        
        Args:
            product: Product dict from extraction
            verbose: Whether to print progress
        """
        product_id = product.get('id', '')
        product_name = product.get('name', 'Unknown')
        source_doc = product.get('source_document', 'unknown')
        
        if verbose:
            print(f"  Loading product: {product_name}")
        
        # Ensure document exists
        doc_id = self._ensure_document(source_doc)
        
        # Create Product node
        self.driver.execute_query(
            """
            MERGE (p:Product {id: $id})
            SET p.name = $name,
                p.category = $category,
                p.subcategory = $subcategory,
                p.description = $description,
                p.interest_rate_apy = $interest_rate_apy,
                p.interest_rate_apr = $interest_rate_apr,
                p.interest_rate_range = $interest_rate_range,
                p.minimum_balance = $minimum_balance,
                p.minimum_opening_deposit = $minimum_opening_deposit,
                p.annual_fee = $annual_fee,
                p.term_months = $term_months,
                p.loan_amount_min = $loan_amount_min,
                p.loan_amount_max = $loan_amount_max,
                p.credit_limit_min = $credit_limit_min,
                p.credit_limit_max = $credit_limit_max,
                p.is_fdic_insured = $is_fdic_insured,
                p.fdic_coverage = $fdic_coverage,
                p.best_for = $best_for
            """,
            id=product_id,
            name=product_name,
            category=product.get('category'),
            subcategory=product.get('subcategory'),
            description=product.get('description'),
            interest_rate_apy=product.get('interest_rate_apy'),
            interest_rate_apr=product.get('interest_rate_apr'),
            interest_rate_range=product.get('interest_rate_range'),
            minimum_balance=product.get('minimum_balance'),
            minimum_opening_deposit=product.get('minimum_opening_deposit'),
            annual_fee=product.get('annual_fee'),
            term_months=product.get('term_months'),
            loan_amount_min=product.get('loan_amount_min'),
            loan_amount_max=product.get('loan_amount_max'),
            credit_limit_min=product.get('credit_limit_min'),
            credit_limit_max=product.get('credit_limit_max'),
            is_fdic_insured=product.get('is_fdic_insured'),
            fdic_coverage=product.get('fdic_coverage'),
            best_for=product.get('best_for'),
            routing_=RoutingControl.WRITE
        )
        self._stats['products'] += 1
        
        # Link Product to Bank
        self.driver.execute_query(
            """
            MATCH (b:Bank {id: $bank_id})
            MATCH (p:Product {id: $product_id})
            MERGE (b)-[:OFFERS]->(p)
            """,
            bank_id=self.bank_id,
            product_id=product_id,
            routing_=RoutingControl.WRITE
        )
        
        # Link Product to Document
        self.driver.execute_query(
            """
            MATCH (p:Product {id: $product_id})
            MATCH (d:Document {id: $doc_id})
            MERGE (p)-[:EXTRACTED_FROM]->(d)
            """,
            product_id=product_id,
            doc_id=doc_id,
            routing_=RoutingControl.WRITE
        )
        
        # Load Fees
        for fee in product.get('fees', []):
            self._load_fee(product_id, fee)
        
        # Load Features
        for feature in product.get('features', []):
            self._load_feature(product_id, feature)
        
        # Load Rewards
        for reward in product.get('rewards', []):
            self._load_reward(product_id, reward)
        
        # Load Requirements
        for req in product.get('requirements', []):
            self._load_product_requirement(product_id, req)
    
    def _load_fee(self, product_id: str, fee: Dict[str, Any]):
        """Load a fee and link it to a product."""
        fee_id = fee.get('id', f"{product_id}_fee_{fee.get('type', 'unknown')}")
        
        self.driver.execute_query(
            """
            MERGE (f:Fee {id: $id})
            SET f.name = $name,
                f.type = $type,
                f.amount = $amount,
                f.is_waivable = $is_waivable,
                f.waiver_condition = $waiver_condition
            WITH f
            MATCH (p:Product {id: $product_id})
            MERGE (p)-[:HAS_FEE]->(f)
            """,
            id=fee_id,
            name=fee.get('name') or fee.get('type', 'Unknown Fee'),
            type=fee.get('type'),
            amount=fee.get('amount'),
            is_waivable=fee.get('is_waivable', False),
            waiver_condition=fee.get('waiver_condition'),
            product_id=product_id,
            routing_=RoutingControl.WRITE
        )
        self._stats['fees'] += 1
    
    def _load_feature(self, product_id: str, feature: Dict[str, Any]):
        """Load a feature and link it to a product."""
        feature_id = feature.get('id', f"{product_id}_feat_{hash(feature.get('name', ''))}")
        
        self.driver.execute_query(
            """
            MERGE (f:Feature {id: $id})
            SET f.name = $name,
                f.description = $description,
                f.is_highlighted = $is_highlighted
            WITH f
            MATCH (p:Product {id: $product_id})
            MERGE (p)-[:HAS_FEATURE]->(f)
            """,
            id=feature_id,
            name=feature.get('name', 'Unknown Feature'),
            description=feature.get('description'),
            is_highlighted=feature.get('is_highlighted', False),
            product_id=product_id,
            routing_=RoutingControl.WRITE
        )
        self._stats['features'] += 1
    
    def _load_reward(self, product_id: str, reward: Dict[str, Any]):
        """Load a reward and link it to a product."""
        reward_id = reward.get('id', f"{product_id}_reward_{hash(reward.get('category', ''))}")
        
        self.driver.execute_query(
            """
            MERGE (r:Reward {id: $id})
            SET r.name = $name,
                r.category = $category,
                r.rate = $rate,
                r.rate_type = $rate_type,
                r.description = $description
            WITH r
            MATCH (p:Product {id: $product_id})
            MERGE (p)-[:HAS_REWARD]->(r)
            """,
            id=reward_id,
            name=reward.get('name') or reward.get('category', 'Unknown Reward'),
            category=reward.get('category'),
            rate=reward.get('rate'),
            rate_type=reward.get('rate_type'),
            description=reward.get('description'),
            product_id=product_id,
            routing_=RoutingControl.WRITE
        )
        self._stats['rewards'] += 1
    
    def _load_product_requirement(self, product_id: str, req: Dict[str, Any]):
        """Load a product requirement and link it to a product."""
        req_id = req.get('id', f"{product_id}_req_{hash(req.get('requirement_type', ''))}")
        
        self.driver.execute_query(
            """
            MERGE (r:Requirement {id: $id})
            SET r.name = $name,
                r.type = $type,
                r.value = $value,
                r.description = $description
            WITH r
            MATCH (p:Product {id: $product_id})
            MERGE (p)-[:REQUIRES]->(r)
            """,
            id=req_id,
            name=req.get('name') or req.get('requirement_type', 'Unknown'),
            type=req.get('requirement_type'),
            value=req.get('value'),
            description=req.get('description'),
            product_id=product_id,
            routing_=RoutingControl.WRITE
        )
        self._stats['requirements'] += 1
    
    def load_products(self, products: List[Dict[str, Any]], verbose: bool = True):
        """
        Load multiple products.
        
        Args:
            products: List of product dicts
            verbose: Whether to print progress
        """
        if verbose:
            print(f"Loading {len(products)} products...")
        
        for product in products:
            self.load_product(product, verbose=False)
        
        if verbose:
            print(f"  [ok] Loaded {self._stats['products']} products")
            print(f"  [ok] Loaded {self._stats['fees']} fees")
            print(f"  [ok] Loaded {self._stats['features']} features")
            print(f"  [ok] Loaded {self._stats['rewards']} rewards")
            print(f"  [ok] Loaded {self._stats['requirements']} requirements")
    
    # =========================================================================
    # Regulation Loading
    # =========================================================================
    
    def load_regulation(self, regulation: Dict[str, Any], verbose: bool = False):
        """
        Load a single regulation and its related entities.
        
        Args:
            regulation: Regulation dict from extraction
            verbose: Whether to print progress
        """
        reg_id = regulation.get('id', '')
        reg_name = regulation.get('name', 'Unknown')
        source_doc = regulation.get('source_document', 'unknown')
        
        if verbose:
            print(f"  Loading regulation: {reg_name}")
        
        # Ensure document exists
        doc_id = self._ensure_document(source_doc)
        
        # Create Regulation node
        self.driver.execute_query(
            """
            MERGE (r:Regulation {id: $id})
            SET r.name = $name,
                r.full_name = $full_name,
                r.type = $type,
                r.framework = $framework,
                r.jurisdiction = $jurisdiction,
                r.description = $description,
                r.effective_date = $effective_date,
                r.supersedes = $supersedes,
                r.key_compliance_areas = $key_compliance_areas
            """,
            id=reg_id,
            name=reg_name,
            full_name=regulation.get('full_name'),
            type=regulation.get('regulation_type'),
            framework=regulation.get('framework'),
            jurisdiction=regulation.get('jurisdiction'),
            description=regulation.get('description'),
            effective_date=str(regulation.get('effective_date')) if regulation.get('effective_date') else None,
            supersedes=regulation.get('supersedes'),
            key_compliance_areas=regulation.get('key_compliance_areas'),
            routing_=RoutingControl.WRITE
        )
        self._stats['regulations'] += 1
        
        # Link Regulation to Bank (compliance)
        self.driver.execute_query(
            """
            MATCH (b:Bank {id: $bank_id})
            MATCH (r:Regulation {id: $reg_id})
            MERGE (b)-[:COMPLIES_WITH]->(r)
            """,
            bank_id=self.bank_id,
            reg_id=reg_id,
            routing_=RoutingControl.WRITE
        )
        
        # Link Regulation to Document
        self.driver.execute_query(
            """
            MATCH (r:Regulation {id: $reg_id})
            MATCH (d:Document {id: $doc_id})
            MERGE (r)-[:EXTRACTED_FROM]->(d)
            """,
            reg_id=reg_id,
            doc_id=doc_id,
            routing_=RoutingControl.WRITE
        )
        
        # Load Requirements
        for req in regulation.get('requirements', []):
            self._load_regulatory_requirement(reg_id, req)
        
        # Load Risk Indicators
        for indicator in regulation.get('risk_indicators', []):
            self._load_risk_indicator(reg_id, indicator)
        
        # Load Penalties
        for penalty in regulation.get('penalties', []):
            self._load_penalty(reg_id, penalty)
    
    def _load_regulatory_requirement(self, reg_id: str, req: Dict[str, Any]):
        """Load a regulatory requirement and link it to a regulation."""
        req_id = req.get('id', f"{reg_id}_req_{hash(req.get('name', ''))}")
        
        self.driver.execute_query(
            """
            MERGE (rr:RegulatoryRequirement {id: $id})
            SET rr.name = $name,
                rr.category = $category,
                rr.description = $description,
                rr.threshold_value = $threshold_value,
                rr.threshold_type = $threshold_type,
                rr.applies_to = $applies_to
            WITH rr
            MATCH (r:Regulation {id: $reg_id})
            MERGE (r)-[:HAS_REQUIREMENT]->(rr)
            """,
            id=req_id,
            name=req.get('name', 'Unknown Requirement'),
            category=req.get('category'),
            description=req.get('description'),
            threshold_value=req.get('threshold_value'),
            threshold_type=req.get('threshold_type'),
            applies_to=req.get('applies_to'),
            reg_id=reg_id,
            routing_=RoutingControl.WRITE
        )
        self._stats['regulatory_requirements'] += 1
    
    def _load_risk_indicator(self, reg_id: str, indicator: Dict[str, Any]):
        """Load a risk indicator and link it to a regulation."""
        ind_id = indicator.get('id', f"{reg_id}_ind_{hash(indicator.get('name', ''))}")
        
        self.driver.execute_query(
            """
            MERGE (ri:RiskIndicator {id: $id})
            SET ri.name = $name,
                ri.description = $description,
                ri.threshold = $threshold,
                ri.risk_level = $risk_level
            WITH ri
            MATCH (r:Regulation {id: $reg_id})
            MERGE (r)-[:INDICATES_RISK]->(ri)
            """,
            id=ind_id,
            name=indicator.get('name', 'Unknown Indicator'),
            description=indicator.get('description'),
            threshold=indicator.get('threshold'),
            risk_level=indicator.get('risk_level'),
            reg_id=reg_id,
            routing_=RoutingControl.WRITE
        )
        self._stats['risk_indicators'] += 1
    
    def _load_penalty(self, reg_id: str, penalty: Dict[str, Any]):
        """Load a penalty and link it to a regulation."""
        penalty_id = penalty.get('id', f"{reg_id}_penalty_{hash(penalty.get('penalty_type', ''))}")
        
        self.driver.execute_query(
            """
            MERGE (pn:Penalty {id: $id})
            SET pn.name = $name,
                pn.type = $type,
                pn.description = $description,
                pn.amount = $amount,
                pn.severity = $severity
            WITH pn
            MATCH (r:Regulation {id: $reg_id})
            MERGE (r)-[:HAS_PENALTY]->(pn)
            """,
            id=penalty_id,
            name=penalty.get('name') or penalty.get('penalty_type', 'Unknown'),
            type=penalty.get('penalty_type'),
            description=penalty.get('description'),
            amount=penalty.get('amount'),
            severity=penalty.get('severity'),
            reg_id=reg_id,
            routing_=RoutingControl.WRITE
        )
        self._stats['penalties'] += 1
    
    def load_regulations(self, regulations: List[Dict[str, Any]], verbose: bool = True):
        """
        Load multiple regulations.
        
        Args:
            regulations: List of regulation dicts
            verbose: Whether to print progress
        """
        if verbose:
            print(f"Loading {len(regulations)} regulations...")
        
        for reg in regulations:
            self.load_regulation(reg, verbose=False)
        
        if verbose:
            print(f"  [ok] Loaded {self._stats['regulations']} regulations")
            print(f"  [ok] Loaded {self._stats['regulatory_requirements']} requirements")
            print(f"  [ok] Loaded {self._stats['risk_indicators']} risk indicators")
            print(f"  [ok] Loaded {self._stats['penalties']} penalties")
    
    # =========================================================================
    # Risk Entity Loading
    # =========================================================================
    
    def load_risk(self, risk: Dict[str, Any], verbose: bool = False):
        """Load a risk category."""
        risk_id = risk.get('id', '')
        risk_name = risk.get('name', 'Unknown')
        source_doc = risk.get('source_document', 'unknown')
        
        if verbose:
            print(f"  Loading risk: {risk_name}")
        
        doc_id = self._ensure_document(source_doc)
        
        self.driver.execute_query(
            """
            MERGE (r:Risk {id: $id})
            SET r.name = $name,
                r.category = $category,
                r.description = $description,
                r.key_metrics = $key_metrics,
                r.risk_limits = $risk_limits
            """,
            id=risk_id,
            name=risk_name,
            category=risk.get('category'),
            description=risk.get('description'),
            key_metrics=risk.get('key_metrics'),
            risk_limits=risk.get('risk_limits'),
            routing_=RoutingControl.WRITE
        )
        self._stats['risks'] += 1
        
        # Link to document
        self.driver.execute_query(
            """
            MATCH (r:Risk {id: $risk_id})
            MATCH (d:Document {id: $doc_id})
            MERGE (r)-[:EXTRACTED_FROM]->(d)
            """,
            risk_id=risk_id,
            doc_id=doc_id,
            routing_=RoutingControl.WRITE
        )
    
    def load_portfolio(self, portfolio: Dict[str, Any], verbose: bool = False):
        """Load a portfolio and its related entities."""
        port_id = portfolio.get('id', '')
        port_name = portfolio.get('name', 'Unknown')
        source_doc = portfolio.get('source_document', 'unknown')
        
        if verbose:
            print(f"  Loading portfolio: {port_name}")
        
        doc_id = self._ensure_document(source_doc)
        
        # Handle nested risk_score
        risk_score = portfolio.get('risk_score', {})
        risk_score_value = risk_score.get('score') if isinstance(risk_score, dict) else None
        risk_score_rating = risk_score.get('rating') if isinstance(risk_score, dict) else None
        
        self.driver.execute_query(
            """
            MERGE (p:Portfolio {id: $id})
            SET p.name = $name,
                p.type = $type,
                p.asset_class = $asset_class,
                p.total_value = $total_value,
                p.current_exposure = $current_exposure,
                p.primary_risk = $primary_risk,
                p.risk_score = $risk_score,
                p.risk_rating = $risk_rating,
                p.owner = $owner
            """,
            id=port_id,
            name=port_name,
            type=portfolio.get('portfolio_type'),
            asset_class=portfolio.get('asset_class'),
            total_value=portfolio.get('total_value'),
            current_exposure=portfolio.get('current_exposure'),
            primary_risk=portfolio.get('primary_risk'),
            risk_score=risk_score_value,
            risk_rating=risk_score_rating,
            owner=portfolio.get('owner'),
            routing_=RoutingControl.WRITE
        )
        self._stats['portfolios'] += 1
        
        # Link Portfolio to Bank
        self.driver.execute_query(
            """
            MATCH (b:Bank {id: $bank_id})
            MATCH (p:Portfolio {id: $port_id})
            MERGE (b)-[:OWNS]->(p)
            """,
            bank_id=self.bank_id,
            port_id=port_id,
            routing_=RoutingControl.WRITE
        )
        
        # Link to document
        self.driver.execute_query(
            """
            MATCH (p:Portfolio {id: $port_id})
            MATCH (d:Document {id: $doc_id})
            MERGE (p)-[:EXTRACTED_FROM]->(d)
            """,
            port_id=port_id,
            doc_id=doc_id,
            routing_=RoutingControl.WRITE
        )
        
        # Load risk factors
        for factor in portfolio.get('risk_factors', []):
            self._load_risk_factor(port_id, factor)
        
        # Load mitigation strategies
        for strategy in portfolio.get('mitigation_strategies', []):
            self._load_mitigation_strategy(port_id, strategy)
    
    def _load_risk_factor(self, port_id: str, factor: Dict[str, Any]):
        """Load a risk factor and link it to a portfolio."""
        factor_id = factor.get('id', f"{port_id}_factor_{hash(factor.get('name', ''))}")
        
        self.driver.execute_query(
            """
            MERGE (rf:RiskFactor {id: $id})
            SET rf.name = $name,
                rf.description = $description,
                rf.severity = $severity
            WITH rf
            MATCH (p:Portfolio {id: $port_id})
            MERGE (p)-[:HAS_RISK_FACTOR]->(rf)
            """,
            id=factor_id,
            name=factor.get('name', 'Unknown Factor'),
            description=factor.get('description'),
            severity=factor.get('severity'),
            port_id=port_id,
            routing_=RoutingControl.WRITE
        )
        self._stats['risk_factors'] += 1
    
    def _load_mitigation_strategy(self, port_id: str, strategy: Dict[str, Any]):
        """Load a mitigation strategy and link it to a portfolio."""
        strat_id = strategy.get('id', f"{port_id}_mitig_{hash(strategy.get('name', ''))}")
        
        self.driver.execute_query(
            """
            MERGE (ms:MitigationStrategy {id: $id})
            SET ms.name = $name,
                ms.description = $description,
                ms.target_risk = $target_risk,
                ms.priority = $priority,
                ms.implementation_status = $implementation_status
            WITH ms
            MATCH (p:Portfolio {id: $port_id})
            MERGE (p)-[:MITIGATED_BY]->(ms)
            """,
            id=strat_id,
            name=strategy.get('name', 'Unknown Strategy'),
            description=strategy.get('description'),
            target_risk=strategy.get('target_risk'),
            priority=strategy.get('priority'),
            implementation_status=strategy.get('implementation_status'),
            port_id=port_id,
            routing_=RoutingControl.WRITE
        )
        self._stats['mitigation_strategies'] += 1
    
    def load_counterparty(self, counterparty: Dict[str, Any], verbose: bool = False):
        """Load a counterparty."""
        cp_id = counterparty.get('id', '')
        cp_name = counterparty.get('name', 'Unknown')
        source_doc = counterparty.get('source_document', 'unknown')
        
        if verbose:
            print(f"  Loading counterparty: {cp_name}")
        
        doc_id = self._ensure_document(source_doc)
        
        self.driver.execute_query(
            """
            MERGE (c:Counterparty {id: $id})
            SET c.name = $name,
                c.type = $type,
                c.industry = $industry,
                c.country = $country,
                c.credit_rating = $credit_rating,
                c.total_exposure = $total_exposure,
                c.risk_assessment = $risk_assessment
            """,
            id=cp_id,
            name=cp_name,
            type=counterparty.get('counterparty_type'),
            industry=counterparty.get('industry'),
            country=counterparty.get('country'),
            credit_rating=counterparty.get('credit_rating'),
            total_exposure=counterparty.get('total_exposure'),
            risk_assessment=counterparty.get('risk_assessment'),
            routing_=RoutingControl.WRITE
        )
        self._stats['counterparties'] += 1
        
        # Link to document
        self.driver.execute_query(
            """
            MATCH (c:Counterparty {id: $cp_id})
            MATCH (d:Document {id: $doc_id})
            MERGE (c)-[:EXTRACTED_FROM]->(d)
            """,
            cp_id=cp_id,
            doc_id=doc_id,
            routing_=RoutingControl.WRITE
        )
    
    def load_risks(self, risks_data: Dict[str, List[Dict[str, Any]]], verbose: bool = True):
        """
        Load all risk-related entities.
        
        Args:
            risks_data: Dict with 'risks', 'portfolios', 'counterparties' keys
            verbose: Whether to print progress
        """
        risks = risks_data.get('risks', [])
        portfolios = risks_data.get('portfolios', [])
        counterparties = risks_data.get('counterparties', [])
        
        if verbose:
            print(f"Loading risk entities...")
        
        for risk in risks:
            self.load_risk(risk, verbose=False)
        
        for portfolio in portfolios:
            self.load_portfolio(portfolio, verbose=False)
        
        for cp in counterparties:
            self.load_counterparty(cp, verbose=False)
        
        if verbose:
            print(f"  [ok] Loaded {self._stats['risks']} risk categories")
            print(f"  [ok] Loaded {self._stats['portfolios']} portfolios")
            print(f"  [ok] Loaded {self._stats['counterparties']} counterparties")
            print(f"  [ok] Loaded {self._stats['risk_factors']} risk factors")
            print(f"  [ok] Loaded {self._stats['mitigation_strategies']} mitigation strategies")
    
    # =========================================================================
    # Summary
    # =========================================================================
    
    def print_summary(self):
        """Print a summary of the loaded data."""
        print("\n" + "=" * 50)
        print("FSI Knowledge Graph Loading Summary")
        print("=" * 50)
        
        # Count nodes by label
        result = self.driver.execute_query(
            """
            MATCH (n)
            RETURN labels(n)[0] as label, count(*) as count
            ORDER BY label
            """,
            result_transformer_=lambda r: r.data()
        )
        
        print("\nNode counts:")
        for row in result:
            print(f"  {row['label']}: {row['count']}")
        
        # Count relationships
        result = self.driver.execute_query(
            """
            MATCH ()-[r]->()
            RETURN type(r) as type, count(*) as count
            ORDER BY type
            """,
            result_transformer_=lambda r: r.data()
        )
        
        print("\nRelationship counts:")
        for row in result:
            print(f"  {row['type']}: {row['count']}")
        
        # Sample products
        result = self.driver.execute_query(
            """
            MATCH (p:Product)
            RETURN p.name as name, p.category as category
            LIMIT 5
            """,
            result_transformer_=lambda r: r.data()
        )
        
        if result:
            print("\nSample products:")
            for row in result:
                print(f"  {row['name']} ({row['category']})")
    
    def get_stats(self) -> Dict[str, int]:
        """Get loading statistics."""
        return self._stats.copy()
