# Service Request Portal MCP Server

Mock MCP (Model Context Protocol) server for demonstrating infrastructure change request workflows during VMware to BareMetal OpenShift migrations.

## Overview

This server simulates a Service Request Portal that handles:
- **Firewall Rules**: New EgressIP whitelisting for internal system access
- **Certificates**: New certificates when cluster routes are in SAN list
- **DNS/Vanity URLs**: Creating or modifying Vanity URL mappings
- **SSO Configuration**: Registration with new SSO host
- **Operator Installation**: Redis, Couchbase, Service Mesh setup
- **Cleanup Requests**: Source cluster project deletion

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Migration Agent                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ MCP Protocol
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              Service Request Portal MCP Server              │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ submit_firewall │  │ submit_cert     │  ...             │
│  └─────────────────┘  └─────────────────┘                  │
│                              │                              │
│                              ▼                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              MockRequestStore                        │   │
│  │  - In-memory ticket storage                         │   │
│  │  - Status tracking                                  │   │
│  │  - Simulated workflows                              │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Available Tools

### submit_firewall_request
Submit a firewall rule request for new EgressIP whitelisting.

```python
{
    "namespace": "payments-api",
    "source_egress_ips": ["10.100.50.10", "10.100.50.11"],
    "destination_hosts": ["db.internal.example.com"],
    "destination_ports": ["5432"],
    "protocol": "TCP",
    "justification": "Migration to BareMetal OpenShift"
}
```

### submit_certificate_request
Submit a certificate request when cluster routes are in SAN list.

```python
{
    "namespace": "payments-api",
    "common_name": "payments.vandelay.com",
    "san_list": [
        "payments.vandelay.com",
        "payments-api.apps.baremetal-east-dev.vandelay.internal"
    ],
    "certificate_type": "server"
}
```

### submit_dns_request
Submit a DNS/Vanity URL request.

```python
{
    "namespace": "payments-api",
    "vanity_url": "payments.vandelay.com",
    "target_vip": "baremetal-east-dev-vip.vandelay.internal",
    "target_vip_ip": "10.100.1.10",
    "request_type": "create"
}
```

### submit_sso_request
Submit an SSO configuration request.

```python
{
    "namespace": "payments-api",
    "application_id": "APP-12345",
    "sso_provider": "modern_sso",
    "base_url": "https://payments.vandelay.com",
    "new_sso_host": "sso-east-dev.vandelay.internal",
    "request_type": "registration"
}
```

### submit_operator_request
Submit an operator installation request to Platform Ops.

```python
{
    "namespace": "payments-api",
    "operator_name": "redis",
    "operator_config": {
        "cpu": "4",
        "memory": "16Gi",
        "storage": "50Gi",
        "replicas": 3
    },
    "destination_cluster": "BAREMETAL-EAST-DEV"
}
```

### submit_cleanup_request
Submit a cleanup request to delete project from source cluster.

```python
{
    "namespace": "payments-api",
    "source_cluster": "VMWARE-EAST-DEV-1",
    "environment": "DEV",
    "confirmation": "I_CONFIRM_DELETION"
}
```

### check_request_status
Check the status of a service request.

```python
{
    "ticket_id": "FW-1001"
}
```

### list_open_requests
List all open service requests.

```python
{
    "namespace": "payments-api",  # optional
    "request_type": "firewall"    # optional
}
```

### simulate_approval
Simulate approval/progress on a request (demo only).

```python
{
    "ticket_id": "FW-1001"
}
```

## Usage

### Running the Server

```bash
# Install dependencies
pip install fastapi uvicorn

# Run the server
python -m mcp_servers.service_request.server --port 8080
```

### Using Programmatically

```python
from mcp_servers.service_request.server import call_tool

# Submit a firewall request
result = call_tool("submit_firewall_request", {
    "namespace": "payments-api",
    "source_egress_ips": ["10.100.50.10"],
    "destination_hosts": ["db.internal.example.com"],
    "destination_ports": ["5432"],
})

print(result)
# {
#     "success": True,
#     "ticket_id": "FW-1001",
#     "status": "submitted",
#     "message": "Firewall request submitted. Estimated completion: 2026-02-02",
#     "lead_time_days": 14,
#     ...
# }
```

### HTTP API

```bash
# List available tools
curl http://localhost:8080/tools

# Submit a request
curl -X POST http://localhost:8080/tools/submit_firewall_request \
  -H "Content-Type: application/json" \
  -d '{
    "namespace": "payments-api",
    "source_egress_ips": ["10.100.50.10"],
    "destination_hosts": ["db.internal.example.com"],
    "destination_ports": ["5432"]
  }'

# Check status
curl -X POST http://localhost:8080/tools/check_request_status \
  -H "Content-Type: application/json" \
  -d '{"ticket_id": "FW-1001"}'
```

## Lead Times

| Request Type | Lead Time |
|--------------|-----------|
| Firewall     | 14 days   |
| Certificate  | 7 days    |
| DNS          | 3 days    |
| SSO          | 7 days    |
| Operator     | 5 days    |
| Cleanup      | 3 days    |

## Request Lifecycle

```
submitted → pending_approval → approved → in_progress → completed
                                    ↓
                                rejected
```

## Production Integration

This is a **mock implementation** for demonstration. For production:

1. Replace `MockRequestStore` with actual API calls to your Change Management Platform
2. Implement proper authentication (OAuth, API keys, etc.)
3. Add audit logging
4. Integrate with your ticketing system (ServiceNow, Jira, etc.)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SERVICE_REQUEST_PORT` | Server port | 8080 |
| `SERVICE_REQUEST_HOST` | Server host | 0.0.0.0 |
