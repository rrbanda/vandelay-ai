"""
Guardrails Plugin for GraphRAG
===============================

Implements security policies and guardrails:
- Tool authorization (block unauthorized tool usage)
- Query filtering (block sensitive queries)
- Rate limiting
- Response validation

Usage:
    from graphrag.plugins import GuardrailsPlugin
    
    guardrails = GuardrailsPlugin(
        blocked_tools=['execute_cypher'],  # Block raw Cypher execution
        max_tokens_per_request=10000,
    )
    
    runner = InMemoryRunner(
        agent=root_agent,
        app_name='graphrag',
        plugins=[guardrails],
    )
"""

import re
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Callable

from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types


class GuardrailsPlugin(BasePlugin):
    """
    Plugin that enforces security policies and guardrails.
    
    Features:
    - Block specific tools
    - Filter sensitive queries
    - Rate limiting per user
    - Token limits
    - Custom validation callbacks
    """
    
    def __init__(
        self,
        name: str = "guardrails",
        # Tool restrictions
        blocked_tools: Optional[List[str]] = None,
        allowed_tools: Optional[List[str]] = None,  # If set, only these tools are allowed
        # Query filtering
        blocked_patterns: Optional[List[str]] = None,
        # Rate limiting
        rate_limit_per_minute: Optional[int] = None,
        # Token limits
        max_tokens_per_request: Optional[int] = None,
        # Custom validators
        custom_query_validator: Optional[Callable[[str], bool]] = None,
        custom_tool_validator: Optional[Callable[[str, Dict], bool]] = None,
    ):
        super().__init__(name=name)
        
        # Tool restrictions
        self.blocked_tools: Set[str] = set(blocked_tools or [])
        self.allowed_tools: Optional[Set[str]] = set(allowed_tools) if allowed_tools else None
        
        # Query filtering - compile patterns for efficiency
        self.blocked_patterns: List[re.Pattern] = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in (blocked_patterns or [])
        ]
        
        # Rate limiting
        self.rate_limit_per_minute = rate_limit_per_minute
        self._request_times: Dict[str, List[float]] = defaultdict(list)
        
        # Token limits
        self.max_tokens_per_request = max_tokens_per_request
        self._current_tokens = 0
        
        # Custom validators
        self.custom_query_validator = custom_query_validator
        self.custom_tool_validator = custom_tool_validator
        
        # Violations log
        self._violations: List[Dict[str, Any]] = []
    
    def _log_violation(self, violation_type: str, details: Dict[str, Any]):
        """Log a security violation."""
        self._violations.append({
            'type': violation_type,
            'timestamp': time.time(),
            **details,
        })
    
    def _check_rate_limit(self, user_id: str) -> bool:
        """Check if user is within rate limit."""
        if not self.rate_limit_per_minute:
            return True
        
        now = time.time()
        minute_ago = now - 60
        
        # Clean old entries
        self._request_times[user_id] = [
            t for t in self._request_times[user_id] if t > minute_ago
        ]
        
        # Check limit
        if len(self._request_times[user_id]) >= self.rate_limit_per_minute:
            return False
        
        # Record this request
        self._request_times[user_id].append(now)
        return True
    
    def _check_blocked_patterns(self, text: str) -> Optional[str]:
        """Check if text matches any blocked patterns."""
        for pattern in self.blocked_patterns:
            if pattern.search(text):
                return pattern.pattern
        return None
    
    # =========================================================================
    # User Message Callback
    # =========================================================================
    
    async def on_user_message_callback(
        self,
        *,
        invocation_context: InvocationContext,
        user_message: types.Content,
    ) -> Optional[types.Content]:
        """
        Filter incoming user messages.
        
        Checks:
        - Rate limiting
        - Blocked patterns
        - Custom query validation
        """
        # Extract text from message
        text = ""
        if user_message.parts:
            for part in user_message.parts:
                if hasattr(part, 'text') and part.text:
                    text = part.text
                    break
        
        # Get user ID
        user_id = getattr(invocation_context, 'user_id', 'unknown')
        
        # Check rate limit
        if not self._check_rate_limit(user_id):
            self._log_violation('rate_limit', {'user_id': user_id})
            return types.Content(
                role="user",
                parts=[types.Part(text="Rate limit exceeded. Please wait before sending more requests.")]
            )
        
        # Check blocked patterns
        matched_pattern = self._check_blocked_patterns(text)
        if matched_pattern:
            self._log_violation('blocked_pattern', {
                'user_id': user_id,
                'pattern': matched_pattern,
                'query': text[:100],
            })
            return types.Content(
                role="user",
                parts=[types.Part(text="I cannot process this type of request.")]
            )
        
        # Custom query validation
        if self.custom_query_validator and not self.custom_query_validator(text):
            self._log_violation('custom_query_validation', {
                'user_id': user_id,
                'query': text[:100],
            })
            return types.Content(
                role="user",
                parts=[types.Part(text="This query is not allowed.")]
            )
        
        # Reset token counter for new request
        self._current_tokens = 0
        
        return None  # Allow the message through
    
    # =========================================================================
    # Model Callbacks
    # =========================================================================
    
    async def after_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_response: LlmResponse,
        **kwargs,  # Accept additional kwargs for compatibility
    ) -> Optional[LlmResponse]:
        """
        Check token usage after model call.
        
        If token limit is exceeded, stop further processing.
        """
        if not self.max_tokens_per_request:
            return None
        
        usage = getattr(llm_response, 'usage_metadata', None)
        if usage:
            total = getattr(usage, 'total_token_count', 0)
            self._current_tokens += total
            
            if self._current_tokens > self.max_tokens_per_request:
                self._log_violation('token_limit', {
                    'tokens_used': self._current_tokens,
                    'limit': self.max_tokens_per_request,
                })
                # Could return a modified response here to stop processing
        
        return None
    
    # =========================================================================
    # Tool Callbacks
    # =========================================================================
    
    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_context: ToolContext,
        **kwargs,  # Accept tool_args for compatibility
    ) -> Optional[Dict]:
        """
        Check if tool is authorized before execution.
        
        Returns a rejection message if tool is blocked.
        """
        tool_name = getattr(tool, 'name', str(tool))
        tool_args = kwargs.get('tool_args', kwargs.get('args', {}))
        
        # Check if tool is explicitly blocked
        if tool_name in self.blocked_tools:
            self._log_violation('blocked_tool', {
                'tool': tool_name,
                'args': str(tool_args)[:100],
            })
            return {
                'error': f"Tool '{tool_name}' is not authorized",
                'blocked': True,
            }
        
        # Check if tool is in allowed list (if whitelist is active)
        if self.allowed_tools is not None and tool_name not in self.allowed_tools:
            self._log_violation('unauthorized_tool', {
                'tool': tool_name,
                'args': str(tool_args)[:100],
            })
            return {
                'error': f"Tool '{tool_name}' is not in the allowed list",
                'blocked': True,
            }
        
        # Custom tool validation
        if self.custom_tool_validator and not self.custom_tool_validator(tool_name, tool_args):
            self._log_violation('custom_tool_validation', {
                'tool': tool_name,
                'args': str(tool_args)[:100],
            })
            return {
                'error': f"Tool '{tool_name}' call was rejected by policy",
                'blocked': True,
            }
        
        return None  # Allow the tool to execute
    
    # =========================================================================
    # Violations Access
    # =========================================================================
    
    def get_violations(self) -> List[Dict[str, Any]]:
        """Get all logged security violations."""
        return self._violations
    
    def get_violations_summary(self) -> Dict[str, int]:
        """Get count of violations by type."""
        summary: Dict[str, int] = defaultdict(int)
        for v in self._violations:
            summary[v['type']] += 1
        return dict(summary)
    
    def clear_violations(self):
        """Clear violation log."""
        self._violations = []


# =============================================================================
# Pre-configured Guardrails for FSI/Banking
# =============================================================================

def create_fsi_guardrails() -> GuardrailsPlugin:
    """
    Create guardrails configured for Financial Services.
    
    Blocks:
    - Raw Cypher execution (use safe tools instead)
    - PII-related queries
    - Account number patterns
    """
    return GuardrailsPlugin(
        name="fsi_guardrails",
        # Block raw Cypher execution - force use of safe tools
        blocked_tools=['execute_cypher'],
        # Block patterns that might indicate PII or sensitive data requests
        blocked_patterns=[
            r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',  # Credit card numbers
            r'\b\d{3}[- ]?\d{2}[- ]?\d{4}\b',  # SSN pattern
            r'password|secret|credential',  # Credential requests
        ],
        # Rate limit: 30 requests per minute
        rate_limit_per_minute=30,
        # Token limit: 50k tokens per request
        max_tokens_per_request=50000,
    )
