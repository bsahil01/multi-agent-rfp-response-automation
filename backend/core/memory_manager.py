"""
Memory manager for agent conversations with Drizzle ORM persistence
Provides buffer memory with database backup for chat sessions
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain.memory import ConversationBufferWindowMemory

from .db.client import drizzle_client

logger = logging.getLogger(__name__)


class AgentMemoryManager:
    """Manages agent conversation memory with Drizzle ORM persistence"""
    
    def __init__(self, window_size: int = 10, max_messages: int = 100):
        self.window_size = window_size
        self.max_messages = max_messages
        self.memory_cache: Dict[str, ConversationBufferWindowMemory] = {}
        self.last_sync: Dict[str, datetime] = {}
    
    def get_memory(self, session_id: str) -> ConversationBufferWindowMemory:
        """Get or create memory for a session"""
        if session_id not in self.memory_cache:
            memory = ConversationBufferWindowMemory(
                k=self.window_size,
                return_messages=True,
                human_prefix="User",
                ai_prefix="Assistant"
            )
            self.memory_cache[session_id] = memory
            
            # Load existing messages from database
            self._load_messages_from_db(session_id, memory)
        
        return self.memory_cache[session_id]
    
    async def add_user_message(self, session_id: str, message: str) -> bool:
        """Add user message to memory and save to database"""
        memory = self.get_memory(session_id)
        
        # Add to LangChain memory
        memory.chat_memory.add_user_message(message)
        
        # Save to database using Drizzle
        success = await drizzle_client.save_chat_message(
            session_id=session_id,
            message_type="user",
            content=message
        )
        
        # Sync session state
        await self._sync_session_state(session_id, memory)
        
        return success
    
    async def add_ai_message(self, session_id: str, message: str, metadata: Dict[str, Any] = None) -> bool:
        """Add AI message to memory and save to database"""
        memory = self.get_memory(session_id)
        
        # Add to LangChain memory
        memory.chat_memory.add_ai_message(message)
        
        # Save to database with metadata using Drizzle
        success = await drizzle_client.save_chat_message(
            session_id=session_id,
            message_type="assistant",
            content=message,
            metadata=metadata or {}
        )
        
        # Sync session state
        await self._sync_session_state(session_id, memory)
        
        return success
    
    def get_messages(self, session_id: str) -> List[BaseMessage]:
        """Get all messages for a session"""
        memory = self.get_memory(session_id)
        return memory.chat_memory.messages
    
    def get_recent_messages(self, session_id: str, limit: int = 5) -> List[BaseMessage]:
        """Get recent messages within the window"""
        memory = self.get_memory(session_id)
        all_messages = memory.chat_memory.messages
        return all_messages[-limit:] if len(all_messages) > limit else all_messages
    
    def clear_memory(self, session_id: str) -> bool:
        """Clear memory for a session"""
        if session_id in self.memory_cache:
            del self.memory_cache[session_id]
        if session_id in self.last_sync:
            del self.last_sync[session_id]
        return True
    
    async def save_agent_state(self, session_id: str, state: Dict[str, Any]) -> bool:
        """Save complete agent state to database using Drizzle"""
        # Save to database
        success = await drizzle_client.save_chat_session(session_id, state)
        
        if success:
            self.last_sync[session_id] = datetime.utcnow()
        
        return success
    
    async def load_agent_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Load agent state from database using Drizzle"""
        return await drizzle_client.load_chat_session(session_id)
    
    async def log_agent_interaction(self, session_id: str, agent_name: str, 
                                   input_data: Any, output_data: Any, 
                                   reasoning: str = "", tool_calls: List = None) -> bool:
        """Log detailed agent interaction using Drizzle"""
        interaction_data = {
            "type": "agent_response",
            "input": self._serialize_data(input_data),
            "output": self._serialize_data(output_data),
            "reasoning": reasoning,
            "tool_calls": tool_calls or []
        }
        
        return await drizzle_client.save_agent_interaction(
            session_id=session_id,
            agent_name=agent_name,
            interaction_data=interaction_data
        )
    
    async def _load_messages_from_db(self, session_id: str, memory: ConversationBufferWindowMemory):
        """Load existing messages from database into memory"""
        try:
            messages = await drizzle_client.get_chat_messages(session_id, limit=self.max_messages)
            
            # Clear existing memory
            memory.chat_memory.clear()
            
            # Add messages in chronological order
            for msg in reversed(messages):  # Reverse to get oldest first
                if msg["message_type"] == "user":
                    memory.chat_memory.add_user_message(msg["content"])
                else:
                    memory.chat_memory.add_ai_message(msg["content"])
            
            logger.info(f"Loaded {len(messages)} messages for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error loading messages from DB: {e}")
    
    async def _sync_session_state(self, session_id: str, memory: ConversationBufferWindowMemory):
        """Sync session state with database"""
        # Only sync if it's been more than 30 seconds since last sync
        last_sync = self.last_sync.get(session_id)
        if not last_sync or datetime.utcnow() - last_sync > timedelta(seconds=30):
            # Create basic state from memory
            state = {
                "messages": [],  # Messages handled separately
                "current_step": "IDLE",
                "session_id": session_id
            }
            
            await self.save_agent_state(session_id, state)
    
    def _serialize_data(self, data: Any) -> Any:
        """Serialize data for database storage"""
        try:
            if hasattr(data, 'dict'):
                return data.dict()
            elif isinstance(data, (dict, list, str, int, float, bool)):
                return data
            else:
                return str(data)
        except Exception:
            return str(data)
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a session"""
        memory = self.get_memory(session_id)
        messages = memory.chat_memory.messages
        
        user_messages = [m for m in messages if isinstance(m, HumanMessage)]
        ai_messages = [m for m in messages if isinstance(m, AIMessage)]
        
        return {
            "session_id": session_id,
            "total_messages": len(messages),
            "user_messages": len(user_messages),
            "ai_messages": len(ai_messages),
            "window_size": self.window_size,
            "last_sync": self.last_sync.get(session_id, None),
            "database_available": drizzle_client.is_available()
        }
    
    async def cleanup_old_sessions(self, days_old: int = 7):
        """Clean up old sessions from cache"""
        cutoff = datetime.utcnow() - timedelta(days=days_old)
        
        sessions_to_remove = []
        for session_id, last_sync in self.last_sync.items():
            if last_sync and last_sync < cutoff:
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            self.clear_memory(session_id)
        
        logger.info(f"Cleaned up {len(sessions_to_remove)} old sessions")


# Global memory manager instance
memory_manager = AgentMemoryManager()
