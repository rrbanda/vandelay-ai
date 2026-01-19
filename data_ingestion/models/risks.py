"""
Risk models for FSI risk management.

This module defines Pydantic models for extracting risk-related information
from risk assessment documents, policy frameworks, and compliance reports.

Risk types covered:
- Credit Risk
- Market Risk
- Operational Risk
- Liquidity Risk

Also includes:
- Portfolio risk assessments
- Counterparty risk profiles
- Mitigation strategies

Based on:
- data_ingestion/data/fsi_documents/credit_risk_assessment.txt
- data_ingestion/data/fsi_documents/basel_iii_overview.txt
"""

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from .base import ExtractedEntity, RiskLevel, generate_id


# =============================================================================
# Risk Category Enums
# =============================================================================

class RiskCategory(str, Enum):
    """
    Categories of financial risk.
    
    Based on Basel III risk taxonomy.
    """
    CREDIT_RISK = "Credit Risk"
    MARKET_RISK = "Market Risk"
    OPERATIONAL_RISK = "Operational Risk"
    LIQUIDITY_RISK = "Liquidity Risk"
    COUNTERPARTY_RISK = "Counterparty Risk"
    INTEREST_RATE_RISK = "Interest Rate Risk"
    CURRENCY_RISK = "Currency Risk"
    CONCENTRATION_RISK = "Concentration Risk"
    REPUTATIONAL_RISK = "Reputational Risk"
    LEGAL_RISK = "Legal Risk"
    COMPLIANCE_RISK = "Compliance Risk"
    MODEL_RISK = "Model Risk"
    OTHER = "Other"


class AssetClass(str, Enum):
    """
    Asset classes for portfolio categorization.
    """
    RESIDENTIAL_MORTGAGES = "Residential Mortgages"
    COMMERCIAL_MORTGAGES = "Commercial Mortgages"
    CORPORATE_LOANS = "Corporate Loans"
    CONSUMER_LOANS = "Consumer Loans"
    DERIVATIVES = "Derivatives"
    EQUITIES = "Equities"
    FIXED_INCOME = "Fixed Income"
    COMMODITIES = "Commodities"
    FOREIGN_EXCHANGE = "Foreign Exchange"
    CASH = "Cash"
    OTHER = "Other"


class CreditRating(str, Enum):
    """
    Credit rating grades.
    
    Based on S&P/Moody's scale.
    """
    # Investment Grade
    AAA = "AAA"
    AA_PLUS = "AA+"
    AA = "AA"
    AA_MINUS = "AA-"
    A_PLUS = "A+"
    A = "A"
    A_MINUS = "A-"
    BBB_PLUS = "BBB+"
    BBB = "BBB"
    BBB_MINUS = "BBB-"
    
    # Non-Investment Grade (Speculative)
    BB_PLUS = "BB+"
    BB = "BB"
    BB_MINUS = "BB-"
    B_PLUS = "B+"
    B = "B"
    B_MINUS = "B-"
    
    # High Risk
    CCC = "CCC"
    CC = "CC"
    C = "C"
    D = "D"  # Default
    
    # Not Rated
    NR = "Not Rated"


class CounterpartyType(str, Enum):
    """
    Types of counterparties.
    """
    CORPORATE = "Corporate"
    FINANCIAL_INSTITUTION = "Financial Institution"
    HEDGE_FUND = "Hedge Fund"
    SOVEREIGN = "Sovereign"
    MUNICIPAL = "Municipal"
    RETAIL = "Retail"
    SPV = "Special Purpose Vehicle"
    CCP = "Central Counterparty"
    OTHER = "Other"


# =============================================================================
# Risk Score Model
# =============================================================================

class RiskScore(BaseModel):
    """
    A risk score for an entity (portfolio, counterparty, etc.).
    """
    score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Risk score from 0-100 (higher = more risky)"
    )
    rating: RiskLevel = Field(
        ...,
        description="Qualitative risk rating"
    )
    methodology: Optional[str] = Field(
        None,
        description="Methodology used to calculate the score"
    )
    as_of_date: Optional[date] = Field(
        None,
        description="Date when the score was calculated"
    )
    
    @classmethod
    def from_score(cls, score: int, as_of_date: date = None) -> "RiskScore":
        """Create RiskScore from numeric score, auto-assigning rating."""
        if score <= 25:
            rating = RiskLevel.LOW
        elif score <= 50:
            rating = RiskLevel.MEDIUM
        elif score <= 75:
            rating = RiskLevel.HIGH
        else:
            rating = RiskLevel.CRITICAL
        return cls(score=score, rating=rating, as_of_date=as_of_date)


# =============================================================================
# Mitigation Strategy Model
# =============================================================================

class MitigationStrategy(BaseModel):
    """
    A strategy to mitigate identified risks.
    """
    name: str = Field(
        ...,
        description="Name of the mitigation strategy"
    )
    description: str = Field(
        ...,
        description="Detailed description of the strategy"
    )
    target_risk: RiskCategory = Field(
        ...,
        description="The type of risk this strategy mitigates"
    )
    priority: str = Field(
        default="Medium",
        description="Priority level: 'Low', 'Medium', 'High', 'Critical'"
    )
    implementation_status: Optional[str] = Field(
        None,
        description="Status: 'Planned', 'In Progress', 'Implemented', 'Under Review'"
    )
    expected_impact: Optional[str] = Field(
        None,
        description="Expected impact on risk reduction"
    )


# =============================================================================
# Risk Factor Model
# =============================================================================

class RiskFactor(BaseModel):
    """
    A specific factor contributing to risk.
    """
    name: str = Field(
        ...,
        description="Name of the risk factor"
    )
    description: str = Field(
        ...,
        description="Description of how this factor contributes to risk"
    )
    severity: str = Field(
        default="Medium",
        description="Severity: 'Low', 'Medium', 'High'"
    )
    is_mitigated: bool = Field(
        default=False,
        description="Whether mitigation measures are in place"
    )


# =============================================================================
# Counterparty Model
# =============================================================================

class Counterparty(ExtractedEntity):
    """
    A counterparty in financial transactions.
    
    Represents entities with which a bank has exposure through
    trades, loans, or other financial relationships.
    """
    id: str = Field(
        default="",
        description="Unique identifier (auto-generated if empty)"
    )
    name: str = Field(
        ...,
        description="Name of the counterparty"
    )
    
    # Classification
    counterparty_type: CounterpartyType = Field(
        ...,
        description="Type of counterparty"
    )
    industry: Optional[str] = Field(
        None,
        description="Industry sector"
    )
    country: Optional[str] = Field(
        None,
        description="Country of incorporation/domicile"
    )
    
    # Credit Assessment
    credit_rating: Optional[CreditRating] = Field(
        None,
        description="Credit rating"
    )
    rating_agency: Optional[str] = Field(
        None,
        description="Rating agency (e.g., 'S&P', 'Moody\\'s', 'Fitch')"
    )
    internal_rating: Optional[str] = Field(
        None,
        description="Internal credit rating if different from external"
    )
    
    # Exposure
    total_exposure: Optional[float] = Field(
        None,
        ge=0,
        description="Total exposure amount in dollars"
    )
    exposure_type: Optional[str] = Field(
        None,
        description="Type of exposure (e.g., 'Loan', 'Derivative', 'Trade')"
    )
    
    # Risk Assessment
    risk_assessment: RiskLevel = Field(
        default=RiskLevel.MEDIUM,
        description="Overall risk assessment"
    )
    risk_factors: List[RiskFactor] = Field(
        default_factory=list,
        description="Factors contributing to the risk assessment"
    )
    
    # Relationship
    relationship_description: Optional[str] = Field(
        None,
        description="Description of the business relationship"
    )
    
    def __init__(self, **data):
        """Generate ID if not provided."""
        super().__init__(**data)
        if not self.id:
            self.id = generate_id(self.name, prefix="CP-")


# =============================================================================
# Portfolio Model
# =============================================================================

class Portfolio(ExtractedEntity):
    """
    A portfolio of assets with associated risks.
    
    Represents a collection of financial assets that are
    managed together and share common risk characteristics.
    """
    id: str = Field(
        default="",
        description="Unique identifier (auto-generated if empty)"
    )
    name: str = Field(
        ...,
        description="Name of the portfolio (e.g., 'Mortgage Portfolio A')"
    )
    
    # Classification
    portfolio_type: str = Field(
        ...,
        description="Type of portfolio: 'Trading', 'Lending', 'Investment', etc."
    )
    asset_class: AssetClass = Field(
        ...,
        description="Primary asset class"
    )
    
    # Value
    total_value: Optional[float] = Field(
        None,
        ge=0,
        description="Total portfolio value in dollars"
    )
    num_assets: Optional[int] = Field(
        None,
        ge=0,
        description="Number of assets in the portfolio"
    )
    
    # Risk Assessment
    primary_risk: RiskCategory = Field(
        ...,
        description="Primary risk category affecting this portfolio"
    )
    secondary_risks: List[RiskCategory] = Field(
        default_factory=list,
        description="Secondary risk categories"
    )
    risk_score: Optional[RiskScore] = Field(
        None,
        description="Overall risk score"
    )
    current_exposure: Optional[float] = Field(
        None,
        ge=0,
        description="Current risk exposure amount in dollars"
    )
    
    # Risk Factors
    risk_factors: List[RiskFactor] = Field(
        default_factory=list,
        description="Key risk factors for this portfolio"
    )
    
    # Mitigation
    mitigation_strategies: List[MitigationStrategy] = Field(
        default_factory=list,
        description="Risk mitigation strategies"
    )
    
    # Ownership
    owner: Optional[str] = Field(
        None,
        description="Name of the owning institution"
    )
    
    # Counterparties
    key_counterparties: List[str] = Field(
        default_factory=list,
        description="Names of key counterparties"
    )
    
    def __init__(self, **data):
        """Generate ID if not provided."""
        super().__init__(**data)
        if not self.id:
            self.id = generate_id(self.name, prefix="PORT-")


# =============================================================================
# Main Risk Model
# =============================================================================

class Risk(ExtractedEntity):
    """
    A risk category with its assessment framework.
    
    This is the main entity representing different types of financial risk
    and how they are measured and managed.
    """
    id: str = Field(
        default="",
        description="Unique identifier (auto-generated if empty)"
    )
    name: str = Field(
        ...,
        description="Name of the risk (e.g., 'Credit Risk', 'Market Risk')"
    )
    
    # Classification
    category: RiskCategory = Field(
        ...,
        description="Risk category"
    )
    
    # Description
    description: str = Field(
        ...,
        description="Description of the risk and its potential impact"
    )
    
    # Assessment
    default_score: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Default/baseline risk score (0-100)"
    )
    
    # Measurement
    measurement_approach: Optional[str] = Field(
        None,
        description="How this risk is measured (e.g., 'VaR', 'Expected Loss')"
    )
    key_metrics: List[str] = Field(
        default_factory=list,
        description="Key metrics used to measure this risk"
    )
    
    # Limits
    risk_limits: List[str] = Field(
        default_factory=list,
        description="Risk limits and thresholds (e.g., 'Max 10% of Tier 1 capital')"
    )
    
    # Mitigation
    standard_mitigations: List[str] = Field(
        default_factory=list,
        description="Standard mitigation approaches for this risk type"
    )
    
    # Regulatory
    regulatory_framework: Optional[str] = Field(
        None,
        description="Regulatory framework governing this risk (e.g., 'Basel III')"
    )
    
    def __init__(self, **data):
        """Generate ID if not provided."""
        super().__init__(**data)
        if not self.id:
            self.id = generate_id(self.name, prefix="RISK-")


# =============================================================================
# Extraction Container Model
# =============================================================================

class RiskExtraction(BaseModel):
    """
    Container for extracting risk-related entities from a document.
    
    The LLM will output this structure containing all risk-related
    entities found in a single document.
    """
    risks: List[Risk] = Field(
        default_factory=list,
        description="Risk categories extracted from the document"
    )
    portfolios: List[Portfolio] = Field(
        default_factory=list,
        description="Portfolios with risk assessments"
    )
    counterparties: List[Counterparty] = Field(
        default_factory=list,
        description="Counterparties with risk profiles"
    )
    mitigation_strategies: List[MitigationStrategy] = Field(
        default_factory=list,
        description="Risk mitigation strategies mentioned"
    )
    document_name: str = Field(
        default="unknown",
        description="Name of the source document"
    )
    document_type: str = Field(
        default="Risk Assessment",
        description="Type of document"
    )
    extraction_notes: Optional[str] = Field(
        None,
        description="Any notes about the extraction"
    )
