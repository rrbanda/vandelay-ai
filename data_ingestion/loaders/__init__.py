"""
FSI Data Loaders
================

Loaders for populating Neo4j Knowledge Graph and LlamaStack Vector Store.

Usage:
    from data_ingestion.loaders import FSIGraphLoader, FSIVectorLoader
    
    # Load to Neo4j
    graph_loader = FSIGraphLoader()
    graph_loader.initialize_schema(clear_first=True)
    graph_loader.load_products(products_data)
    graph_loader.load_regulations(regulations_data)
    graph_loader.load_risks(risks_data)
    
    # Load to Vector Store
    vector_loader = FSIVectorLoader()
    vector_loader.load_from_directory("data_ingestion/data/fsi_documents")
"""

from data_ingestion.loaders.schema import (
    NODE_CONSTRAINTS,
    INDEXES,
    create_constraints,
    create_indexes,
    create_all_schema,
    clear_database,
    drop_all_constraints,
    get_schema_summary,
)
from data_ingestion.loaders.graph_loader import (
    FSIGraphLoader,
    get_driver,
)
from data_ingestion.loaders.vector_loader import (
    FSIVectorLoader,
)

__all__ = [
    # Schema
    "NODE_CONSTRAINTS",
    "INDEXES",
    "create_constraints",
    "create_indexes",
    "create_all_schema",
    "clear_database",
    "drop_all_constraints",
    "get_schema_summary",
    # Graph Loader
    "FSIGraphLoader",
    "get_driver",
    # Vector Loader
    "FSIVectorLoader",
]
