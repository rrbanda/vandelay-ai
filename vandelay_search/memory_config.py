"""
Memory Configuration for GraphRAG
===================================

Implements Long-Term Knowledge storage using ADK MemoryService.

Using InMemoryMemoryService since we use LlamaStack (not Vertex AI).
For persistent memory in production, consider:
- Redis-backed custom implementation
- PostgreSQL with pgvector
- Neo4j as a memory store (since we already have Neo4j)

Key Operations:
- add_session_to_memory: Ingest completed sessions into long-term storage
- search_memory: Query past conversations and knowledge

Reference: https://google.github.io/adk-docs/sessions/memory/
"""

from google.adk.memory import InMemoryMemoryService

# Try to import memory tools
try:
    from google.adk.tools import load_memory
    from google.adk.tools.preload_memory_tool import PreloadMemoryTool
    HAS_MEMORY_TOOLS = True
except ImportError:
    HAS_MEMORY_TOOLS = False
    load_memory = None
    PreloadMemoryTool = None


def get_memory_service():
    """
    Get the memory service.
    
    Currently uses InMemoryMemoryService (no persistence across restarts).
    For production, implement a persistent backend using Neo4j or Redis.
        
    Returns:
        Memory service instance
    """
    return InMemoryMemoryService()


def get_memory_tools():
    """
    Get memory tools for the agent.
    
    Returns:
        List of memory tools (load_memory, PreloadMemoryTool)
    """
    tools = []
    
    if HAS_MEMORY_TOOLS:
        if load_memory:
            tools.append(load_memory)
        # Note: PreloadMemoryTool is added differently (as a tool instance)
    
    return tools


def get_preload_memory_tool():
    """
    Get the PreloadMemoryTool for automatic memory retrieval.
    
    This tool retrieves relevant memories at the start of each turn.
    
    Returns:
        PreloadMemoryTool instance or None
    """
    if HAS_MEMORY_TOOLS and PreloadMemoryTool:
        return PreloadMemoryTool()
    return None


# =============================================================================
# Memory-aware callback for auto-saving sessions
# =============================================================================

async def auto_save_session_to_memory(callback_context):
    """
    Callback to automatically save session to memory after each interaction.
    
    This extracts meaningful information from the conversation and
    stores it in long-term memory for future retrieval.
    
    Usage:
        agent = Agent(
            ...
            after_agent_callback=auto_save_session_to_memory,
        )
    """
    try:
        invocation_context = callback_context._invocation_context
        if invocation_context.memory_service:
            await invocation_context.memory_service.add_session_to_memory(
                invocation_context.session
            )
    except Exception as e:
        # Don't fail the request if memory save fails
        print(f"Warning: Failed to save session to memory: {e}")
    
    return None


# =============================================================================
# Custom Memory Search Tool
# =============================================================================

def create_memory_search_tool(memory_service):
    """
    Create a custom memory search tool that uses a specific memory service.
    
    This allows searching across past conversations for relevant context.
    
    Args:
        memory_service: The memory service to search
        
    Returns:
        A function that can be used as an ADK tool
    """
    async def search_past_conversations(
        query: str,
        max_results: int = 5,
    ) -> dict:
        """
        Search past conversations for relevant information.
        
        Use this when the user asks about something that might have been
        discussed in previous conversations.
        
        Args:
            query: The search query (e.g., "previous discussion about mortgages")
            max_results: Maximum number of results to return
            
        Returns:
            Dict containing relevant memories from past conversations
        """
        try:
            # Search the memory service
            results = await memory_service.search_memory(query=query)
            
            # Format results
            memories = []
            for memory in results.memories[:max_results]:
                if memory.content:
                    memory_text = ""
                    for part in memory.content.parts:
                        if hasattr(part, 'text'):
                            memory_text += part.text
                    memories.append({
                        "content": memory_text,
                        "timestamp": getattr(memory, 'timestamp', None),
                    })
            
            return {
                "query": query,
                "found": len(memories),
                "memories": memories,
            }
        except Exception as e:
            return {
                "query": query,
                "error": str(e),
                "memories": [],
            }
    
    return search_past_conversations
