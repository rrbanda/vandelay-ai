#!/usr/bin/env python3
"""
Service Request Portal MCP Server

A mock MCP server that simulates infrastructure change request workflows
for VMware to BareMetal OpenShift migrations.

This server provides tools for:
- Firewall rule requests
- Certificate orders
- DNS/Vanity URL changes
- SSO configuration requests
- Operator installation requests
- Cleanup requests

Usage:
    # Run standalone server
    python -m mcp_servers.service_request.server
    
    # Or import and use programmatically
    from mcp_servers.service_request import run_server
    run_server(port=8080)

The server implements the MCP (Model Context Protocol) specification
for integration with AI agents.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .mock_responses import (
    get_store,
    RequestType,
    RequestStatus,
    MockRequestStore,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServiceRequestTools:
    """
    MCP Tool implementations for Service Request Portal.
    
    Each method is a tool that can be called by AI agents.
    """
    
    def __init__(self, store: MockRequestStore = None):
        """Initialize with optional custom store."""
        self.store = store or get_store()
    
    def submit_firewall_request(
        self,
        namespace: str,
        source_egress_ips: List[str],
        destination_hosts: List[str],
        destination_ports: List[str],
        protocol: str = "TCP",
        justification: str = "",
    ) -> Dict[str, Any]:
        """
        Submit a firewall rule request for new EgressIP whitelisting.
        
        Args:
            namespace: Namespace requiring the firewall rule
            source_egress_ips: List of new BareMetal EgressIP addresses
            destination_hosts: Target hosts/IPs that need access
            destination_ports: Target ports
            protocol: TCP or UDP (default: TCP)
            justification: Business justification for the request
            
        Returns:
            Ticket information including ID and estimated completion
        """
        details = {
            "source_egress_ips": source_egress_ips,
            "destination_hosts": destination_hosts,
            "destination_ports": destination_ports,
            "protocol": protocol,
            "direction": "outbound",
        }
        
        request = self.store.create_request(
            request_type=RequestType.FIREWALL,
            namespace=namespace,
            details=details,
            justification=justification or f"Migration firewall request for {namespace}",
        )
        
        return {
            "success": True,
            "ticket_id": request["ticket_id"],
            "status": request["status"],
            "message": f"Firewall request submitted. Estimated completion: {request['estimated_completion']}",
            "lead_time_days": request["lead_time_days"],
            "request": request,
        }
    
    def submit_certificate_request(
        self,
        namespace: str,
        common_name: str,
        san_list: List[str],
        certificate_type: str = "server",
        justification: str = "",
    ) -> Dict[str, Any]:
        """
        Submit a certificate request for new/updated certificates.
        
        Args:
            namespace: Namespace requiring the certificate
            common_name: Primary hostname for the certificate
            san_list: Subject Alternative Names to include
            certificate_type: Type of certificate (server, client, etc.)
            justification: Business justification
            
        Returns:
            Ticket information including ID and estimated completion
        """
        details = {
            "common_name": common_name,
            "san_list": san_list,
            "certificate_type": certificate_type,
            "key_size": 2048,
            "validity_years": 1,
        }
        
        request = self.store.create_request(
            request_type=RequestType.CERTIFICATE,
            namespace=namespace,
            details=details,
            justification=justification or f"Migration certificate for {namespace}",
        )
        
        return {
            "success": True,
            "ticket_id": request["ticket_id"],
            "status": request["status"],
            "message": f"Certificate request submitted. Estimated completion: {request['estimated_completion']}",
            "lead_time_days": request["lead_time_days"],
            "request": request,
        }
    
    def submit_dns_request(
        self,
        namespace: str,
        vanity_url: str,
        target_vip: str,
        target_vip_ip: str,
        request_type: str = "create",
        justification: str = "",
    ) -> Dict[str, Any]:
        """
        Submit a DNS/Vanity URL request.
        
        Args:
            namespace: Associated namespace
            vanity_url: The vanity URL to create/modify
            target_vip: Target VIP hostname
            target_vip_ip: Target VIP IP address
            request_type: create, modify, or delete
            justification: Business justification
            
        Returns:
            Ticket information
        """
        details = {
            "vanity_url": vanity_url,
            "target_vip": target_vip,
            "target_vip_ip": target_vip_ip,
            "dns_action": request_type,
        }
        
        request = self.store.create_request(
            request_type=RequestType.DNS,
            namespace=namespace,
            details=details,
            justification=justification or f"Migration DNS request for {vanity_url}",
        )
        
        return {
            "success": True,
            "ticket_id": request["ticket_id"],
            "status": request["status"],
            "message": f"DNS request submitted. Estimated completion: {request['estimated_completion']}",
            "lead_time_days": request["lead_time_days"],
            "request": request,
        }
    
    def submit_sso_request(
        self,
        namespace: str,
        application_id: str,
        sso_provider: str,
        base_url: str,
        new_sso_host: str,
        request_type: str = "registration",
        justification: str = "",
    ) -> Dict[str, Any]:
        """
        Submit an SSO configuration request.
        
        Args:
            namespace: Namespace for the application
            application_id: Application identifier
            sso_provider: SSO provider type (modern_sso, legacy_sso)
            base_url: Application base URL for SSO
            new_sso_host: New SSO registration hostname
            request_type: registration, modification, or removal
            justification: Business justification
            
        Returns:
            Ticket information
        """
        details = {
            "application_id": application_id,
            "sso_provider": sso_provider,
            "base_url": base_url,
            "new_sso_host": new_sso_host,
            "sso_action": request_type,
        }
        
        request = self.store.create_request(
            request_type=RequestType.SSO,
            namespace=namespace,
            details=details,
            justification=justification or f"Migration SSO request for {application_id}",
        )
        
        return {
            "success": True,
            "ticket_id": request["ticket_id"],
            "status": request["status"],
            "message": f"SSO request submitted. Estimated completion: {request['estimated_completion']}",
            "lead_time_days": request["lead_time_days"],
            "request": request,
        }
    
    def submit_operator_request(
        self,
        namespace: str,
        operator_name: str,
        operator_config: Dict[str, Any],
        destination_cluster: str,
        justification: str = "",
    ) -> Dict[str, Any]:
        """
        Submit an operator installation request to Platform Ops.
        
        Args:
            namespace: Target namespace
            operator_name: Name of operator (redis, couchbase, service_mesh)
            operator_config: Configuration including resource requirements
            destination_cluster: BareMetal cluster name
            justification: Business justification
            
        Returns:
            Ticket information
        """
        details = {
            "operator_name": operator_name,
            "operator_config": operator_config,
            "destination_cluster": destination_cluster,
        }
        
        request = self.store.create_request(
            request_type=RequestType.OPERATOR,
            namespace=namespace,
            details=details,
            justification=justification or f"Operator installation: {operator_name}",
        )
        
        return {
            "success": True,
            "ticket_id": request["ticket_id"],
            "status": request["status"],
            "message": f"Operator request submitted. Estimated completion: {request['estimated_completion']}",
            "lead_time_days": request["lead_time_days"],
            "request": request,
        }
    
    def submit_cleanup_request(
        self,
        namespace: str,
        source_cluster: str,
        environment: str,
        confirmation: str,
        justification: str = "",
    ) -> Dict[str, Any]:
        """
        Submit a cleanup request to delete project from source cluster.
        
        Args:
            namespace: Namespace to delete
            source_cluster: VMware cluster to delete from
            environment: DEV, UAT, or PROD
            confirmation: Confirmation string (must be "I_CONFIRM_DELETION")
            justification: Business justification
            
        Returns:
            Ticket information
        """
        if confirmation != "I_CONFIRM_DELETION":
            return {
                "success": False,
                "error": "Cleanup request requires confirmation='I_CONFIRM_DELETION'",
            }
        
        details = {
            "source_cluster": source_cluster,
            "environment": environment,
            "cleanup_type": "project_deletion",
            "confirmed": True,
        }
        
        # Use incident for DEV, change for UAT/PROD
        ticket_type = "incident" if environment == "DEV" else "change"
        
        request = self.store.create_request(
            request_type=RequestType.CLEANUP,
            namespace=namespace,
            details=details,
            justification=justification or f"Post-migration cleanup for {namespace}",
        )
        
        request["ticket_type"] = ticket_type
        
        return {
            "success": True,
            "ticket_id": request["ticket_id"],
            "ticket_type": ticket_type,
            "status": request["status"],
            "message": f"Cleanup request submitted as {ticket_type}. Namespace will be deleted from {source_cluster}.",
            "lead_time_days": request["lead_time_days"],
            "warning": "This action is irreversible. Deleted projects cannot be restored.",
            "request": request,
        }
    
    def check_request_status(self, ticket_id: str) -> Dict[str, Any]:
        """
        Check the status of a service request.
        
        Args:
            ticket_id: The ticket ID to check
            
        Returns:
            Current status and request details
        """
        request = self.store.get_request(ticket_id)
        
        if not request:
            return {
                "success": False,
                "error": f"Ticket {ticket_id} not found",
            }
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "status": request["status"],
            "request_type": request["request_type"],
            "namespace": request["namespace"],
            "created_at": request["created_at"],
            "updated_at": request["updated_at"],
            "estimated_completion": request["estimated_completion"],
            "details": request["details"],
            "notes": request["notes"],
        }
    
    def list_open_requests(
        self,
        namespace: str = None,
        request_type: str = None,
    ) -> Dict[str, Any]:
        """
        List all open service requests.
        
        Args:
            namespace: Optional filter by namespace
            request_type: Optional filter by type (firewall, certificate, dns, sso)
            
        Returns:
            List of open requests
        """
        type_filter = None
        if request_type:
            try:
                type_filter = RequestType(request_type)
            except ValueError:
                pass
        
        requests = self.store.list_requests(
            namespace=namespace,
            request_type=type_filter,
        )
        
        # Filter to open only
        open_statuses = ["submitted", "pending_approval", "approved", "in_progress"]
        open_requests = [r for r in requests if r["status"] in open_statuses]
        
        return {
            "success": True,
            "count": len(open_requests),
            "requests": [
                {
                    "ticket_id": r["ticket_id"],
                    "request_type": r["request_type"],
                    "namespace": r["namespace"],
                    "status": r["status"],
                    "created_at": r["created_at"],
                    "estimated_completion": r["estimated_completion"],
                }
                for r in open_requests
            ],
        }
    
    def simulate_approval(self, ticket_id: str) -> Dict[str, Any]:
        """
        Simulate approval/progress on a request (for demo purposes).
        
        This advances the request through workflow stages:
        submitted → pending_approval → approved → in_progress → completed
        
        Args:
            ticket_id: Ticket to advance
            
        Returns:
            Updated status
        """
        request = self.store.simulate_progress(ticket_id)
        
        if not request:
            return {
                "success": False,
                "error": f"Ticket {ticket_id} not found",
            }
        
        return {
            "success": True,
            "ticket_id": ticket_id,
            "previous_status": "progressed",
            "new_status": request["status"],
            "message": f"Request progressed to {request['status']}",
        }


# Create global tools instance
tools = ServiceRequestTools()


def get_tool_definitions() -> List[dict]:
    """Get MCP tool definitions for this server."""
    return [
        {
            "name": "submit_firewall_request",
            "description": "Submit a firewall rule request for new EgressIP whitelisting. Use when migrating to BareMetal OpenShift and internal systems need updated firewall rules.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "Namespace requiring the firewall rule"},
                    "source_egress_ips": {"type": "array", "items": {"type": "string"}, "description": "New BareMetal EgressIP addresses"},
                    "destination_hosts": {"type": "array", "items": {"type": "string"}, "description": "Target hosts/IPs that need access"},
                    "destination_ports": {"type": "array", "items": {"type": "string"}, "description": "Target ports"},
                    "protocol": {"type": "string", "enum": ["TCP", "UDP"], "default": "TCP"},
                    "justification": {"type": "string", "description": "Business justification"},
                },
                "required": ["namespace", "source_egress_ips", "destination_hosts", "destination_ports"],
            },
        },
        {
            "name": "submit_certificate_request",
            "description": "Submit a certificate request for migration. Use when cluster-based routes are in the SAN list and need updating.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "Namespace requiring the certificate"},
                    "common_name": {"type": "string", "description": "Primary hostname for the certificate"},
                    "san_list": {"type": "array", "items": {"type": "string"}, "description": "Subject Alternative Names"},
                    "certificate_type": {"type": "string", "default": "server"},
                    "justification": {"type": "string"},
                },
                "required": ["namespace", "common_name", "san_list"],
            },
        },
        {
            "name": "submit_dns_request",
            "description": "Submit a DNS/Vanity URL request. Use to create or modify Vanity URL mappings to new cluster VIP.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "Associated namespace"},
                    "vanity_url": {"type": "string", "description": "The vanity URL"},
                    "target_vip": {"type": "string", "description": "Target VIP hostname"},
                    "target_vip_ip": {"type": "string", "description": "Target VIP IP address"},
                    "request_type": {"type": "string", "enum": ["create", "modify", "delete"], "default": "create"},
                    "justification": {"type": "string"},
                },
                "required": ["namespace", "vanity_url", "target_vip", "target_vip_ip"],
            },
        },
        {
            "name": "submit_sso_request",
            "description": "Submit an SSO configuration request for migration. Use to register with new SSO host or update base URL.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "application_id": {"type": "string", "description": "Application identifier"},
                    "sso_provider": {"type": "string", "enum": ["modern_sso", "legacy_sso"]},
                    "base_url": {"type": "string", "description": "Application base URL"},
                    "new_sso_host": {"type": "string", "description": "New SSO registration hostname"},
                    "request_type": {"type": "string", "enum": ["registration", "modification", "removal"], "default": "registration"},
                    "justification": {"type": "string"},
                },
                "required": ["namespace", "application_id", "sso_provider", "base_url", "new_sso_host"],
            },
        },
        {
            "name": "submit_operator_request",
            "description": "Submit an operator installation request to Platform Ops. Use for Redis, Couchbase, Service Mesh, etc.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                    "operator_name": {"type": "string", "enum": ["redis", "couchbase", "service_mesh", "other"]},
                    "operator_config": {"type": "object", "description": "Configuration including resource requirements"},
                    "destination_cluster": {"type": "string", "description": "BareMetal cluster name"},
                    "justification": {"type": "string"},
                },
                "required": ["namespace", "operator_name", "operator_config", "destination_cluster"],
            },
        },
        {
            "name": "submit_cleanup_request",
            "description": "Submit a cleanup request to delete project from source VMware cluster after successful migration.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "Namespace to delete"},
                    "source_cluster": {"type": "string", "description": "VMware cluster to delete from"},
                    "environment": {"type": "string", "enum": ["DEV", "UAT", "PROD"]},
                    "confirmation": {"type": "string", "description": "Must be 'I_CONFIRM_DELETION'"},
                    "justification": {"type": "string"},
                },
                "required": ["namespace", "source_cluster", "environment", "confirmation"],
            },
        },
        {
            "name": "check_request_status",
            "description": "Check the status of a service request by ticket ID.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string", "description": "The ticket ID to check"},
                },
                "required": ["ticket_id"],
            },
        },
        {
            "name": "list_open_requests",
            "description": "List all open service requests, optionally filtered by namespace or type.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "namespace": {"type": "string", "description": "Filter by namespace"},
                    "request_type": {"type": "string", "enum": ["firewall", "certificate", "dns", "sso", "operator", "cleanup"]},
                },
            },
        },
        {
            "name": "simulate_approval",
            "description": "Simulate approval/progress on a request (demo only). Advances request through workflow stages.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "ticket_id": {"type": "string", "description": "Ticket to advance"},
                },
                "required": ["ticket_id"],
            },
        },
    ]


def call_tool(name: str, arguments: dict) -> dict:
    """
    Call an MCP tool by name with arguments.
    
    Args:
        name: Tool name
        arguments: Tool arguments
        
    Returns:
        Tool result
    """
    tool_methods = {
        "submit_firewall_request": tools.submit_firewall_request,
        "submit_certificate_request": tools.submit_certificate_request,
        "submit_dns_request": tools.submit_dns_request,
        "submit_sso_request": tools.submit_sso_request,
        "submit_operator_request": tools.submit_operator_request,
        "submit_cleanup_request": tools.submit_cleanup_request,
        "check_request_status": tools.check_request_status,
        "list_open_requests": tools.list_open_requests,
        "simulate_approval": tools.simulate_approval,
    }
    
    method = tool_methods.get(name)
    if not method:
        return {"error": f"Unknown tool: {name}"}
    
    try:
        return method(**arguments)
    except Exception as e:
        logger.error(f"Error calling tool {name}: {e}")
        return {"error": str(e)}


# Simple HTTP server for standalone operation
app = None

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    
    app = FastAPI(
        title="Service Request Portal MCP Server",
        description="Mock MCP server for migration service requests",
        version="1.0.0",
    )
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    @app.get("/tools")
    async def list_tools():
        return {"tools": get_tool_definitions()}
    
    @app.post("/tools/{tool_name}")
    async def invoke_tool(tool_name: str, request: Request):
        body = await request.json()
        result = call_tool(tool_name, body)
        return JSONResponse(content=result)
    
    @app.post("/mcp/call")
    async def mcp_call(request: Request):
        """MCP-compatible endpoint."""
        body = await request.json()
        tool_name = body.get("name")
        arguments = body.get("arguments", {})
        result = call_tool(tool_name, arguments)
        return JSONResponse(content={"content": [{"type": "text", "text": json.dumps(result)}]})

except ImportError:
    logger.info("FastAPI not available. HTTP server disabled.")


def run_server(host: str = "0.0.0.0", port: int = 8080):
    """Run the MCP server."""
    if app is None:
        raise RuntimeError("FastAPI is required to run the server. Install with: pip install fastapi uvicorn")
    
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Service Request Portal MCP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    
    args = parser.parse_args()
    
    print(f"Starting Service Request Portal MCP Server on {args.host}:{args.port}")
    run_server(args.host, args.port)
