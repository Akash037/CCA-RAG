"""
Advanced Memory Management System for RAG.

Handles multiple memory types:
- Session Memory: Current conversation context
- Short-term Memory: Recent interactions (Redis)
- Long-term Memory: User preferences & history (Database)
- Conversation Memory: Persistent chat history (Vertex AI Memory Corpus)
"""

import json
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from google.cloud import aiplatform

from ..core.config import settings
from ..core.logging import get_logger
from ..core.database import get_db_session, User, UserSession, Conversation, Message
from ..models.schemas import MemoryContext, UserResponse

logger = get_logger(__name__)


class SessionMemoryManager:
    """Manages session-level memory (current conversation context)."""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._session_timers: Dict[str, datetime] = {}
    
    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get current session context."""
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "conversation_history": [],
                "current_topic": None,
                "user_intent": None,
                "context_variables": {},
                "created_at": datetime.utcnow().isoformat()
            }
            self._session_timers[session_id] = datetime.utcnow()
        
        return self._sessions[session_id].copy()
    
    async def update_session_context(self, session_id: str, 
                                   context_update: Dict[str, Any]) -> None:
        """Update session context."""
        if session_id not in self._sessions:
            await self.get_session_context(session_id)
        
        self._sessions[session_id].update(context_update)
        self._session_timers[session_id] = datetime.utcnow()
        
        logger.info("Session context updated", 
                   session_id=session_id, 
                   context_keys=list(context_update.keys()))
    
    async def add_to_conversation_history(self, session_id: str, 
                                        role: str, content: str) -> None:
        """Add message to conversation history."""
        context = await self.get_session_context(session_id)
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        context["conversation_history"].append(message)
        
        # Keep only last N messages to prevent memory bloat
        max_history = settings.max_conversation_history
        if len(context["conversation_history"]) > max_history:
            context["conversation_history"] = context["conversation_history"][-max_history:]
        
        await self.update_session_context(session_id, context)
    
    async def clear_session(self, session_id: str) -> None:
        """Clear session memory."""
        if session_id in self._sessions:
            del self._sessions[session_id]
        if session_id in self._session_timers:
            del self._session_timers[session_id]
        
        logger.info("Session cleared", session_id=session_id)
    
    async def cleanup_expired_sessions(self) -> None:
        """Clean up expired sessions."""
        current_time = datetime.utcnow()
        timeout = timedelta(seconds=settings.session_timeout)
        
        expired_sessions = [
            session_id for session_id, last_activity in self._session_timers.items()
            if current_time - last_activity > timeout
        ]
        
        for session_id in expired_sessions:
            await self.clear_session(session_id)
        
        if expired_sessions:
            logger.info("Expired sessions cleaned up", count=len(expired_sessions))


class ShortTermMemoryManager:
    """Manages short-term memory using Redis."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(settings.redis_url)
            await self.redis_client.ping()
            logger.info("Connected to Redis for short-term memory")
        except Exception as e:
            logger.error("Failed to connect to Redis", error=str(e))
            self.redis_client = None
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")
    
    async def store_interaction(self, user_id: str, interaction_data: Dict[str, Any]) -> None:
        """Store user interaction in short-term memory."""
        if not self.redis_client:
            return
        
        key = f"short_term:{user_id}"
        interaction_data["timestamp"] = datetime.utcnow().isoformat()
        
        try:
            # Store as list of interactions
            await self.redis_client.lpush(key, json.dumps(interaction_data))
            
            # Keep only recent interactions
            await self.redis_client.ltrim(key, 0, 99)  # Keep last 100 interactions
            
            # Set TTL
            await self.redis_client.expire(key, settings.short_term_memory_ttl)
            
            logger.debug("Interaction stored in short-term memory", 
                        user_id=user_id, 
                        interaction_type=interaction_data.get("type"))
        except Exception as e:
            logger.error("Failed to store interaction", 
                        user_id=user_id, 
                        error=str(e))
    
    async def get_recent_interactions(self, user_id: str, 
                                    limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent user interactions."""
        if not self.redis_client:
            return []
        
        key = f"short_term:{user_id}"
        
        try:
            interactions = await self.redis_client.lrange(key, 0, limit - 1)
            return [json.loads(interaction) for interaction in interactions]
        except Exception as e:
            logger.error("Failed to get recent interactions", 
                        user_id=user_id, 
                        error=str(e))
            return []
    
    async def store_user_preferences(self, user_id: str, 
                                   preferences: Dict[str, Any]) -> None:
        """Store user preferences temporarily."""
        if not self.redis_client:
            return
        
        key = f"preferences:{user_id}"
        
        try:
            await self.redis_client.setex(
                key, 
                settings.short_term_memory_ttl, 
                json.dumps(preferences)
            )
            logger.debug("Preferences stored", user_id=user_id)
        except Exception as e:
            logger.error("Failed to store preferences", 
                        user_id=user_id, 
                        error=str(e))
    
    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user preferences from short-term memory."""
        if not self.redis_client:
            return {}
        
        key = f"preferences:{user_id}"
        
        try:
            preferences = await self.redis_client.get(key)
            return json.loads(preferences) if preferences else {}
        except Exception as e:
            logger.error("Failed to get preferences", 
                        user_id=user_id, 
                        error=str(e))
            return {}


class LongTermMemoryManager:
    """Manages long-term memory using database."""
    
    async def get_or_create_user(self, user_id: str, 
                               user_data: Optional[Dict[str, Any]] = None) -> UserResponse:
        """Get existing user or create new one."""
        async with get_db_session() as session:
            # Try to get existing user
            result = await session.execute(
                select(User).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                return UserResponse(
                    id=user.id,
                    user_id=user.user_id,
                    name=user.name,
                    email=user.email,
                    preferences=json.loads(user.preferences) if user.preferences else None,
                    created_at=user.created_at,
                    updated_at=user.updated_at
                )
            
            # Create new user
            new_user = User(
                user_id=user_id,
                name=user_data.get("name") if user_data else None,
                email=user_data.get("email") if user_data else None,
                preferences=json.dumps(user_data.get("preferences", {})) if user_data else None
            )
            
            session.add(new_user)
            await session.commit()
            await session.refresh(new_user)
            
            logger.info("New user created", user_id=user_id)
            
            return UserResponse(
                id=new_user.id,
                user_id=new_user.user_id,
                name=new_user.name,
                email=new_user.email,
                preferences=json.loads(new_user.preferences) if new_user.preferences else None,
                created_at=new_user.created_at,
                updated_at=new_user.updated_at
            )
    
    async def update_user_preferences(self, user_id: str, 
                                    preferences: Dict[str, Any]) -> None:
        """Update user preferences in database."""
        async with get_db_session() as session:
            await session.execute(
                update(User)
                .where(User.user_id == user_id)
                .values(
                    preferences=json.dumps(preferences),
                    updated_at=datetime.utcnow()
                )
            )
            await session.commit()
            
            logger.info("User preferences updated", user_id=user_id)
    
    async def get_conversation_history(self, user_id: str, 
                                     limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's conversation history."""
        async with get_db_session() as session:
            # Get recent conversations
            conversations_result = await session.execute(
                select(Conversation)
                .where(Conversation.user_id == user_id)
                .order_by(Conversation.updated_at.desc())
                .limit(10)  # Last 10 conversations
            )
            conversations = conversations_result.scalars().all()
            
            conversation_history = []
            
            for conversation in conversations:
                # Get messages for this conversation
                messages_result = await session.execute(
                    select(Message)
                    .where(Message.conversation_id == conversation.id)
                    .order_by(Message.created_at.asc())
                    .limit(limit)
                )
                messages = messages_result.scalars().all()
                
                conversation_data = {
                    "conversation_id": conversation.id,
                    "title": conversation.title,
                    "created_at": conversation.created_at.isoformat(),
                    "messages": [
                        {
                            "role": msg.role,
                            "content": msg.content,
                            "created_at": msg.created_at.isoformat(),
                            "metadata": json.loads(msg.message_metadata) if msg.message_metadata else None
                        }
                        for msg in messages
                    ]
                }
                conversation_history.append(conversation_data)
            
            return conversation_history


class ConversationMemoryManager:
    """Manages conversation memory using Vertex AI Memory Corpus."""
    
    def __init__(self):
        self.client = None
        self.memory_corpus_id = settings.rag_memory_corpus_id
    
    async def initialize(self) -> None:
        """Initialize Vertex AI client."""
        try:
            aiplatform.init(
                project=settings.google_cloud_project,
                location=settings.vertex_ai_location
            )
            self.client = aiplatform.gapic.ReasoningEngineServiceAsyncClient()
            logger.info("Vertex AI Memory Corpus client initialized")
        except Exception as e:
            logger.error("Failed to initialize Vertex AI client", error=str(e))
    
    async def store_conversation_memory(self, user_id: str, 
                                      conversation_data: Dict[str, Any]) -> None:
        """Store conversation in memory corpus."""
        if not self.client:
            return
        
        try:
            # Format memory data for Vertex AI
            memory_content = {
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "conversation": conversation_data
            }
            
            # Store in memory corpus
            # Note: This is a placeholder for the actual Vertex AI Memory API
            # The exact implementation will depend on the final API structure
            
            logger.debug("Conversation stored in memory corpus", user_id=user_id)
        except Exception as e:
            logger.error("Failed to store conversation memory", 
                        user_id=user_id, 
                        error=str(e))
    
    async def retrieve_relevant_memories(self, user_id: str, 
                                       query: str, 
                                       limit: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant memories from conversation corpus."""
        if not self.client:
            return []
        
        try:
            # Query memory corpus for relevant conversations
            # Note: This is a placeholder for the actual Vertex AI Memory API
            
            # For now, return empty list
            return []
        except Exception as e:
            logger.error("Failed to retrieve conversation memories", 
                        user_id=user_id, 
                        error=str(e))
            return []


class AdvancedMemoryManager:
    """Central memory manager coordinating all memory types."""
    
    def __init__(self):
        self.session_memory = SessionMemoryManager()
        self.short_term_memory = ShortTermMemoryManager()
        self.long_term_memory = LongTermMemoryManager()
        self.conversation_memory = ConversationMemoryManager()
    
    async def initialize(self) -> None:
        """Initialize all memory managers."""
        await self.short_term_memory.connect()
        await self.conversation_memory.initialize()
        logger.info("Advanced Memory Manager initialized")
    
    async def get_comprehensive_memory(self, session_id: str, 
                                     user_id: Optional[str] = None) -> MemoryContext:
        """Get comprehensive memory context for a query."""
        memory_context = MemoryContext()
        
        # Get session memory
        memory_context.session_memory = await self.session_memory.get_session_context(session_id)
        
        if user_id:
            # Get short-term memory
            recent_interactions = await self.short_term_memory.get_recent_interactions(user_id)
            user_preferences = await self.short_term_memory.get_user_preferences(user_id)
            
            memory_context.short_term_memory = {
                "recent_interactions": recent_interactions,
                "preferences": user_preferences
            }
            
            # Get long-term memory
            user_profile = await self.long_term_memory.get_or_create_user(user_id)
            conversation_history = await self.long_term_memory.get_conversation_history(user_id)
            
            memory_context.long_term_memory = {
                "user_profile": user_profile.dict(),
                "conversation_history": conversation_history
            }
            
            # Get conversation memory (relevant past conversations)
            # This would use the query to find relevant memories
            # memory_context.conversation_memory = await self.conversation_memory.retrieve_relevant_memories(
            #     user_id, query, limit=5
            # )
        
        return memory_context
    
    async def update_memory_after_interaction(self, session_id: str, 
                                            user_id: Optional[str],
                                            query: str, 
                                            response: str,
                                            metadata: Optional[Dict[str, Any]] = None) -> None:
        """Update all memory systems after an interaction."""
        # Update session memory
        await self.session_memory.add_to_conversation_history(session_id, "user", query)
        await self.session_memory.add_to_conversation_history(session_id, "assistant", response)
        
        if user_id:
            # Store interaction in short-term memory
            interaction_data = {
                "type": "query_response",
                "query": query,
                "response": response,
                "session_id": session_id,
                "metadata": metadata or {}
            }
            await self.short_term_memory.store_interaction(user_id, interaction_data)
            
            # Store in conversation memory corpus
            conversation_data = {
                "query": query,
                "response": response,
                "session_id": session_id,
                "metadata": metadata or {}
            }
            await self.conversation_memory.store_conversation_memory(user_id, conversation_data)
    
    async def cleanup(self) -> None:
        """Clean up memory systems."""
        await self.session_memory.cleanup_expired_sessions()
        await self.short_term_memory.disconnect()
        logger.info("Memory systems cleaned up")


# Global memory manager instance
memory_manager = AdvancedMemoryManager()
