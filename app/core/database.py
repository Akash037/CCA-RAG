"""
Database models and session management.
"""

from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, Text, Float, Integer, Boolean, func
from sqlmodel import Field, SQLModel

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# ========================
# User Models
# ========================

class User(SQLModel, table=True):
    """User model for tracking user interactions and preferences."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True, unique=True, description="External user ID")
    name: Optional[str] = Field(default=None, description="User display name")
    email: Optional[str] = Field(default=None, description="User email")
    preferences: Optional[str] = Field(default=None, description="JSON-encoded user preferences")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserSession(SQLModel, table=True):
    """User session model for tracking active sessions."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, unique=True, description="Session identifier")
    user_id: str = Field(index=True, description="User identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True, description="Session active status")


# ========================
# Conversation Models
# ========================

class Conversation(SQLModel, table=True):
    """Conversation model for tracking chat sessions."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, description="Session identifier")
    user_id: str = Field(index=True, description="User identifier")
    title: Optional[str] = Field(default=None, description="Conversation title")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Message(SQLModel, table=True):
    """Message model for individual conversation messages."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id", index=True)
    role: str = Field(description="Message role: user, assistant, system")
    content: str = Field(description="Message content")
    metadata: Optional[str] = Field(default=None, description="JSON-encoded metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ========================
# RAG & Memory Models
# ========================

class QueryLog(SQLModel, table=True):
    """Query log model for tracking RAG queries and responses."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True, description="Session identifier")
    user_id: Optional[str] = Field(default=None, index=True, description="User identifier")
    query: str = Field(description="User query")
    response: str = Field(description="Generated response")
    sources: Optional[str] = Field(default=None, description="JSON-encoded source documents")
    confidence_score: Optional[float] = Field(default=None, description="Response confidence")
    processing_time: Optional[float] = Field(default=None, description="Processing time in seconds")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserFeedback(SQLModel, table=True):
    """User feedback model for tracking response quality."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    query_log_id: int = Field(foreign_key="querylog.id", index=True)
    user_id: str = Field(index=True, description="User identifier")
    rating: int = Field(description="Rating 1-5")
    feedback_text: Optional[str] = Field(default=None, description="Feedback comment")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentSync(SQLModel, table=True):
    """Document sync model for tracking Google Drive synchronization."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    document_id: str = Field(index=True, unique=True, description="Google Drive document ID")
    file_name: str = Field(description="Document file name")
    file_type: str = Field(description="Document type")
    last_modified: datetime = Field(description="Last modification time")
    sync_status: str = Field(description="Sync status: pending, synced, error")
    corpus_id: Optional[str] = Field(default=None, description="RAG corpus ID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ========================
# Database Engine & Session
# ========================

class DatabaseManager:
    """Database manager for handling connections and sessions."""
    
    def __init__(self):
        self.engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_recycle=300,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session with proper cleanup."""
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def create_tables(self):
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Database tables created successfully")
    
    async def close(self):
        """Close database connections."""
        await self.engine.dispose()
        logger.info("Database connections closed")


# Global database manager
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database sessions in FastAPI."""
    async with db_manager.get_session() as session:
        yield session
