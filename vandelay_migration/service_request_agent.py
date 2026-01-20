"""
Service Request Agent - MCP Server Integration
===============================================

Handles infrastructure change requests via the Service Request Portal (MCP):
- Firewall rule requests (14 day lead time)
- Certificate requests (7 day lead time)
- DNS/Vanity URL requests (3 day lead time)
- SSO registration requests (7 day lead time)
- Operator installation requests (5 day lead time)
- Source cluster cleanup requests (3 day lead time)

This is the KEY EXTENSION of the migration agent - integrating with
enterprise change management systems.
"""

from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types

from .config_loader import load_config, get_llm_config

# Import only service request tools (MCP)
from .migration_tools import (
    submit_firewall_request,
    submit_certificate_request,
    submit_dns_request,
    submit_sso_request,
    submit_operator_request,
    submit_cleanup_request,
    check_request_status,
    list_open_requests,
)


# Load configuration
config = load_config()
llm_config = get_llm_config(config)
agent_config = config.get('sub_agents', {}).get('service_request', {})

# Default instruction if not in config
DEFAULT_INSTRUCTION = '''
You help developers submit and track infrastructure change requests.

## Request Types & Lead Times

| Request | Lead Time | When Needed |
|---------|-----------|-------------|
| Firewall | 14 days | New egress IP needs whitelisting |
| Certificate | 7 days | Only if cluster routes in certificate SAN |
| DNS | 3 days | Vanity URL pointing to new cluster VIP |
| SSO | 7 days | App registration with new SSO host |
| Operator | 5 days | Redis, Couchbase, Service Mesh on new cluster |
| Cleanup | 3 days | Delete old namespace (IRREVERSIBLE) |

## Before Submitting

- Confirm all required details with the developer
- Warn about lead times
- For cleanup: REQUIRE explicit confirmation

## After Submitting

- Provide the ticket ID
- Explain next steps
- Remind them to plan for the lead time

## Style

- Be helpful but cautious with destructive operations
- Always confirm namespace before submitting
- Provide ticket IDs clearly
'''

# Service request tools list (MCP integration)
SERVICE_REQUEST_TOOLS = [
    submit_firewall_request,
    submit_certificate_request,
    submit_dns_request,
    submit_sso_request,
    submit_operator_request,
    submit_cleanup_request,
    check_request_status,
    list_open_requests,
]

# Create the service request agent
service_request_agent = Agent(
    name=agent_config.get('name', 'service_request_agent'),
    model=LiteLlm(
        model=llm_config['model'],
        api_base=llm_config['api_base'],
        api_key=llm_config['api_key'],
    ),
    instruction=agent_config.get('instruction', DEFAULT_INSTRUCTION),
    description=agent_config.get('description',
        'Submits infrastructure requests on behalf of developers and tracks ticket status'
    ),
    tools=SERVICE_REQUEST_TOOLS,
    output_key="service_request_response",
    generate_content_config=types.GenerateContentConfig(
        temperature=llm_config.get('temperature', 0.1)
    ),
)
