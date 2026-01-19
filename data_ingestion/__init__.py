"""
FSI Data Ingestion Module
=========================

This module handles the ingestion of FSI (Financial Services Industry) data
into both a Neo4j Knowledge Graph and a LlamaStack Vector Store.

The module is a PREREQUISITE for running the RAG agent - data must be ingested
before the agent can query it.

Usage:
    # Ingest graph data (from Cypher file)
    python -m data_ingestion.ingest_graph
    
    # Ingest vector data (documents)
    python -m data_ingestion.ingest_vector

Components:
    - ingest_graph.py: Load Cypher data into Neo4j
    - ingest_vector.py: Load documents into LlamaStack Vector Store
    - models/: Pydantic models for FSI entities
    - loaders/: Data store loaders (Neo4j Graph, LlamaStack Vector)
"""

__version__ = "1.0.0"

# Re-export key classes for convenience
from data_ingestion.loaders import (
    FSIGraphLoader,
    FSIVectorLoader,
)

__all__ = [
    # Loaders
    "FSIGraphLoader",
    "FSIVectorLoader",
]
