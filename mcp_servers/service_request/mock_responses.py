"""
Mock Response Store for Service Request Portal

Provides in-memory storage and mock responses for service request
demonstration. Simulates ticket creation, status tracking, and
approval workflows.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum


class RequestStatus(Enum):
    """Service request status values."""
    SUBMITTED = "submitted"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class RequestType(Enum):
    """Types of service requests."""
    FIREWALL = "firewall"
    CERTIFICATE = "certificate"
    DNS = "dns"
    SSO = "sso"
    OPERATOR = "operator"
    CLEANUP = "cleanup"


# Lead times by request type (in days)
LEAD_TIMES = {
    RequestType.FIREWALL: 14,
    RequestType.CERTIFICATE: 7,
    RequestType.DNS: 3,
    RequestType.SSO: 7,
    RequestType.OPERATOR: 5,
    RequestType.CLEANUP: 3,
}


class MockRequestStore:
    """
    In-memory store for mock service requests.
    
    Simulates a service request portal with ticket creation,
    status tracking, and mock approval workflows.
    """
    
    def __init__(self):
        """Initialize empty request store."""
        self._requests: Dict[str, dict] = {}
        self._counter = 1000
    
    def _generate_ticket_id(self, request_type: RequestType) -> str:
        """Generate a unique ticket ID."""
        self._counter += 1
        prefix = {
            RequestType.FIREWALL: "FW",
            RequestType.CERTIFICATE: "CERT",
            RequestType.DNS: "DNS",
            RequestType.SSO: "SSO",
            RequestType.OPERATOR: "OPS",
            RequestType.CLEANUP: "CLN",
        }.get(request_type, "REQ")
        
        return f"{prefix}-{self._counter}"
    
    def create_request(
        self,
        request_type: RequestType,
        namespace: str,
        details: dict,
        justification: str,
        requestor: str = "migration_agent",
    ) -> dict:
        """
        Create a new service request.
        
        Args:
            request_type: Type of request
            namespace: Target namespace
            details: Request-specific details
            justification: Business justification
            requestor: Who created the request
            
        Returns:
            Created request record
        """
        ticket_id = self._generate_ticket_id(request_type)
        lead_time = LEAD_TIMES.get(request_type, 7)
        
        now = datetime.now()
        estimated_completion = now + timedelta(days=lead_time)
        
        request = {
            "ticket_id": ticket_id,
            "request_type": request_type.value,
            "namespace": namespace,
            "details": details,
            "justification": justification,
            "requestor": requestor,
            "status": RequestStatus.SUBMITTED.value,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "estimated_completion": estimated_completion.strftime("%Y-%m-%d"),
            "lead_time_days": lead_time,
            "approvals": [],
            "notes": [],
        }
        
        self._requests[ticket_id] = request
        return request
    
    def get_request(self, ticket_id: str) -> Optional[dict]:
        """Get a request by ticket ID."""
        return self._requests.get(ticket_id)
    
    def update_status(
        self,
        ticket_id: str,
        new_status: RequestStatus,
        note: str = None,
    ) -> Optional[dict]:
        """
        Update request status.
        
        Args:
            ticket_id: Ticket to update
            new_status: New status
            note: Optional note
            
        Returns:
            Updated request or None if not found
        """
        request = self._requests.get(ticket_id)
        if not request:
            return None
        
        request["status"] = new_status.value
        request["updated_at"] = datetime.now().isoformat()
        
        if note:
            request["notes"].append({
                "timestamp": datetime.now().isoformat(),
                "note": note,
            })
        
        return request
    
    def list_requests(
        self,
        namespace: str = None,
        request_type: RequestType = None,
        status: RequestStatus = None,
    ) -> List[dict]:
        """
        List requests with optional filters.
        
        Args:
            namespace: Filter by namespace
            request_type: Filter by type
            status: Filter by status
            
        Returns:
            List of matching requests
        """
        results = []
        
        for request in self._requests.values():
            if namespace and request["namespace"] != namespace:
                continue
            if request_type and request["request_type"] != request_type.value:
                continue
            if status and request["status"] != status.value:
                continue
            results.append(request)
        
        # Sort by created_at descending
        results.sort(key=lambda x: x["created_at"], reverse=True)
        return results
    
    def get_open_requests(self, namespace: str = None) -> List[dict]:
        """Get all open (non-completed/cancelled/rejected) requests."""
        open_statuses = [
            RequestStatus.SUBMITTED.value,
            RequestStatus.PENDING_APPROVAL.value,
            RequestStatus.APPROVED.value,
            RequestStatus.IN_PROGRESS.value,
        ]
        
        results = []
        for request in self._requests.values():
            if request["status"] in open_statuses:
                if namespace is None or request["namespace"] == namespace:
                    results.append(request)
        
        return results
    
    def simulate_progress(self, ticket_id: str) -> Optional[dict]:
        """
        Simulate progress on a request (for demo purposes).
        
        Advances the request through the workflow stages.
        """
        request = self._requests.get(ticket_id)
        if not request:
            return None
        
        current_status = request["status"]
        
        # State machine for progression
        transitions = {
            RequestStatus.SUBMITTED.value: RequestStatus.PENDING_APPROVAL,
            RequestStatus.PENDING_APPROVAL.value: RequestStatus.APPROVED,
            RequestStatus.APPROVED.value: RequestStatus.IN_PROGRESS,
            RequestStatus.IN_PROGRESS.value: RequestStatus.COMPLETED,
        }
        
        next_status = transitions.get(current_status)
        if next_status:
            return self.update_status(
                ticket_id,
                next_status,
                f"Auto-progressed from {current_status}"
            )
        
        return request


# Global store instance
_store = None


def get_store() -> MockRequestStore:
    """Get the global mock request store."""
    global _store
    if _store is None:
        _store = MockRequestStore()
    return _store
