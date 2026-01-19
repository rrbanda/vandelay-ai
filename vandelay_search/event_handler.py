"""
Event Handler for GraphRAG
===========================

Events are the fundamental units of information flow in ADK.
They represent every significant occurrence during agent interaction.

Event Types:
- User Input: author='user', content with text
- Agent Response: author='AgentName', content with text
- Tool Call Request: content with function_call
- Tool Result: content with function_response
- State/Artifact Update: actions with state_delta/artifact_delta
- Control Signal: actions with transfer_to_agent/escalate

Reference: https://google.github.io/adk-docs/events/
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

# Setup logging
logger = logging.getLogger(__name__)


@dataclass
class EventSummary:
    """Summary of an event for logging/debugging."""
    event_id: str
    invocation_id: str
    author: str
    event_type: str
    timestamp: float
    content_preview: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict] = None
    tool_result: Optional[Any] = None
    state_changes: Optional[Dict] = None
    is_final: bool = False
    is_partial: bool = False
    error: Optional[str] = None


def classify_event(event) -> str:
    """
    Classify an event by its type.
    
    Returns one of:
    - 'user_input'
    - 'tool_call'
    - 'tool_result'
    - 'text_response'
    - 'streaming_chunk'
    - 'state_update'
    - 'control_signal'
    - 'error'
    - 'unknown'
    """
    # Check for errors
    if hasattr(event, 'error_code') and event.error_code:
        return 'error'
    
    # Check author
    author = getattr(event, 'author', None)
    if author == 'user':
        return 'user_input'
    
    # Check content
    content = getattr(event, 'content', None)
    if content and hasattr(content, 'parts') and content.parts:
        # Check for function calls
        if hasattr(event, 'get_function_calls'):
            calls = event.get_function_calls()
            if calls:
                return 'tool_call'
        
        # Check for function responses
        if hasattr(event, 'get_function_responses'):
            responses = event.get_function_responses()
            if responses:
                return 'tool_result'
        
        # Check for text
        for part in content.parts:
            if hasattr(part, 'text') and part.text:
                if getattr(event, 'partial', False):
                    return 'streaming_chunk'
                return 'text_response'
    
    # Check for actions
    actions = getattr(event, 'actions', None)
    if actions:
        if hasattr(actions, 'transfer_to_agent') and actions.transfer_to_agent:
            return 'control_signal'
        if hasattr(actions, 'escalate') and actions.escalate:
            return 'control_signal'
        if hasattr(actions, 'state_delta') and actions.state_delta:
            return 'state_update'
        if hasattr(actions, 'artifact_delta') and actions.artifact_delta:
            return 'state_update'
    
    return 'unknown'


def summarize_event(event) -> EventSummary:
    """
    Create a summary of an event for logging/debugging.
    """
    event_type = classify_event(event)
    
    summary = EventSummary(
        event_id=getattr(event, 'id', 'unknown'),
        invocation_id=getattr(event, 'invocation_id', 'unknown'),
        author=getattr(event, 'author', 'unknown'),
        event_type=event_type,
        timestamp=getattr(event, 'timestamp', datetime.now().timestamp()),
        is_partial=getattr(event, 'partial', False),
        is_final=event.is_final_response() if hasattr(event, 'is_final_response') else False,
    )
    
    # Extract content preview
    content = getattr(event, 'content', None)
    if content and hasattr(content, 'parts') and content.parts:
        for part in content.parts:
            if hasattr(part, 'text') and part.text:
                text = part.text
                summary.content_preview = text[:100] + '...' if len(text) > 100 else text
                break
    
    # Extract tool call info
    if event_type == 'tool_call' and hasattr(event, 'get_function_calls'):
        calls = event.get_function_calls()
        if calls:
            summary.tool_name = calls[0].name
            summary.tool_args = dict(calls[0].args) if calls[0].args else {}
    
    # Extract tool result info
    if event_type == 'tool_result' and hasattr(event, 'get_function_responses'):
        responses = event.get_function_responses()
        if responses:
            summary.tool_name = responses[0].name
            result = responses[0].response
            # Truncate large results
            if isinstance(result, dict):
                summary.tool_result = {k: str(v)[:50] for k, v in list(result.items())[:3]}
            else:
                summary.tool_result = str(result)[:100]
    
    # Extract state changes
    actions = getattr(event, 'actions', None)
    if actions and hasattr(actions, 'state_delta') and actions.state_delta:
        summary.state_changes = dict(actions.state_delta)
    
    # Extract error info
    if event_type == 'error':
        summary.error = getattr(event, 'error_message', 'Unknown error')
    
    return summary


def format_event_log(summary: EventSummary) -> str:
    """Format an event summary as a log line."""
    parts = [
        f"[{summary.event_type.upper()}]",
        f"author={summary.author}",
    ]
    
    if summary.content_preview:
        parts.append(f'text="{summary.content_preview}"')
    
    if summary.tool_name:
        parts.append(f"tool={summary.tool_name}")
    
    if summary.tool_args:
        args_str = json.dumps(summary.tool_args)[:50]
        parts.append(f"args={args_str}")
    
    if summary.tool_result:
        parts.append(f"result={summary.tool_result}")
    
    if summary.state_changes:
        parts.append(f"state_delta={summary.state_changes}")
    
    if summary.is_final:
        parts.append("[FINAL]")
    
    if summary.error:
        parts.append(f"error={summary.error}")
    
    return " | ".join(parts)


class EventLogger:
    """
    Event logger for debugging and observability.
    
    Usage:
        event_logger = EventLogger(verbose=True)
        
        async for event in runner.run_async(...):
            event_logger.log(event)
            if event.is_final_response():
                # Process final response
    """
    
    def __init__(
        self,
        verbose: bool = False,
        log_function_calls: bool = True,
        log_state_changes: bool = True,
        log_streaming: bool = False,
    ):
        self.verbose = verbose
        self.log_function_calls = log_function_calls
        self.log_state_changes = log_state_changes
        self.log_streaming = log_streaming
        self.events: List[EventSummary] = []
    
    def log(self, event) -> EventSummary:
        """Log an event and return its summary."""
        summary = summarize_event(event)
        self.events.append(summary)
        
        # Skip streaming chunks unless enabled
        if summary.event_type == 'streaming_chunk' and not self.log_streaming:
            return summary
        
        # Log based on settings
        if self.verbose:
            log_line = format_event_log(summary)
            logger.info(log_line)
            print(f"EVENT: {log_line}")
        elif summary.event_type == 'tool_call' and self.log_function_calls:
            print(f"  → Calling {summary.tool_name}({summary.tool_args})")
        elif summary.event_type == 'tool_result' and self.log_function_calls:
            print(f"  ← {summary.tool_name} returned")
        elif summary.event_type == 'state_update' and self.log_state_changes:
            print(f"  ⚡ State updated: {summary.state_changes}")
        elif summary.is_final and summary.content_preview:
            print(f"  ✓ Final: {summary.content_preview}")
        
        return summary
    
    def get_tool_calls(self) -> List[EventSummary]:
        """Get all tool call events."""
        return [e for e in self.events if e.event_type == 'tool_call']
    
    def get_final_responses(self) -> List[EventSummary]:
        """Get all final response events."""
        return [e for e in self.events if e.is_final]
    
    def get_state_changes(self) -> Dict[str, Any]:
        """Get aggregated state changes from all events."""
        changes = {}
        for event in self.events:
            if event.state_changes:
                changes.update(event.state_changes)
        return changes
    
    def get_errors(self) -> List[EventSummary]:
        """Get all error events."""
        return [e for e in self.events if e.event_type == 'error']
    
    def summary(self) -> Dict[str, Any]:
        """Get a summary of all logged events."""
        return {
            'total_events': len(self.events),
            'tool_calls': len(self.get_tool_calls()),
            'final_responses': len(self.get_final_responses()),
            'errors': len(self.get_errors()),
            'state_changes': self.get_state_changes(),
            'tools_used': list(set(e.tool_name for e in self.events if e.tool_name)),
        }
    
    def clear(self):
        """Clear logged events."""
        self.events = []


# =============================================================================
# Event Processor for Agentic Loop
# =============================================================================

class AgenticEventProcessor:
    """
    Process events for the Agentic RAG loop.
    
    Tracks:
    - Retrieval operations (which tools were called)
    - Answer quality (from critic responses)
    - Iteration count
    - Final responses
    
    Usage:
        processor = AgenticEventProcessor()
        
        async for event in runner.run_async(...):
            processor.process(event)
            
            if processor.should_stop():
                break
        
        print(processor.get_response())
    """
    
    def __init__(self, max_iterations: int = 3, min_quality_score: int = 80):
        self.max_iterations = max_iterations
        self.min_quality_score = min_quality_score
        self.reset()
    
    def reset(self):
        """Reset processor state for a new query."""
        self.iteration_count = 0
        self.retrieval_results = []
        self.quality_score = 0
        self.final_response = ""
        self.tools_called = []
        self.errors = []
        self._current_tool_call = None
    
    def process(self, event) -> None:
        """Process an event and update internal state."""
        event_type = classify_event(event)
        
        if event_type == 'tool_call':
            self._handle_tool_call(event)
        elif event_type == 'tool_result':
            self._handle_tool_result(event)
        elif event_type == 'text_response':
            self._handle_text_response(event)
        elif event_type == 'error':
            self._handle_error(event)
    
    def _handle_tool_call(self, event):
        """Handle tool call event."""
        if hasattr(event, 'get_function_calls'):
            calls = event.get_function_calls()
            if calls:
                tool_name = calls[0].name
                tool_args = dict(calls[0].args) if calls[0].args else {}
                self._current_tool_call = {
                    'name': tool_name,
                    'args': tool_args,
                }
                self.tools_called.append(tool_name)
                
                # Track iteration for retriever tools
                if tool_name in ['vector_search', 'graph_query', 'cypher_expert']:
                    self.iteration_count += 1
    
    def _handle_tool_result(self, event):
        """Handle tool result event."""
        if hasattr(event, 'get_function_responses'):
            responses = event.get_function_responses()
            if responses:
                result = responses[0].response
                tool_name = responses[0].name
                
                # Store retrieval result
                if tool_name in ['vector_search', 'graph_query', 'cypher_expert']:
                    self.retrieval_results.append({
                        'tool': tool_name,
                        'result': result,
                    })
                
                # Extract quality score from critic
                if tool_name == 'answer_critic' and isinstance(result, dict):
                    if 'completeness_score' in result:
                        self.quality_score = result['completeness_score']
    
    def _handle_text_response(self, event):
        """Handle text response event."""
        if hasattr(event, 'is_final_response') and event.is_final_response():
            content = getattr(event, 'content', None)
            if content and hasattr(content, 'parts') and content.parts:
                for part in content.parts:
                    if hasattr(part, 'text') and part.text:
                        self.final_response = part.text
                        break
    
    def _handle_error(self, event):
        """Handle error event."""
        error_msg = getattr(event, 'error_message', 'Unknown error')
        self.errors.append(error_msg)
    
    def should_stop(self) -> bool:
        """
        Determine if the agentic loop should stop.
        
        Stop conditions:
        - Max iterations reached
        - Quality score >= min threshold
        - Errors occurred
        """
        if self.errors:
            return True
        if self.iteration_count >= self.max_iterations:
            return True
        if self.quality_score >= self.min_quality_score:
            return True
        return False
    
    def get_response(self) -> str:
        """Get the final response text."""
        return self.final_response
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the processing."""
        return {
            'iterations': self.iteration_count,
            'quality_score': self.quality_score,
            'tools_called': self.tools_called,
            'retrieval_count': len(self.retrieval_results),
            'errors': self.errors,
            'stopped_reason': self._get_stop_reason(),
        }
    
    def _get_stop_reason(self) -> str:
        """Get the reason for stopping."""
        if self.errors:
            return 'error'
        if self.quality_score >= self.min_quality_score:
            return 'quality_threshold_met'
        if self.iteration_count >= self.max_iterations:
            return 'max_iterations_reached'
        return 'in_progress'


# =============================================================================
# Helper functions for common event operations
# =============================================================================

def extract_text_from_event(event) -> Optional[str]:
    """Extract text content from an event."""
    content = getattr(event, 'content', None)
    if content and hasattr(content, 'parts') and content.parts:
        for part in content.parts:
            if hasattr(part, 'text') and part.text:
                return part.text
    return None


def extract_tool_calls_from_event(event) -> List[Dict[str, Any]]:
    """Extract tool call information from an event."""
    if hasattr(event, 'get_function_calls'):
        calls = event.get_function_calls()
        if calls:
            return [
                {'name': call.name, 'args': dict(call.args) if call.args else {}}
                for call in calls
            ]
    return []


def extract_tool_results_from_event(event) -> List[Dict[str, Any]]:
    """Extract tool result information from an event."""
    if hasattr(event, 'get_function_responses'):
        responses = event.get_function_responses()
        if responses:
            return [
                {'name': resp.name, 'result': resp.response}
                for resp in responses
            ]
    return []


def is_retrieval_event(event) -> bool:
    """Check if event is a retrieval operation (vector search or graph query)."""
    tool_calls = extract_tool_calls_from_event(event)
    retrieval_tools = {'vector_search', 'graph_query', 'cypher_expert', 
                       'vector_search_agent', 'graph_query_agent', 'cypher_expert_agent'}
    return any(call['name'] in retrieval_tools for call in tool_calls)


def is_critic_event(event) -> bool:
    """Check if event is an answer critic operation."""
    tool_calls = extract_tool_calls_from_event(event)
    return any(call['name'] in {'answer_critic', 'answer_critic_agent'} for call in tool_calls)
