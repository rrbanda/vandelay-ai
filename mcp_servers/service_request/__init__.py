"""
Service Request Portal MCP Server

A mock MCP server for demonstrating infrastructure change request workflows
during VMware to BareMetal OpenShift migrations.

Supported request types:
- Firewall rules (new EgressIP whitelisting)
- Certificate orders (new certs for cluster routes)
- DNS changes (Vanity URL mappings)
- SSO configuration (registration with new SSO host)

This is a mock implementation for demonstration purposes.
Replace with actual CMP integration for production use.
"""

from .server import app, run_server
from .mock_responses import MockRequestStore

__all__ = ['app', 'run_server', 'MockRequestStore']
