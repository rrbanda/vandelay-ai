"""
State Manager for Agentic RAG Loop
====================================

Implements session state management for tracking:
- Retrieval history (for continuous query updating)
- Answer quality scores (for critic loop)
- Iteration count (for max iterations)
- Extracted entities (for follow-up queries)

Uses ADK's recommended state management patterns:
- CallbackContext.state for modifications
- Proper key prefixes (temp:, user:, app:)
- Event-driven state updates via callbacks

Reference: https://google.github.io/adk-docs/sessions/state/
"""

import json
from typing import Any, Dict, List, Optional

# Import context types from the correct modules
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.tool_context import ToolContext


# =============================================================================
# State Key Constants
# =============================================================================
# 
# State Prefixes and Persistence:
# - No prefix: Session-scoped (persists within session, shown in UI)
# - user: prefix: User-scoped (persists across sessions for same user)
# - app: prefix: App-scoped (persists across all users/sessions)
# - temp: prefix: Invocation-scoped (cleared after each invocation, NOT shown in UI)

# Temporary state (cleared after each invocation - NOT visible in ADK web UI)
TEMP_ITERATION_COUNT = "temp:iteration_count"
TEMP_NEEDS_FOLLOWUP = "temp:needs_followup"
TEMP_FOLLOWUP_QUERY = "temp:followup_query"

# Session state (persists within session - VISIBLE in ADK web UI)
SESSION_QUERY_COUNT = "query_count"
SESSION_LAST_QUERY = "last_query"
SESSION_LAST_ANSWER_SCORE = "last_answer_score"
SESSION_RETRIEVAL_HISTORY = "retrieval_history"
SESSION_CURRENT_QUERY = "current_query"
SESSION_EXTRACTED_ENTITIES = "extracted_entities"
SESSION_TOOLS_USED = "tools_used"

# User state (persists across sessions for same user)
USER_PREFERENCES = "user:preferences"
USER_NAME = "user:name"
USER_QUERY_HISTORY = "user:query_history"


# =============================================================================
# State Initialization
# =============================================================================

def initialize_invocation_state(context: CallbackContext, user_query: str) -> None:
    """
    Initialize state at the start of an invocation.
    
    Called in before_agent_call callback.
    Uses session-scoped keys for visibility in ADK web UI.
    
    Args:
        context: The callback context
        user_query: The user's query for this invocation
    """
    # Initialize temp state (not visible in UI)
    context.state[TEMP_ITERATION_COUNT] = 0
    context.state[TEMP_NEEDS_FOLLOWUP] = False
    context.state[TEMP_FOLLOWUP_QUERY] = ""
    
    # Initialize/update session state (VISIBLE in ADK web UI)
    if user_query:
        context.state[SESSION_LAST_QUERY] = user_query
        context.state[SESSION_CURRENT_QUERY] = user_query
    
    # Reset retrieval history for new query
    context.state[SESSION_RETRIEVAL_HISTORY] = json.dumps([])
    context.state[SESSION_EXTRACTED_ENTITIES] = json.dumps({})
    context.state[SESSION_TOOLS_USED] = json.dumps([])
    
    # Increment query count
    try:
        current_count = int(context.state.get(SESSION_QUERY_COUNT, 0) or 0)
    except (ValueError, TypeError):
        current_count = 0
    context.state[SESSION_QUERY_COUNT] = current_count + 1


# =============================================================================
# Retrieval History Management
# =============================================================================

def add_retrieval_to_history(
    context: ToolContext,
    tool_name: str,
    query: str,
    results: Any,
    score: Optional[int] = None,
) -> None:
    """
    Add a retrieval result to the history.
    
    Called from tool functions to track all retrievals.
    Uses session-scoped key for visibility in ADK web UI.
    
    Args:
        context: Tool context for state access
        tool_name: Name of the tool used
        query: The query that was executed
        results: The results from the tool
        score: Optional relevance score
    """
    # Get current history (session-scoped for UI visibility)
    history_json = context.state.get(SESSION_RETRIEVAL_HISTORY, "[]")
    try:
        history = json.loads(history_json)
    except json.JSONDecodeError:
        history = []
    
    # Add new entry
    entry = {
        "tool": tool_name,
        "query": query[:100],  # Truncate for UI
        "result_count": len(results) if isinstance(results, list) else 1,
        "has_error": bool(results.get("error")) if isinstance(results, dict) else False,
        "score": score,
    }
    history.append(entry)
    
    # Update state (session-scoped)
    context.state[SESSION_RETRIEVAL_HISTORY] = json.dumps(history)
    
    # Also track tools used
    tools_json = context.state.get(SESSION_TOOLS_USED, "[]")
    try:
        tools = json.loads(tools_json)
    except json.JSONDecodeError:
        tools = []
    if tool_name not in tools:
        tools.append(tool_name)
        context.state[SESSION_TOOLS_USED] = json.dumps(tools)


def get_retrieval_history(context: CallbackContext) -> List[Dict[str, Any]]:
    """Get the retrieval history for current session."""
    history_json = context.state.get(SESSION_RETRIEVAL_HISTORY, "[]")
    try:
        return json.loads(history_json)
    except json.JSONDecodeError:
        return []


# =============================================================================
# Iteration Tracking
# =============================================================================

def increment_iteration(context: CallbackContext) -> int:
    """
    Increment the iteration counter.
    
    Returns:
        Current iteration count after increment
    """
    count = context.state.get(TEMP_ITERATION_COUNT, 0)
    count += 1
    context.state[TEMP_ITERATION_COUNT] = count
    return count


def get_iteration_count(context: CallbackContext) -> int:
    """Get current iteration count."""
    return context.state.get(TEMP_ITERATION_COUNT, 0)


def should_continue_loop(context: CallbackContext, max_iterations: int = 3) -> bool:
    """
    Check if the agentic loop should continue.
    
    Args:
        context: Callback context
        max_iterations: Maximum allowed iterations
        
    Returns:
        True if more iterations are allowed
    """
    current = get_iteration_count(context)
    needs_followup = context.state.get(TEMP_NEEDS_FOLLOWUP, False)
    return current < max_iterations and needs_followup


# =============================================================================
# Answer Quality Tracking
# =============================================================================

def update_answer_quality(
    context: CallbackContext,
    score: int,
    needs_followup: bool = False,
    followup_query: str = "",
) -> None:
    """
    Update the answer quality assessment.
    
    Called after the Answer Critic evaluates results.
    Uses session-scoped key for visibility in ADK web UI.
    
    Args:
        context: Callback context
        score: Quality score (0-100)
        needs_followup: Whether follow-up queries are needed
        followup_query: Suggested follow-up query
    """
    # Session-scoped (visible in UI)
    context.state[SESSION_LAST_ANSWER_SCORE] = score
    
    # Temp-scoped (for internal loop control)
    context.state[TEMP_NEEDS_FOLLOWUP] = needs_followup
    context.state[TEMP_FOLLOWUP_QUERY] = followup_query


def get_answer_quality(context: CallbackContext) -> Dict[str, Any]:
    """Get current answer quality state."""
    return {
        "score": context.state.get(SESSION_LAST_ANSWER_SCORE, 0),
        "needs_followup": context.state.get(TEMP_NEEDS_FOLLOWUP, False),
        "followup_query": context.state.get(TEMP_FOLLOWUP_QUERY, ""),
    }


# =============================================================================
# Entity Extraction Tracking
# =============================================================================

def update_extracted_entities(
    context: CallbackContext,
    entities: Dict[str, List[str]],
) -> None:
    """
    Update extracted entities for continuous query updating.
    Uses session-scoped key for visibility in ADK web UI.
    
    Args:
        context: Callback context
        entities: Dict mapping entity type to list of names
    """
    # Merge with existing entities (session-scoped for UI visibility)
    existing_json = context.state.get(SESSION_EXTRACTED_ENTITIES, "{}")
    try:
        existing = json.loads(existing_json)
    except json.JSONDecodeError:
        existing = {}
    
    for entity_type, names in entities.items():
        if entity_type in existing:
            existing[entity_type] = list(set(existing[entity_type] + names))
        else:
            existing[entity_type] = names
    
    context.state[SESSION_EXTRACTED_ENTITIES] = json.dumps(existing)


def get_extracted_entities(context: CallbackContext) -> Dict[str, List[str]]:
    """Get all extracted entities for this session."""
    entities_json = context.state.get(SESSION_EXTRACTED_ENTITIES, "{}")
    try:
        return json.loads(entities_json)
    except json.JSONDecodeError:
        return {}


# =============================================================================
# Query Refinement
# =============================================================================

def update_current_query(context: CallbackContext, refined_query: str) -> None:
    """Update the current query after refinement."""
    context.state[SESSION_CURRENT_QUERY] = refined_query


def get_current_query(context: CallbackContext) -> str:
    """Get the current (possibly refined) query."""
    return context.state.get(SESSION_CURRENT_QUERY, "")


# =============================================================================
# State Summary for Instruction Injection
# =============================================================================

def get_state_summary_for_agent(context: CallbackContext) -> Dict[str, Any]:
    """
    Get a summary of current state for agent instruction injection.
    
    This can be used with ADK's {key} templating in instructions.
    
    Returns:
        Dict with key state values suitable for instruction injection
    """
    return {
        "iteration": get_iteration_count(context),
        "query": get_current_query(context),
        "retrieval_count": len(get_retrieval_history(context)),
        "quality_score": context.state.get(SESSION_LAST_ANSWER_SCORE, 0),
        "entities": get_extracted_entities(context),
        "needs_followup": context.state.get(TEMP_NEEDS_FOLLOWUP, False),
        "query_count": context.state.get(SESSION_QUERY_COUNT, 0),
    }
