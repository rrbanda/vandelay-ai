"""
Agent Callbacks for Agentic RAG Loop
======================================

Implements before/after callbacks for state management:
- before_agent_call: Initialize state, log query
- after_agent_call: Update state, evaluate quality

These callbacks use CallbackContext to properly manage state
following ADK best practices.

ADK Callback Signature:
- before_agent_callback: (callback_context: CallbackContext) -> Optional[Content]
- after_agent_callback: (callback_context: CallbackContext) -> Optional[Content]

Reference: https://google.github.io/adk-docs/agents/callbacks/
"""

import json
import logging
from typing import Any, Dict, Optional

from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from .state_manager import (
    initialize_invocation_state,
    increment_iteration,
    get_iteration_count,
    get_retrieval_history,
    get_answer_quality,
    get_extracted_entities,
    update_answer_quality,
    TEMP_ITERATION_COUNT,
    SESSION_QUERY_COUNT,
)
from .config_loader import get_agentic_loop_config

logger = logging.getLogger(__name__)


def before_agent_call(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Called before each agent invocation.
    
    Updates state to track (session-scoped for ADK web UI visibility):
    - Query count (simple integer, visible in UI)
    
    Args:
        callback_context: The callback context with state access
        
    Returns:
        Optional Content to skip agent call (return None to proceed)
    """
    # Increment query count - use simple int (not JSON string)
    try:
        current_count = int(callback_context.state.get(SESSION_QUERY_COUNT) or 0)
    except (ValueError, TypeError):
        current_count = 0
    callback_context.state[SESSION_QUERY_COUNT] = current_count + 1
    
    # Initialize iteration count (temp-scoped, internal only)
    iteration = callback_context.state.get(TEMP_ITERATION_COUNT)
    if iteration is None:
        callback_context.state[TEMP_ITERATION_COUNT] = 0
    else:
        loop_config = get_agentic_loop_config()
        max_iterations = loop_config.get('max_iterations', 3)
        if iteration >= max_iterations:
            return types.Content(
                role="model",
                parts=[types.Part(text=(
                    "I've reached the maximum number of retrieval iterations. "
                    "Here's what I found based on available data."
                ))]
            )
        callback_context.state[TEMP_ITERATION_COUNT] = iteration + 1
    
    return None


def after_agent_call(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """
    Called after each agent invocation.
    
    Logs state summary for debugging.
    
    Args:
        callback_context: The callback context with state access
        
    Returns:
        Optional modified Content (return None to use original)
    """
    query_count = callback_context.state.get(SESSION_QUERY_COUNT, 0)
    iteration = callback_context.state.get(TEMP_ITERATION_COUNT, 0)
    
    logger.debug(f"After agent: query_count={query_count}, iteration={iteration}")
    
    return None


def create_tool_wrapper_with_state(tool_func, tool_name: str):
    """
    Create a wrapper for a tool function that tracks state.
    
    This enables automatic tracking of retrieval history.
    
    Args:
        tool_func: The original tool function
        tool_name: Name of the tool for state tracking
        
    Returns:
        Wrapped function that tracks state
    """
    from .state_manager import add_retrieval_to_history
    
    def wrapper(tool_context, *args, **kwargs):
        # Call original function
        result = tool_func(*args, **kwargs)
        
        # Track in state
        query = kwargs.get('query', str(args[0]) if args else '')
        add_retrieval_to_history(
            tool_context,
            tool_name=tool_name,
            query=query,
            results=result,
        )
        
        return result
    
    # Preserve function metadata
    wrapper.__name__ = tool_func.__name__
    wrapper.__doc__ = tool_func.__doc__
    
    return wrapper


# =============================================================================
# State-Aware Instruction Provider
# =============================================================================

async def dynamic_instruction_provider(context) -> str:
    """
    Dynamic instruction provider that injects state into instructions.
    
    This is an alternative to using {key} templating that gives
    more control over instruction generation.
    
    Args:
        context: ReadonlyContext from ADK
        
    Returns:
        Instruction string with state injected
    """
    from .config_loader import load_config
    
    config = load_config()
    base_instruction = config.get('orchestrator', {}).get('instruction', '')
    
    # Get state values
    iteration = context.state.get(TEMP_ITERATION_COUNT, 0)
    query_count = context.state.get(SESSION_QUERY_COUNT, 0)
    
    # Inject state into instruction
    state_context = f"""
## Current Context
- This is iteration {iteration} of the current query
- User has asked {query_count} total queries this session
"""
    
    return base_instruction + state_context
