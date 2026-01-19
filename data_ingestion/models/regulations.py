"""
Regulation models for FSI regulatory frameworks.

This module defines Pydantic models for extracting regulatory information
from compliance documents, policy guides, and regulatory frameworks.

Regulations covered:
- Basel III (capital requirements, liquidity ratios)
- AML (Anti-Money Laundering)
- KYC (Know Your Customer)
- MiFID II, Dodd-Frank, etc.

Based on:
- data_ingestion/data/fsi_documents/aml_compliance_policy.txt
- data_ingestion/data/fsi_documents/basel_iii_overview.txt
"""

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field

from .base import ExtractedEntity, Jurisdiction, generate_id


# =============================================================================
# Regulation Type Enums
# =============================================================================

class RegulationType(str, Enum):
    """
    Types of regulatory frameworks.
    
    Categorizes regulations by their primary focus area.
    """
    CAPITAL_REQUIREMENTS = "Capital Requirements"
    LIQUIDITY = "Liquidity"
    ANTI_MONEY_LAUNDERING = "Anti-Money Laundering"
    KNOW_YOUR_CUSTOMER = "Know Your Customer"
    CONSUMER_PROTECTION = "Consumer Protection"
    MARKET_CONDUCT = "Market Conduct"
    DATA_PROTECTION = "Data Protection"
    REPORTING = "Reporting"
    DERIVATIVES = "Derivatives"
    STRESS_TESTING = "Stress Testing"
    OTHER = "Other"


class RequirementCategory(str, Enum):
    """
    Categories of regulatory requirements.
    
    Groups requirements by their nature and purpose.
    """
    # Capital-related
    CAPITAL_RATIO = "Capital Ratio"
    CAPITAL_BUFFER = "Capital Buffer"
    LEVERAGE = "Leverage"
    
    # Liquidity-related
    LIQUIDITY_RATIO = "Liquidity Ratio"
    FUNDING_RATIO = "Funding Ratio"
    
    # AML/KYC-related
    CUSTOMER_DUE_DILIGENCE = "Customer Due Diligence"
    ENHANCED_DUE_DILIGENCE = "Enhanced Due Diligence"
    TRANSACTION_MONITORING = "Transaction Monitoring"
    SUSPICIOUS_ACTIVITY_REPORTING = "Suspicious Activity Reporting"
    RECORD_KEEPING = "Record Keeping"
    
    # General
    DOCUMENTATION = "Documentation"
    REPORTING = "Reporting"
    VERIFICATION = "Verification"
    AUDIT = "Audit"
    TRAINING = "Training"
    GOVERNANCE = "Governance"
    
    # Risk-related
    RISK_ASSESSMENT = "Risk Assessment"
    RISK_MANAGEMENT = "Risk Management"
    
    OTHER = "Other"


class ComplianceStatus(str, Enum):
    """
    Status of compliance with a regulation.
    """
    COMPLIANT = "Compliant"
    PARTIALLY_COMPLIANT = "Partially Compliant"
    NON_COMPLIANT = "Non-Compliant"
    UNDER_REVIEW = "Under Review"
    NOT_APPLICABLE = "Not Applicable"


# =============================================================================
# Requirement Model
# =============================================================================

class RegulatoryRequirement(BaseModel):
    """
    A specific requirement within a regulation.
    
    Examples:
    - Basel III CET1 ratio: minimum 4.5%
    - AML SAR filing: within 30 days
    - KYC verification: before account opening
    """
    id: str = Field(
        default="",
        description="Unique identifier (auto-generated if empty)"
    )
    name: str = Field(
        ...,
        description="Name of the requirement (e.g., 'CET1 Capital Ratio', 'SAR Filing')"
    )
    category: RequirementCategory = Field(
        ...,
        description="Category of the requirement"
    )
    
    # Requirement details
    description: str = Field(
        ...,
        description="Detailed description of what is required"
    )
    threshold_value: Optional[str] = Field(
        None,
        description="Numeric threshold if applicable (e.g., '4.5%', '$10,000', '30 days')"
    )
    threshold_type: Optional[str] = Field(
        None,
        description="Type of threshold: 'minimum', 'maximum', 'within', 'at_least'"
    )
    
    # Applicability
    applies_to: Optional[str] = Field(
        None,
        description="Who this requirement applies to (e.g., 'all banks', 'high-risk customers')"
    )
    exceptions: Optional[str] = Field(
        None,
        description="Any exceptions to this requirement"
    )
    
    # Frequency
    frequency: Optional[str] = Field(
        None,
        description="How often this must be performed (e.g., 'ongoing', 'quarterly', 'annually')"
    )
    
    # Related regulations
    parent_regulation: Optional[str] = Field(
        None,
        description="Name of the parent regulation (e.g., 'Basel III', 'AML')"
    )
    
    def __init__(self, **data):
        """Generate ID if not provided."""
        super().__init__(**data)
        if not self.id:
            parent = self.parent_regulation or "unknown"
            self.id = generate_id(f"{self.name}_{parent}", prefix="REQ-")


# =============================================================================
# Penalty Model
# =============================================================================

class Penalty(BaseModel):
    """
    Penalties for non-compliance with a regulation.
    """
    penalty_type: str = Field(
        ...,
        description="Type of penalty (e.g., 'Fine', 'Criminal Prosecution', 'License Revocation')"
    )
    severity: str = Field(
        default="Medium",
        description="Severity level: 'Low', 'Medium', 'High', 'Critical'"
    )
    amount: Optional[str] = Field(
        None,
        description="Penalty amount if monetary (e.g., 'up to $1 million per violation')"
    )
    description: Optional[str] = Field(
        None,
        description="Description of the penalty and when it applies"
    )


# =============================================================================
# Risk Indicator Model (for AML/KYC)
# =============================================================================

class RiskIndicator(BaseModel):
    """
    Indicators that trigger enhanced scrutiny or flagging.
    
    Used in AML/KYC for identifying suspicious activities.
    """
    name: str = Field(
        ...,
        description="Name of the risk indicator (e.g., 'Large Cash Transaction')"
    )
    description: str = Field(
        ...,
        description="Description of what constitutes this indicator"
    )
    threshold: Optional[str] = Field(
        None,
        description="Threshold that triggers this indicator (e.g., 'over $10,000')"
    )
    action_required: Optional[str] = Field(
        None,
        description="Action required when this indicator is triggered"
    )
    risk_level: str = Field(
        default="Medium",
        description="Risk level: 'Low', 'Medium', 'High'"
    )


# =============================================================================
# Main Regulation Model
# =============================================================================

class Regulation(ExtractedEntity):
    """
    A regulatory framework or compliance requirement.
    
    This is the main entity representing regulatory frameworks like
    Basel III, AML, KYC, MiFID II, Dodd-Frank, etc.
    
    Inherits from ExtractedEntity to track source document.
    """
    # Identity
    id: str = Field(
        default="",
        description="Unique identifier (auto-generated if empty)"
    )
    name: str = Field(
        ...,
        description="Name of the regulation (e.g., 'Basel III', 'AML', 'KYC')"
    )
    full_name: Optional[str] = Field(
        None,
        description="Full official name if different from common name"
    )
    
    # Classification
    regulation_type: RegulationType = Field(
        ...,
        description="Primary type/focus of the regulation"
    )
    framework: Optional[str] = Field(
        None,
        description="Parent framework if applicable (e.g., 'Basel' for Basel III)"
    )
    
    # Jurisdiction and Applicability
    jurisdiction: Jurisdiction = Field(
        default=Jurisdiction.INTERNATIONAL,
        description="Geographic jurisdiction where this regulation applies"
    )
    applies_to: Optional[str] = Field(
        None,
        description="Types of institutions this applies to (e.g., 'all banks', 'systemically important')"
    )
    
    # Description
    description: str = Field(
        ...,
        description="Description of the regulation's purpose and scope"
    )
    summary: Optional[str] = Field(
        None,
        description="Brief summary of key points"
    )
    
    # Timeline
    effective_date: Optional[date] = Field(
        None,
        description="Date when the regulation became effective"
    )
    last_updated: Optional[date] = Field(
        None,
        description="Date of last major update or amendment"
    )
    
    # Components
    requirements: List[RegulatoryRequirement] = Field(
        default_factory=list,
        description="List of specific requirements under this regulation"
    )
    penalties: List[Penalty] = Field(
        default_factory=list,
        description="Penalties for non-compliance"
    )
    risk_indicators: List[RiskIndicator] = Field(
        default_factory=list,
        description="Risk indicators (primarily for AML/KYC)"
    )
    
    # Relationships
    related_regulations: List[str] = Field(
        default_factory=list,
        description="Names of related regulations (e.g., KYC is related to AML)"
    )
    supersedes: Optional[str] = Field(
        None,
        description="Name of regulation this supersedes (e.g., Basel III supersedes Basel II)"
    )
    
    # Compliance
    key_compliance_areas: List[str] = Field(
        default_factory=list,
        description="Main areas institutions must focus on for compliance"
    )
    
    def __init__(self, **data):
        """Generate ID if not provided."""
        super().__init__(**data)
        if not self.id:
            source = self.source_document or "unknown"
            self.id = generate_id(f"{self.name}_{source}", prefix="REG-")


# =============================================================================
# Extraction Container Model
# =============================================================================

class RegulationExtraction(BaseModel):
    """
    Container for extracting regulations from a document.
    
    The LLM will output this structure containing all regulations
    found in a single document.
    """
    regulations: List[Regulation] = Field(
        default_factory=list,
        description="List of all regulations extracted from the document"
    )
    document_name: str = Field(
        default="unknown",
        description="Name of the source document"
    )
    document_type: str = Field(
        default="Policy Document",
        description="Type of document (e.g., 'Compliance Policy', 'Regulatory Guide')"
    )
    extraction_notes: Optional[str] = Field(
        None,
        description="Any notes about the extraction"
    )
