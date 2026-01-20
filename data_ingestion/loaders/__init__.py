"""
Data Loaders
============

Loaders for populating Neo4j Knowledge Graph and LlamaStack Vector Store.

Includes:
- FSI (Financial Services) data loaders
- Migration data loaders (VCS to Vandelay Cloud)

Usage:
    from data_ingestion.loaders import FSIGraphLoader, FSIVectorLoader
    from data_ingestion.loaders import MigrationGraphLoader
    
    # Load FSI data to Neo4j
    graph_loader = FSIGraphLoader()
    graph_loader.initialize_schema(clear_first=True)
    graph_loader.load_products(products_data)
    
    # Load Migration data from CSV
    migration_loader = MigrationGraphLoader()
    migration_loader.initialize_schema(clear_first=True)
    migration_loader.load_from_csv("data/migration_csv")
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
from data_ingestion.loaders.migration_loader import (
    MigrationGraphLoader,
)
from data_ingestion.loaders.migration_schema import (
    create_migration_schema,
    clear_migration_data,
    get_migration_schema_summary,
)

__all__ = [
    # FSI Schema
    "NODE_CONSTRAINTS",
    "INDEXES",
    "create_constraints",
    "create_indexes",
    "create_all_schema",
    "clear_database",
    "drop_all_constraints",
    "get_schema_summary",
    # FSI Graph Loader
    "FSIGraphLoader",
    "get_driver",
    # FSI Vector Loader
    "FSIVectorLoader",
    # Migration Loader
    "MigrationGraphLoader",
    "create_migration_schema",
    "clear_migration_data",
    "get_migration_schema_summary",
]
