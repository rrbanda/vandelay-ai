"""
Neo4j Lifecycle Plugin for GraphRAG
=====================================

Manages Neo4j database connection lifecycle:
- Initialize connection pool on startup
- Verify connectivity before requests
- Clean up connections on shutdown
- Connection health monitoring

Usage:
    from graphrag.plugins import Neo4jLifecyclePlugin
    
    neo4j_plugin = Neo4jLifecyclePlugin()
    
    runner = InMemoryRunner(
        agent=root_agent,
        app_name='graphrag',
        plugins=[neo4j_plugin],
    )
"""

import logging
import time
from typing import Any, Dict, Optional

from google.adk.agents.invocation_context import InvocationContext
from google.adk.plugins.base_plugin import BasePlugin
from google.genai import types

logger = logging.getLogger(__name__)


class Neo4jLifecyclePlugin(BasePlugin):
    """
    Plugin that manages Neo4j connection lifecycle.
    
    Features:
    - Connection initialization on first use
    - Connection health checks
    - Connection statistics
    - Graceful shutdown
    """
    
    def __init__(
        self,
        name: str = "neo4j_lifecycle",
        verify_on_start: bool = True,
        log_stats: bool = False,
    ):
        super().__init__(name=name)
        self.verify_on_start = verify_on_start
        self.log_stats = log_stats
        
        # Connection stats
        self._stats = {
            'connections_verified': 0,
            'verification_failures': 0,
            'queries_executed': 0,
            'last_verification': None,
            'last_error': None,
        }
        
        # Track if initialized
        self._initialized = False
    
    def _get_driver(self):
        """Get the Neo4j driver (lazy import to avoid circular deps)."""
        try:
            from ..sub_agents.graph_query.tools import _get_driver
            return _get_driver()
        except Exception as e:
            logger.error(f"Failed to get Neo4j driver: {e}")
            return None
    
    def _verify_connection(self) -> bool:
        """Verify Neo4j connection is working."""
        try:
            driver = self._get_driver()
            if driver is None:
                return False
            
            # Run a simple query to verify connectivity
            with driver.session() as session:
                result = session.run("RETURN 1 as test")
                record = result.single()
                if record and record['test'] == 1:
                    self._stats['connections_verified'] += 1
                    self._stats['last_verification'] = time.time()
                    return True
            
            return False
        except Exception as e:
            self._stats['verification_failures'] += 1
            self._stats['last_error'] = str(e)
            logger.error(f"Neo4j connection verification failed: {e}")
            return False
    
    # =========================================================================
    # Runner Callbacks
    # =========================================================================
    
    async def before_run_callback(
        self,
        *,
        invocation_context: InvocationContext,
    ) -> Optional[types.Content]:
        """
        Initialize and verify Neo4j connection before processing.
        """
        if self.verify_on_start:
            if not self._initialized:
                logger.info("Initializing Neo4j connection...")
                if self._verify_connection():
                    logger.info("Neo4j connection verified successfully")
                    self._initialized = True
                else:
                    logger.warning("Neo4j connection verification failed")
                    # Don't block execution, tools will handle failures
        
        return None
    
    async def after_run_callback(
        self,
        *,
        invocation_context: InvocationContext,
    ) -> None:
        """
        Log connection stats after run completion.
        """
        if self.log_stats:
            logger.info(f"Neo4j stats: {self._stats}")
    
    # =========================================================================
    # Stats and Health
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return dict(self._stats)
    
    def is_healthy(self) -> bool:
        """Check if connection is healthy."""
        return self._verify_connection()
    
    def reset_stats(self):
        """Reset connection statistics."""
        self._stats = {
            'connections_verified': 0,
            'verification_failures': 0,
            'queries_executed': 0,
            'last_verification': None,
            'last_error': None,
        }
    
    # =========================================================================
    # Cleanup (called externally, not by ADK)
    # =========================================================================
    
    def close(self):
        """
        Close Neo4j driver connection.
        
        Note: This should be called when shutting down the application.
        ADK doesn't have an automatic shutdown hook for plugins.
        """
        try:
            from ..sub_agents.graph_query.tools import _driver
            if _driver is not None:
                _driver.close()
                logger.info("Neo4j connection closed")
        except Exception as e:
            logger.error(f"Error closing Neo4j connection: {e}")
