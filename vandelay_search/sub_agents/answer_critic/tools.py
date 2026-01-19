"""
Answer Critic Tools
====================

Tools for evaluating answer quality and generating follow-ups.
All configuration loaded from config.yaml.
"""

import json
from typing import Any, Dict, List

from ...config_loader import get_critic_thresholds, get_routing_hints


def evaluate_completeness(
    question: str,
    retrieval_results: str,
    result_count: int = 0,
) -> Dict[str, Any]:
    """
    Quick heuristic evaluation of answer completeness.
    
    This is a fast check before calling the full LLM-based critic.
    Returns a preliminary score based on simple heuristics.
    
    Args:
        question: The original user question
        retrieval_results: JSON string of retrieval results
        result_count: Number of results retrieved
        
    Returns:
        Dict with preliminary_score, needs_full_evaluation, suggested_tools
    """
    thresholds = get_critic_thresholds()
    routing_hints = get_routing_hints()
    
    # Parse results
    try:
        results = json.loads(retrieval_results) if isinstance(retrieval_results, str) else retrieval_results
    except json.JSONDecodeError:
        results = []
    
    # Count actual results
    if isinstance(results, list):
        actual_count = len([r for r in results if r and not r.get('error')])
    else:
        actual_count = 1 if results and not results.get('error') else 0
    
    # Quick scoring heuristics
    score = 0
    
    # Has results?
    if actual_count > 0:
        score += 40
    
    # Multiple results for list-type questions?
    question_lower = question.lower()
    if any(word in question_lower for word in ['all', 'list', 'what are', 'show me']):
        if actual_count >= 3:
            score += 20
        elif actual_count >= 1:
            score += 10
    else:
        # Single result is fine for specific questions
        if actual_count >= 1:
            score += 20
    
    # Check keyword overlap
    result_str = json.dumps(results).lower() if results else ""
    keywords = [w for w in question_lower.split() if len(w) > 3]
    keyword_matches = sum(1 for kw in keywords if kw in result_str)
    if keywords:
        keyword_ratio = keyword_matches / len(keywords)
        score += int(keyword_ratio * 30)
    
    # Suggest tools based on question keywords
    suggested_tools = []
    for keyword, tool in routing_hints.items():
        if keyword in question_lower:
            suggested_tools.append(tool)
    
    # Determine if we need full LLM evaluation
    needs_full_eval = thresholds['retry'] <= score < thresholds['complete']
    
    return {
        "preliminary_score": score,
        "result_count": actual_count,
        "needs_full_evaluation": needs_full_eval,
        "quick_recommendation": (
            "complete" if score >= thresholds['complete'] else
            "retry" if score >= thresholds['retry'] else
            "insufficient"
        ),
        "suggested_tools": list(set(suggested_tools))[:3],
    }


def format_for_synthesis(
    question: str,
    retrievals: List[Dict[str, Any]],
    synthesis_notes: str = "",
) -> str:
    """
    Format retrieval results for final answer synthesis.
    
    Args:
        question: Original question
        retrievals: List of retrieval results
        synthesis_notes: Notes from the critic on how to synthesize
        
    Returns:
        Formatted string for the synthesis prompt
    """
    output = [f"Question: {question}", "", "Retrieved Information:"]
    
    for i, r in enumerate(retrievals, 1):
        output.append(f"\n--- Source {i} ({r.get('tool', 'unknown')}) ---")
        
        result = r.get('result', {})
        if isinstance(result, list):
            for item in result[:5]:  # Limit to 5 items per source
                output.append(json.dumps(item, indent=2, default=str))
        else:
            output.append(json.dumps(result, indent=2, default=str))
    
    if synthesis_notes:
        output.append(f"\nSynthesis Notes: {synthesis_notes}")
    
    return "\n".join(output)


def extract_entities_from_results(results: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """
    Extract entity names from retrieval results.
    
    Used for Continuous Query Updating - helps reference
    entities in follow-up queries.
    
    Args:
        results: List of retrieval results
        
    Returns:
        Dict mapping entity type to list of names
    """
    entities = {
        "products": [],
        "regulations": [],
        "portfolios": [],
        "counterparties": [],
    }
    
    for r in results:
        data = r.get('result', [])
        if not isinstance(data, list):
            data = [data] if data else []
        
        for item in data:
            if not isinstance(item, dict):
                continue
            
            # Extract by common field names
            if name := item.get('name') or item.get('product'):
                if 'category' in item or 'apy' in item or 'apr' in item:
                    entities['products'].append(name)
                elif 'regulation' in str(item).lower():
                    entities['regulations'].append(name)
                elif 'portfolio' in str(item).lower() or 'risk_score' in item:
                    entities['portfolios'].append(name)
            
            if name := item.get('regulation'):
                entities['regulations'].append(name)
            
            if name := item.get('counterparty'):
                entities['counterparties'].append(name)
    
    # Deduplicate
    return {k: list(set(v)) for k, v in entities.items() if v}


# Export tools
CRITIC_TOOLS = [
    evaluate_completeness,
    format_for_synthesis,
    extract_entities_from_results,
]
