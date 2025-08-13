"""Unit tests for memory manager functionality."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from app.services.memory_manager import (
    SessionMemoryManager,
    ShortTermMemoryManager,
    LongTermMemoryManager,
    AdvancedMemoryManager
)
from app.models.schemas import MemoryContext


class TestSessionMemoryManager:
    """Test session memory manager."""
    
    @pytest.fixture
    def session_manager(self):
        """Create session memory manager instance."""
        return SessionMemoryManager()
    
    def test_session_creation(self, session_manager):
        """Test session creation."""
        session_id = "test_session_123"
        
        # Create session
        session_manager.create_session(session_id)
        
        # Check session exists
        assert session_id in session_manager.sessions
        assert "conversation_history" in session_manager.sessions[session_id]
        assert "current_topic" in session_manager.sessions[session_id]
        assert "user_preferences" in session_manager.sessions[session_id]
    
    def test_add_message(self, session_manager):
        """Test adding message to session."""
        session_id = "test_session_123"
        session_manager.create_session(session_id)
        
        # Add message
        session_manager.add_message(session_id, "user", "Hello!")
        
        # Check message was added
        history = session_manager.sessions[session_id]["conversation_history"]
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello!"
        assert "timestamp" in history[0]
    
    def test_get_session_context(self, session_manager):
        """Test getting session context."""
        session_id = "test_session_123"
        session_manager.create_session(session_id)
        session_manager.add_message(session_id, "user", "Hello!")
        
        context = session_manager.get_session_context(session_id)
        
        assert "conversation_history" in context
        assert len(context["conversation_history"]) == 1
    
    def test_session_cleanup(self, session_manager):
        """Test session cleanup."""
        session_id = "test_session_123"
        session_manager.create_session(session_id)
        
        # Clear session
        session_manager.clear_session(session_id)
        
        # Check session was removed
        assert session_id not in session_manager.sessions


class TestShortTermMemoryManager:
    """Test short-term memory manager."""
    
    @pytest.fixture
    def redis_mock(self):
        """Mock Redis client."""
        mock = AsyncMock()
        mock.get.return_value = None
        mock.set.return_value = True
        mock.delete.return_value = True
        mock.keys.return_value = []
        return mock
    
    @pytest.fixture
    def short_term_manager(self, redis_mock):
        """Create short-term memory manager with mocked Redis."""
        manager = ShortTermMemoryManager()
        manager.redis = redis_mock
        manager.initialized = True
        return manager
    
    @pytest.mark.asyncio
    async def test_store_interaction(self, short_term_manager, redis_mock):
        """Test storing interaction."""
        user_id = "test_user_123"
        interaction_data = {
            "query": "Test query",
            "response": "Test response",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await short_term_manager.store_interaction(user_id, interaction_data)
        
        # Check Redis was called
        assert redis_mock.set.called
    
    @pytest.mark.asyncio
    async def test_get_recent_interactions(self, short_term_manager, redis_mock):
        """Test getting recent interactions."""
        user_id = "test_user_123"
        
        # Mock Redis response
        redis_mock.get.return_value = '{"recent_interactions": []}'
        
        interactions = await short_term_manager.get_recent_interactions(user_id)
        
        assert interactions is not None
        assert redis_mock.get.called


class TestLongTermMemoryManager:
    """Test long-term memory manager."""
    
    @pytest.fixture
    def db_mock(self):
        """Mock database session."""
        mock = AsyncMock()
        return mock
    
    @pytest.fixture
    def long_term_manager(self, db_mock):
        """Create long-term memory manager with mocked database."""
        manager = LongTermMemoryManager()
        manager.database = MagicMock()
        manager.database.get_session.return_value.__aenter__.return_value = db_mock
        manager.initialized = True
        return manager
    
    @pytest.mark.asyncio
    async def test_get_user_profile(self, long_term_manager, db_mock):
        """Test getting user profile."""
        user_id = "test_user_123"
        
        # Mock database response
        db_mock.execute.return_value.fetchone.return_value = None
        
        profile = await long_term_manager.get_user_profile(user_id)
        
        assert profile is not None
        assert db_mock.execute.called
    
    @pytest.mark.asyncio
    async def test_store_conversation_summary(self, long_term_manager, db_mock):
        """Test storing conversation summary."""
        user_id = "test_user_123"
        session_id = "test_session_123"
        summary = "Test conversation summary"
        
        await long_term_manager.store_conversation_summary(user_id, session_id, summary)
        
        assert db_mock.execute.called


class TestAdvancedMemoryManager:
    """Test advanced memory manager coordination."""
    
    @pytest.fixture
    def mock_managers(self):
        """Mock sub-managers."""
        session_manager = MagicMock()
        short_term_manager = AsyncMock()
        long_term_manager = AsyncMock()
        conversation_manager = AsyncMock()
        
        session_manager.get_session_context.return_value = {"conversation_history": []}
        short_term_manager.get_recent_interactions.return_value = []
        long_term_manager.get_user_profile.return_value = {}
        conversation_manager.get_conversation_memory.return_value = {}
        
        return {
            "session": session_manager,
            "short_term": short_term_manager,
            "long_term": long_term_manager,
            "conversation": conversation_manager
        }
    
    @pytest.fixture
    def advanced_manager(self, mock_managers):
        """Create advanced memory manager with mocked sub-managers."""
        manager = AdvancedMemoryManager()
        manager.session_memory = mock_managers["session"]
        manager.short_term_memory = mock_managers["short_term"]
        manager.long_term_memory = mock_managers["long_term"]
        manager.conversation_memory = mock_managers["conversation"]
        manager.initialized = True
        return manager
    
    @pytest.mark.asyncio
    async def test_get_comprehensive_memory(self, advanced_manager, mock_managers):
        """Test getting comprehensive memory context."""
        session_id = "test_session_123"
        user_id = "test_user_123"
        
        context = await advanced_manager.get_comprehensive_memory(session_id, user_id)
        
        assert isinstance(context, MemoryContext)
        assert context.session_memory is not None
        assert context.short_term_memory is not None
        assert context.long_term_memory is not None
        assert context.conversation_memory is not None
        
        # Check that all sub-managers were called
        mock_managers["session"].get_session_context.assert_called_with(session_id)
        mock_managers["short_term"].get_recent_interactions.assert_called_with(user_id)
        mock_managers["long_term"].get_user_profile.assert_called_with(user_id)
        mock_managers["conversation"].get_conversation_memory.assert_called_with(session_id)
    
    @pytest.mark.asyncio
    async def test_update_memory_after_interaction(self, advanced_manager, mock_managers):
        """Test updating memory after user interaction."""
        session_id = "test_session_123"
        user_id = "test_user_123"
        query = "Test query"
        response = "Test response"
        metadata = {"test": "data"}
        
        await advanced_manager.update_memory_after_interaction(
            session_id, user_id, query, response, metadata
        )
        
        # Check that all update methods were called
        mock_managers["session"].add_message.assert_called()
        mock_managers["short_term"].store_interaction.assert_called()
        mock_managers["long_term"].update_user_activity.assert_called()
        mock_managers["conversation"].add_interaction.assert_called()
