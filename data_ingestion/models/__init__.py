"""
FSI Entity Models
=================

Pydantic models for FSI entities extracted from documents.

Models:
    - Products: Banking products (checking, savings, loans, cards)
    - Regulations: Compliance regulations (Basel III, AML, KYC)
    - Risks: Risk management entities (portfolios, counterparties)

Usage:
    from data_ingestion.models import Product, Regulation, Risk
"""

from data_ingestion.models.base import (
    ExtractedEntity,
    SourceReference,
    RiskLevel,
    Jurisdiction,
    Currency,
    generate_id,
    normalize_name,
)
from data_ingestion.models.products import (
    Product,
    ProductExtraction,
    ProductCategory,
    ProductSubcategory,
    Fee,
    FeeType,
    Feature,
    Reward,
    SignupBonus,
    ProductRequirement,
)
from data_ingestion.models.regulations import (
    Regulation,
    RegulationExtraction,
    RegulationType,
    RegulatoryRequirement,
    RequirementCategory,
    Penalty,
    RiskIndicator,
    ComplianceStatus,
)
from data_ingestion.models.risks import (
    Risk,
    RiskExtraction,
    RiskCategory,
    RiskScore,
    Portfolio,
    Counterparty,
    RiskFactor,
    MitigationStrategy,
    AssetClass,
    CreditRating,
    CounterpartyType,
)

__all__ = [
    # Base
    "ExtractedEntity",
    "SourceReference",
    "RiskLevel",
    "Jurisdiction",
    "Currency",
    "generate_id",
    "normalize_name",
    # Products
    "Product",
    "ProductExtraction",
    "ProductCategory",
    "ProductSubcategory",
    "Fee",
    "FeeType",
    "Feature",
    "Reward",
    "SignupBonus",
    "ProductRequirement",
    # Regulations
    "Regulation",
    "RegulationExtraction",
    "RegulationType",
    "RegulatoryRequirement",
    "RequirementCategory",
    "Penalty",
    "RiskIndicator",
    "ComplianceStatus",
    # Risks
    "Risk",
    "RiskExtraction",
    "RiskCategory",
    "RiskScore",
    "Portfolio",
    "Counterparty",
    "RiskFactor",
    "MitigationStrategy",
    "AssetClass",
    "CreditRating",
    "CounterpartyType",
]
