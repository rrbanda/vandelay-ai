"""
Metrics Plugin for GraphRAG
============================

Collects execution metrics including:
- Token usage (prompt/response)
- Execution times
- Tool invocation counts
- Error counts

Usage:
    from graphrag.plugins import MetricsPlugin
    
    metrics = MetricsPlugin()
    runner = InMemoryRunner(
        agent=root_agent,
        app_name='graphrag',
        plugins=[metrics],
    )
    
    # After running queries...
    print(metrics.get_summary())
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types


@dataclass
class InvocationMetrics:
    """Metrics for a single invocation."""
    start_time: float = 0.0
    end_time: float = 0.0
    prompt_tokens: int = 0
    response_tokens: int = 0
    cached_tokens: int = 0
    llm_calls: int = 0
    tool_calls: int = 0
    agent_calls: int = 0
    errors: int = 0
    tools_used: List[str] = field(default_factory=list)
    agents_used: List[str] = field(default_factory=list)
    
    @property
    def duration(self) -> float:
        return self.end_time - self.start_time if self.end_time else 0.0
    
    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.response_tokens


class MetricsPlugin(BasePlugin):
    """
    Plugin that collects execution metrics.
    
    Tracks:
    - Token usage per invocation
    - Execution time
    - Tool/agent invocation counts
    - Error rates
    """
    
    def __init__(self, name: str = "metrics"):
        super().__init__(name=name)
        self._current: Optional[InvocationMetrics] = None
        self._history: List[InvocationMetrics] = []
        self._tool_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {'calls': 0, 'errors': 0, 'total_time': 0.0}
        )
        self._agent_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {'calls': 0, 'total_time': 0.0}
        )
        self._start_times: Dict[str, float] = {}
    
    # =========================================================================
    # Runner Callbacks
    # =========================================================================
    
    async def before_run_callback(
        self,
        *,
        invocation_context: InvocationContext,
    ) -> Optional[types.Content]:
        """Start tracking new invocation."""
        self._current = InvocationMetrics(start_time=time.time())
        return None
    
    async def after_run_callback(
        self,
        *,
        invocation_context: InvocationContext,
    ) -> None:
        """Finalize and store invocation metrics."""
        if self._current:
            self._current.end_time = time.time()
            self._history.append(self._current)
            self._current = None
    
    # =========================================================================
    # Agent Callbacks
    # =========================================================================
    
    async def before_agent_callback(
        self,
        *,
        agent: BaseAgent,
        callback_context: CallbackContext,
    ) -> None:
        """Track agent invocation."""
        if self._current:
            agent_name = getattr(agent, 'name', 'unknown')
            self._current.agent_calls += 1
            self._current.agents_used.append(agent_name)
            self._start_times[f'agent_{agent_name}'] = time.time()
    
    async def after_agent_callback(
        self,
        *,
        agent: BaseAgent,
        callback_context: CallbackContext,
    ) -> None:
        """Record agent timing."""
        agent_name = getattr(agent, 'name', 'unknown')
        start_key = f'agent_{agent_name}'
        if start_key in self._start_times:
            duration = time.time() - self._start_times[start_key]
            self._agent_stats[agent_name]['calls'] += 1
            self._agent_stats[agent_name]['total_time'] += duration
    
    # =========================================================================
    # Model Callbacks
    # =========================================================================
    
    async def before_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
    ) -> Optional[LlmResponse]:
        """Track LLM call."""
        if self._current:
            self._current.llm_calls += 1
        return None
    
    async def after_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_response: LlmResponse,
        **kwargs,  # Accept additional kwargs for compatibility
    ) -> Optional[LlmResponse]:
        """Extract and record token usage."""
        if self._current:
            usage = getattr(llm_response, 'usage_metadata', None)
            if usage:
                self._current.prompt_tokens += getattr(usage, 'prompt_token_count', 0)
                self._current.response_tokens += getattr(usage, 'candidates_token_count', 0)
                self._current.cached_tokens += getattr(usage, 'cached_content_token_count', 0)
        return None
    
    async def on_model_error_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
        error: Exception,
    ) -> Optional[LlmResponse]:
        """Track LLM errors."""
        if self._current:
            self._current.errors += 1
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
        """Track tool invocation."""
        tool_name = getattr(tool, 'name', str(tool))
        if self._current:
            self._current.tool_calls += 1
            self._current.tools_used.append(tool_name)
        self._start_times[f'tool_{tool_name}'] = time.time()
        return None
    
    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_context: ToolContext,
        **kwargs,  # Accept tool_args, tool_result/result for compatibility
    ) -> Optional[Dict]:
        """Record tool timing."""
        tool_name = getattr(tool, 'name', str(tool))
        start_key = f'tool_{tool_name}'
        if start_key in self._start_times:
            duration = time.time() - self._start_times[start_key]
            self._tool_stats[tool_name]['calls'] += 1
            self._tool_stats[tool_name]['total_time'] += duration
        return None
    
    async def on_tool_error_callback(
        self,
        *,
        tool: BaseTool,
        tool_context: ToolContext,
        error: Exception,
        **kwargs,  # Accept tool_args for compatibility
    ) -> Optional[Dict]:
        """Track tool errors."""
        tool_name = getattr(tool, 'name', str(tool))
        self._tool_stats[tool_name]['errors'] += 1
        if self._current:
            self._current.errors += 1
        return None
    
    # =========================================================================
    # Metrics Access Methods
    # =========================================================================
    
    def get_current(self) -> Optional[InvocationMetrics]:
        """Get current invocation metrics (during run)."""
        return self._current
    
    def get_history(self) -> List[InvocationMetrics]:
        """Get all completed invocation metrics."""
        return self._history
    
    def get_last(self) -> Optional[InvocationMetrics]:
        """Get metrics from last invocation."""
        return self._history[-1] if self._history else None
    
    def get_tool_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get aggregated tool statistics."""
        return dict(self._tool_stats)
    
    def get_agent_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get aggregated agent statistics."""
        return dict(self._agent_stats)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        total_invocations = len(self._history)
        
        if not self._history:
            return {
                'invocations': 0,
                'total_tokens': 0,
                'avg_duration': 0,
                'tools': {},
                'agents': {},
            }
        
        total_tokens = sum(m.total_tokens for m in self._history)
        total_duration = sum(m.duration for m in self._history)
        total_errors = sum(m.errors for m in self._history)
        
        return {
            'invocations': total_invocations,
            'total_tokens': total_tokens,
            'avg_tokens_per_invocation': total_tokens / total_invocations,
            'total_duration': total_duration,
            'avg_duration': total_duration / total_invocations,
            'total_errors': total_errors,
            'error_rate': total_errors / total_invocations if total_invocations else 0,
            'tools': {
                name: {
                    'calls': stats['calls'],
                    'errors': stats['errors'],
                    'avg_time': stats['total_time'] / stats['calls'] if stats['calls'] else 0,
                }
                for name, stats in self._tool_stats.items()
            },
            'agents': {
                name: {
                    'calls': stats['calls'],
                    'avg_time': stats['total_time'] / stats['calls'] if stats['calls'] else 0,
                }
                for name, stats in self._agent_stats.items()
            },
        }
    
    def reset(self):
        """Reset all metrics."""
        self._current = None
        self._history = []
        self._tool_stats = defaultdict(
            lambda: {'calls': 0, 'errors': 0, 'total_time': 0.0}
        )
        self._agent_stats = defaultdict(
            lambda: {'calls': 0, 'total_time': 0.0}
        )
        self._start_times = {}
