"""
Base utilities and common types for FSI entity models.

This module provides:
- ID generation utilities (deterministic, short IDs)
- Common base classes
- Shared type definitions

Based on patterns from tmp/person.py in the employee knowledge graph example.
"""

import base64
import hashlib
from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# =============================================================================
# ID Generation Utilities
# =============================================================================

def generate_id(input_string: str, prefix: str = "", length: int = 8) -> str:
    """
    Generate a short, deterministic ID from a string.
    
    Uses MD5 hash + base64 encoding to create consistent IDs.
    Same input always produces the same output.
    
    Args:
        input_string: Source string to hash (e.g., product name + source doc)
        prefix: Optional prefix (e.g., "PROD-", "REG-")
        length: Length of the random portion (default 8)
        
    Returns:
        Deterministic ID like "PROD-a1b2c3d4"
        
    Example:
        >>> generate_id("Fixed Rate Mortgage 30Y", prefix="PROD-")
        'PROD-kX9mN2pQ'
    """
    # Create deterministic hash
    hash_object = hashlib.md5(input_string.encode())
    digest = hash_object.digest()
    
    # Encode in base64, keep only alphanumeric
    b64_encoded = base64.b64encode(digest).decode('ascii')
    clean_id = ''.join(c for c in b64_encoded if c.isalnum())
    
    # Return with optional prefix
    short_id = clean_id[:length]
    return f"{prefix}{short_id}" if prefix else short_id


def normalize_name(name: str) -> str:
    """
    Normalize entity names for consistent matching.
    
    Used for entity resolution to detect duplicates like:
    - "Basel III" vs "BASEL III" vs "basel iii"
    
    Args:
        name: Original entity name
        
    Returns:
        Normalized lowercase, trimmed name
    """
    return name.strip().lower()


# =============================================================================
# Common Enums (shared across multiple models)
# =============================================================================

class RiskLevel(str, Enum):
    """
    Risk level classification.
    
    Used for customer risk assessment, portfolio risk, etc.
    """
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class Jurisdiction(str, Enum):
    """
    Regulatory jurisdictions.
    
    Determines which regulations apply to entities.
    """
    US = "US"
    EU = "EU"
    UK = "UK"
    INTERNATIONAL = "International"
    ASIA_PACIFIC = "Asia-Pacific"


class Currency(str, Enum):
    """Common currencies for financial products."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CHF = "CHF"


# =============================================================================
# Base Models
# =============================================================================

class ExtractedEntity(BaseModel):
    """
    Base class for all extracted entities.
    
    Provides common fields for tracking extraction metadata:
    - source_document: Which document this was extracted from
    - extraction_confidence: How confident the LLM was (optional)
    
    All entity models should inherit from this.
    """
    source_document: Optional[str] = Field(
        None,
        description="Name of the source document this entity was extracted from"
    )
    extraction_date: Optional[date] = Field(
        None,
        description="Date when this entity was extracted"
    )
    
    class Config:
        """Pydantic configuration."""
        # Allow population by field name or alias
        populate_by_name = True
        # Validate on assignment (not just initialization)
        validate_assignment = True


class SourceReference(BaseModel):
    """
    Reference to source document for traceability.
    
    Per GraphRAG book Chapter 6.2.3:
    "Storing the original unstructured documents and the extracted 
    structured data within the graph preserves the richness of the 
    original data while enabling more precise querying."
    """
    document_name: str = Field(..., description="Name of the source document")
    document_type: Optional[str] = Field(
        None,
        description="Type of document (e.g., 'Product Guide', 'Policy Document')"
    )
    section: Optional[str] = Field(
        None,
        description="Specific section within the document"
    )
    page_or_line: Optional[str] = Field(
        None,
        description="Page number or line reference"
    )


# =============================================================================
# Validation Helpers
# =============================================================================

def validate_percentage(value: float, field_name: str = "value") -> float:
    """
    Validate that a value is a valid percentage (0-100).
    
    Args:
        value: The percentage value
        field_name: Name for error messages
        
    Returns:
        The validated value
        
    Raises:
        ValueError: If value is out of range
    """
    if value < 0 or value > 100:
        raise ValueError(f"{field_name} must be between 0 and 100, got {value}")
    return value


def validate_positive(value: float, field_name: str = "value") -> float:
    """
    Validate that a value is positive.
    
    Args:
        value: The numeric value
        field_name: Name for error messages
        
    Returns:
        The validated value
        
    Raises:
        ValueError: If value is negative
    """
    if value < 0:
        raise ValueError(f"{field_name} must be positive, got {value}")
    return value
