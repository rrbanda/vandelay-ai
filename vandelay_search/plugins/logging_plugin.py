"""
Logging Plugin for GraphRAG
============================

Provides detailed logging of agent, tool, and LLM activity for 
debugging and observability.

Usage:
    from graphrag.plugins import LoggingPlugin
    
    runner = InMemoryRunner(
        agent=root_agent,
        app_name='graphrag',
        plugins=[LoggingPlugin(verbose=True)],
    )
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

logger = logging.getLogger(__name__)


class LoggingPlugin(BasePlugin):
    """
    Plugin that logs all agent workflow activity.
    
    Logs:
    - User messages
    - Agent invocations
    - LLM requests and responses
    - Tool calls and results
    - Events
    - Errors
    """
    
    def __init__(
        self,
        name: str = "logging",
        verbose: bool = False,
        log_llm_requests: bool = True,
        log_tool_args: bool = True,
        log_events: bool = False,
    ):
        super().__init__(name=name)
        self.verbose = verbose
        self.log_llm_requests = log_llm_requests
        self.log_tool_args = log_tool_args
        self.log_events = log_events
        self._start_times: Dict[str, float] = {}
    
    def _log(self, level: str, message: str, **kwargs):
        """Log with consistent formatting."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        prefix = f"[{timestamp}] [{self.name}]"
        
        if self.verbose:
            print(f"{prefix} {message}")
        
        log_func = getattr(logger, level.lower(), logger.info)
        log_func(f"{prefix} {message}", extra=kwargs)
    
    # =========================================================================
    # User Message Callback
    # =========================================================================
    
    async def on_user_message_callback(
        self,
        *,
        invocation_context: InvocationContext,
        user_message: types.Content,
    ) -> Optional[types.Content]:
        """Log incoming user message."""
        text = ""
        if user_message.parts:
            for part in user_message.parts:
                if hasattr(part, 'text') and part.text:
                    text = part.text[:100]
                    break
        
        self._log("info", f"📥 USER MESSAGE: {text}")
        self._start_times['run'] = time.time()
        return None  # Don't modify the message
    
    # =========================================================================
    # Runner Callbacks
    # =========================================================================
    
    async def before_run_callback(
        self,
        *,
        invocation_context: InvocationContext,
    ) -> Optional[types.Content]:
        """Log runner start."""
        self._log("info", "🚀 RUNNER STARTED")
        return None
    
    async def after_run_callback(
        self,
        *,
        invocation_context: InvocationContext,
    ) -> None:
        """Log runner completion with timing."""
        duration = time.time() - self._start_times.get('run', time.time())
        self._log("info", f" RUNNER COMPLETED in {duration:.2f}s")
    
    # =========================================================================
    # Agent Callbacks
    # =========================================================================
    
    async def before_agent_callback(
        self,
        *,
        agent: BaseAgent,
        callback_context: CallbackContext,
    ) -> None:
        """Log agent invocation."""
        agent_name = getattr(agent, 'name', 'unknown')
        self._log("info", f"🤖 AGENT START: {agent_name}")
        self._start_times[f'agent_{agent_name}'] = time.time()
    
    async def after_agent_callback(
        self,
        *,
        agent: BaseAgent,
        callback_context: CallbackContext,
    ) -> None:
        """Log agent completion."""
        agent_name = getattr(agent, 'name', 'unknown')
        start_key = f'agent_{agent_name}'
        duration = time.time() - self._start_times.get(start_key, time.time())
        self._log("info", f"🤖 AGENT END: {agent_name} ({duration:.2f}s)")
    
    # =========================================================================
    # Model Callbacks
    # =========================================================================
    
    async def before_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
    ) -> Optional[LlmResponse]:
        """Log LLM request."""
        if self.log_llm_requests:
            model = getattr(llm_request, 'model', 'unknown')
            self._log("info", f"🧠 LLM REQUEST: model={model}")
        self._start_times['llm'] = time.time()
        return None
    
    async def after_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_response: LlmResponse,
        **kwargs,  # Accept additional kwargs for compatibility
    ) -> Optional[LlmResponse]:
        """Log LLM response with token usage."""
        duration = time.time() - self._start_times.get('llm', time.time())
        
        # Extract token usage if available
        usage = getattr(llm_response, 'usage_metadata', None)
        if usage:
            prompt_tokens = getattr(usage, 'prompt_token_count', 0)
            response_tokens = getattr(usage, 'candidates_token_count', 0)
            self._log(
                "info",
                f"🧠 LLM RESPONSE: {prompt_tokens}+{response_tokens} tokens ({duration:.2f}s)"
            )
        else:
            self._log("info", f"🧠 LLM RESPONSE: ({duration:.2f}s)")
        
        return None
    
    async def on_model_error_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
        error: Exception,
    ) -> Optional[LlmResponse]:
        """Log LLM errors."""
        self._log("error", f"❌ LLM ERROR: {type(error).__name__}: {error}")
        return None  # Let the error propagate
    
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
        """Log tool invocation."""
        tool_name = getattr(tool, 'name', str(tool))
        tool_args = kwargs.get('tool_args', kwargs.get('args', {}))
        
        if self.log_tool_args:
            args_str = str(tool_args)[:100]
            self._log("info", f"🔧 TOOL CALL: {tool_name}({args_str})")
        else:
            self._log("info", f"🔧 TOOL CALL: {tool_name}")
        
        self._start_times[f'tool_{tool_name}'] = time.time()
        return None
    
    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_context: ToolContext,
        **kwargs,  # Accept tool_args, tool_result/result for compatibility
    ) -> Optional[Dict]:
        """Log tool result."""
        tool_name = getattr(tool, 'name', str(tool))
        start_key = f'tool_{tool_name}'
        duration = time.time() - self._start_times.get(start_key, time.time())
        
        # Get result (might be 'tool_result' or 'result' depending on ADK version)
        tool_result = kwargs.get('tool_result') or kwargs.get('result')
        
        # Summarize result
        if isinstance(tool_result, dict):
            result_summary = f"{len(tool_result)} keys"
        elif isinstance(tool_result, list):
            result_summary = f"{len(tool_result)} items"
        else:
            result_summary = str(tool_result)[:50]
        
        self._log("info", f"🔧 TOOL RESULT: {tool_name} → {result_summary} ({duration:.2f}s)")
        return None
    
    async def on_tool_error_callback(
        self,
        *,
        tool: BaseTool,
        tool_context: ToolContext,
        error: Exception,
        **kwargs,  # Accept tool_args for compatibility
    ) -> Optional[Dict]:
        """Log tool errors."""
        tool_name = getattr(tool, 'name', str(tool))
        self._log("error", f"❌ TOOL ERROR: {tool_name}: {type(error).__name__}: {error}")
        return None  # Let the error propagate
    
    # =========================================================================
    # Event Callback
    # =========================================================================
    
    async def on_event_callback(
        self,
        *,
        invocation_context: InvocationContext,
        event: Event,
    ) -> Optional[Event]:
        """Log events."""
        if self.log_events:
            author = getattr(event, 'author', 'unknown')
            is_final = event.is_final_response() if hasattr(event, 'is_final_response') else False
            
            self._log("debug", f"📤 EVENT: author={author}, final={is_final}")
        
        return None
