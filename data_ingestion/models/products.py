"""
Product models for FSI banking products.

This module defines Pydantic models for extracting banking product information
from documents like account guides, loan products, and credit card guides.

Product types covered:
- Deposit accounts (Checking, Savings, Money Market, CDs)
- Loans (Mortgages, Personal, Auto, Home Equity)
- Credit Cards (Rewards, Secured, Business)

Based on:
- data_ingestion/data/fsi_documents/account_types_guide.txt
- data_ingestion/data/fsi_documents/loan_products_guide.txt  
- data_ingestion/data/fsi_documents/credit_cards_guide.txt
"""

from datetime import date
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from .base import ExtractedEntity, generate_id


# =============================================================================
# Product Category Enums
# =============================================================================

class ProductCategory(str, Enum):
    """
    Top-level product categories.
    
    Groups products into major banking categories for filtering and organization.
    """
    # Deposit Accounts
    CHECKING = "Checking Account"
    SAVINGS = "Savings Account"
    MONEY_MARKET = "Money Market Account"
    CERTIFICATE_OF_DEPOSIT = "Certificate of Deposit"
    
    # Loans
    MORTGAGE = "Mortgage"
    PERSONAL_LOAN = "Personal Loan"
    AUTO_LOAN = "Auto Loan"
    HOME_EQUITY = "Home Equity"
    
    # Cards
    CREDIT_CARD = "Credit Card"
    DEBIT_CARD = "Debit Card"


class ProductSubcategory(str, Enum):
    """
    Product subcategories for finer classification.
    
    Provides more specific categorization within each ProductCategory.
    """
    # Checking subcategories
    BASIC_CHECKING = "Basic Checking"
    PREMIUM_CHECKING = "Premium Checking"
    STUDENT_CHECKING = "Student Checking"
    BUSINESS_CHECKING = "Business Checking"
    
    # Savings subcategories
    REGULAR_SAVINGS = "Regular Savings"
    HIGH_YIELD_SAVINGS = "High-Yield Savings"
    
    # CD terms
    SHORT_TERM_CD = "Short-Term CD"      # < 12 months
    MEDIUM_TERM_CD = "Medium-Term CD"    # 12-24 months
    LONG_TERM_CD = "Long-Term CD"        # > 24 months
    
    # Mortgage types
    FIXED_RATE_MORTGAGE = "Fixed Rate Mortgage"
    ADJUSTABLE_RATE_MORTGAGE = "Adjustable Rate Mortgage"
    FHA_LOAN = "FHA Loan"
    VA_LOAN = "VA Loan"
    JUMBO_LOAN = "Jumbo Loan"
    
    # Personal loan types
    UNSECURED_LOAN = "Unsecured Loan"
    SECURED_LOAN = "Secured Loan"
    
    # Home equity types
    HOME_EQUITY_LOAN = "Home Equity Loan"
    HOME_EQUITY_LINE_OF_CREDIT = "Home Equity Line of Credit"
    
    # Auto loan types
    NEW_AUTO = "New Auto"
    USED_AUTO = "Used Auto"
    AUTO_REFINANCE = "Auto Refinance"
    
    # Credit card types
    CASH_BACK_CARD = "Cash Back Card"
    TRAVEL_REWARDS_CARD = "Travel Rewards Card"
    PREMIUM_REWARDS_CARD = "Premium Rewards Card"
    SECURED_CARD = "Secured Card"
    STUDENT_CARD = "Student Card"
    BUSINESS_CARD = "Business Card"
    LOW_INTEREST_CARD = "Low Interest Card"
    
    # Generic fallback
    STANDARD = "Standard"


# =============================================================================
# Fee Models
# =============================================================================

class FeeType(str, Enum):
    """
    Types of fees associated with banking products.
    """
    MONTHLY_MAINTENANCE = "Monthly Maintenance Fee"
    ANNUAL_FEE = "Annual Fee"
    OVERDRAFT = "Overdraft Fee"
    NSF = "Non-Sufficient Funds Fee"
    WIRE_TRANSFER_DOMESTIC = "Domestic Wire Transfer Fee"
    WIRE_TRANSFER_INTERNATIONAL = "International Wire Transfer Fee"
    ATM_OUT_OF_NETWORK = "Out-of-Network ATM Fee"
    ATM_INTERNATIONAL = "International ATM Fee"
    FOREIGN_TRANSACTION = "Foreign Transaction Fee"
    EARLY_WITHDRAWAL = "Early Withdrawal Penalty"
    BALANCE_TRANSFER = "Balance Transfer Fee"
    CASH_ADVANCE = "Cash Advance Fee"
    LATE_PAYMENT = "Late Payment Fee"
    OVER_LIMIT = "Over-Limit Fee"
    PAPER_STATEMENT = "Paper Statement Fee"
    STOP_PAYMENT = "Stop Payment Fee"
    RETURNED_ITEM = "Returned Item Fee"
    ACCOUNT_CLOSURE = "Account Closure Fee"
    OTHER = "Other Fee"


class Fee(BaseModel):
    """
    A fee associated with a banking product.
    
    Captures the fee type, amount, and any conditions for waiver.
    """
    type: FeeType = Field(
        ...,
        description="The type of fee"
    )
    amount: Optional[float] = Field(
        None,
        ge=0,
        description="Fee amount in dollars. Use None if fee is variable."
    )
    amount_description: Optional[str] = Field(
        None,
        description="Description of fee amount if variable (e.g., '3% of amount')"
    )
    waiver_condition: Optional[str] = Field(
        None,
        description="Condition to waive the fee (e.g., 'maintain $500 minimum balance')"
    )
    is_waivable: bool = Field(
        default=False,
        description="Whether this fee can be waived under certain conditions"
    )
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        """Ensure fee amount is non-negative."""
        if v is not None and v < 0:
            raise ValueError('Fee amount cannot be negative')
        return v


# =============================================================================
# Feature and Reward Models
# =============================================================================

class Feature(BaseModel):
    """
    A feature or benefit of a banking product.
    
    Features are selling points that differentiate products.
    """
    name: str = Field(
        ...,
        description="Name of the feature (e.g., 'Free debit card', 'No foreign transaction fees')"
    )
    description: Optional[str] = Field(
        None,
        description="Detailed description of the feature"
    )
    is_highlighted: bool = Field(
        default=False,
        description="Whether this is a primary/highlighted feature"
    )


class Reward(BaseModel):
    """
    Rewards program details for credit cards.
    
    Captures earning rates, bonus offers, and redemption options.
    """
    category: str = Field(
        ...,
        description="Spending category (e.g., 'travel', 'dining', 'all purchases')"
    )
    rate: float = Field(
        ...,
        ge=0,
        description="Reward rate (e.g., 2.0 for 2% cash back or 3.0 for 3X points)"
    )
    rate_type: str = Field(
        default="percent",
        description="Type of rate: 'percent' for cash back, 'multiplier' for points"
    )
    description: Optional[str] = Field(
        None,
        description="Additional details about the reward"
    )


class SignupBonus(BaseModel):
    """
    Welcome/signup bonus for credit cards.
    """
    value: str = Field(
        ...,
        description="Bonus value (e.g., '$200', '60,000 points')"
    )
    spend_requirement: Optional[float] = Field(
        None,
        ge=0,
        description="Required spending to earn bonus in dollars"
    )
    time_period_months: Optional[int] = Field(
        None,
        ge=1,
        description="Time period to meet spend requirement in months"
    )


# =============================================================================
# Requirement Model
# =============================================================================

class ProductRequirement(BaseModel):
    """
    Requirements to open or maintain a product.
    
    Examples: minimum balance, credit score, documentation.
    """
    requirement_type: str = Field(
        ...,
        description="Type of requirement (e.g., 'Minimum Balance', 'Credit Score', 'Documentation')"
    )
    value: Optional[str] = Field(
        None,
        description="Required value (e.g., '$500', '620+', 'Government-issued ID')"
    )
    description: Optional[str] = Field(
        None,
        description="Detailed description of the requirement"
    )
    is_mandatory: bool = Field(
        default=True,
        description="Whether this requirement is mandatory"
    )


# =============================================================================
# Main Product Model
# =============================================================================

class Product(ExtractedEntity):
    """
    A banking product extracted from documents.
    
    This is the main entity representing any banking product:
    accounts, loans, credit cards, etc.
    
    Inherits from ExtractedEntity to track source document.
    """
    # Identity
    id: str = Field(
        default="",
        description="Unique identifier (auto-generated if empty)"
    )
    name: str = Field(
        ...,
        description="Product name exactly as stated in document (e.g., 'Fixed Rate Mortgage 30Y')"
    )
    
    # Classification
    category: ProductCategory = Field(
        ...,
        description="Primary product category"
    )
    subcategory: Optional[ProductSubcategory] = Field(
        None,
        description="More specific subcategory if applicable"
    )
    
    # Financial Terms
    interest_rate_apy: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Annual Percentage Yield for deposit products (e.g., 4.25 for 4.25%)"
    )
    interest_rate_apr: Optional[float] = Field(
        None,
        ge=0,
        le=100,
        description="Annual Percentage Rate for loans/cards (e.g., 6.5 for 6.5%)"
    )
    interest_rate_range: Optional[str] = Field(
        None,
        description="Interest rate range if variable (e.g., '19.99% - 29.99%')"
    )
    minimum_balance: Optional[float] = Field(
        None,
        ge=0,
        description="Minimum balance requirement in dollars"
    )
    minimum_opening_deposit: Optional[float] = Field(
        None,
        ge=0,
        description="Minimum amount to open the account in dollars"
    )
    term_months: Optional[int] = Field(
        None,
        ge=1,
        description="Term length in months (for CDs, loans)"
    )
    credit_limit_min: Optional[float] = Field(
        None,
        ge=0,
        description="Minimum credit limit (for credit cards)"
    )
    credit_limit_max: Optional[float] = Field(
        None,
        ge=0,
        description="Maximum credit limit (for credit cards)"
    )
    loan_amount_min: Optional[float] = Field(
        None,
        ge=0,
        description="Minimum loan amount"
    )
    loan_amount_max: Optional[float] = Field(
        None,
        ge=0,
        description="Maximum loan amount"
    )
    
    # Features, Fees, Rewards
    features: List[Feature] = Field(
        default_factory=list,
        description="List of product features and benefits"
    )
    fees: List[Fee] = Field(
        default_factory=list,
        description="List of associated fees"
    )
    rewards: List[Reward] = Field(
        default_factory=list,
        description="Reward program details (for credit cards)"
    )
    signup_bonus: Optional[SignupBonus] = Field(
        None,
        description="Welcome bonus (for credit cards)"
    )
    requirements: List[ProductRequirement] = Field(
        default_factory=list,
        description="Requirements to open/maintain the product"
    )
    
    # Target Audience
    best_for: Optional[str] = Field(
        None,
        description="Target customer segment (e.g., 'first-time home buyers', 'students')"
    )
    eligibility: Optional[str] = Field(
        None,
        description="Eligibility criteria (e.g., 'ages 17-24', 'credit score 620+')"
    )
    
    # FDIC/Protection
    is_fdic_insured: bool = Field(
        default=False,
        description="Whether the product is FDIC insured"
    )
    fdic_coverage: Optional[float] = Field(
        None,
        ge=0,
        description="FDIC coverage amount in dollars (e.g., 250000)"
    )
    
    def __init__(self, **data):
        """Generate ID if not provided."""
        super().__init__(**data)
        if not self.id:
            # Generate deterministic ID from name + source
            source = self.source_document or "unknown"
            self.id = generate_id(f"{self.name}_{source}", prefix="PROD-")


# =============================================================================
# Extraction Container Model
# =============================================================================

class ProductExtraction(BaseModel):
    """
    Container for extracting multiple products from a document.
    
    The LLM will output this structure containing all products
    found in a single document.
    """
    products: List[Product] = Field(
        default_factory=list,
        description="List of all products extracted from the document"
    )
    document_name: str = Field(
        default="unknown",
        description="Name of the source document"
    )
    document_type: str = Field(
        default="Product Guide",
        description="Type of document (e.g., 'Product Guide', 'Account Types Guide')"
    )
    extraction_notes: Optional[str] = Field(
        None,
        description="Any notes about the extraction (e.g., 'Some rates may be promotional')"
    )
