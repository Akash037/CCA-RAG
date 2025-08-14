"""
Pydantic models for API request/response schemas.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, validator


# ========================
# Enums
# ========================

class MessageRole(str, Enum):
    """Message role enumeration."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class QueryType(str, Enum):
    """Query type enumeration."""
    FACTUAL = "factual"
    CONVERSATIONAL = "conversational"
    ANALYTICAL = "analytical"
    MULTIMODAL = "multimodal"


class FeedbackRating(int, Enum):
    """Feedback rating enumeration."""
    VERY_BAD = 1
    BAD = 2
    NEUTRAL = 3
    GOOD = 4
    EXCELLENT = 5


# ========================
# Base Models
# ========================

class TimestampedModel(BaseModel):
    """Base model with timestamps."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ========================
# User Models
# ========================

class UserBase(BaseModel):
    """Base user model."""
    user_id: str = Field(..., description="Unique user identifier")
    name: Optional[str] = Field(None, description="User display name")
    email: Optional[str] = Field(None, description="User email address")


class UserCreate(UserBase):
    """User creation model."""
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")


class UserUpdate(BaseModel):
    """User update model."""
    name: Optional[str] = Field(None, description="User display name")
    email: Optional[str] = Field(None, description="User email address")
    preferences: Optional[Dict[str, Any]] = Field(None, description="User preferences")


class UserResponse(UserBase, TimestampedModel):
    """User response model."""
    id: int
    preferences: Optional[Dict[str, Any]] = None


# ========================
# Session Models
# ========================

class SessionCreate(BaseModel):
    """Session creation model."""
    user_id: str = Field(..., description="User identifier")


class SessionResponse(BaseModel):
    """Session response model."""
    session_id: str = Field(..., description="Session identifier")
    user_id: str = Field(..., description="User identifier")
    created_at: datetime
    last_activity: datetime
    is_active: bool


# ========================
# Message Models
# ========================

class MessageBase(BaseModel):
    """Base message model."""
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")


class MessageCreate(MessageBase):
    """Message creation model."""
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MessageResponse(MessageBase, TimestampedModel):
    """Message response model."""
    id: int
    conversation_id: int
    metadata: Optional[Dict[str, Any]] = None


# ========================
# Query Models
# ========================

class QueryRequest(BaseModel):
    """RAG query request model."""
    query: str = Field(..., min_length=1, max_length=1000, description="User query")
    session_id: Optional[str] = Field(None, description="Session identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    max_results: Optional[int] = Field(10, ge=1, le=20, description="Maximum results to return")
    include_sources: bool = Field(True, description="Include source documents")
    
    @validator("query")
    def validate_query(cls, v):
        """Validate query is not empty after stripping."""
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()


class SourceDocument(BaseModel):
    """Source document model."""
    document_id: str = Field(..., description="Document identifier")
    title: str = Field(..., description="Document title")
    content_snippet: str = Field(..., description="Relevant content snippet")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence score")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Document metadata")


class QueryResponse(BaseModel):
    """RAG query response model."""
    query: str = Field(..., description="Original query")
    response: str = Field(..., description="Generated response")
    sources: List[SourceDocument] = Field(default_factory=list, description="Source documents")
    confidence_score: Optional[float] = Field(None, ge=0, le=1, description="Overall confidence")
    processing_time: float = Field(..., description="Processing time in seconds")
    session_id: Optional[str] = Field(None, description="Session identifier")
    query_type: Optional[QueryType] = Field(None, description="Detected query type")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


# ========================
# Feedback Models
# ========================

class FeedbackRequest(BaseModel):
    """User feedback request model."""
    query_log_id: int = Field(..., description="Query log identifier")
    rating: FeedbackRating = Field(..., description="Rating from 1-5")
    feedback_text: Optional[str] = Field(None, max_length=1000, description="Feedback comment")


class FeedbackResponse(BaseModel):
    """User feedback response model."""
    id: int
    query_log_id: int
    user_id: str
    rating: int
    feedback_text: Optional[str] = None
    created_at: datetime


# ========================
# Memory Models
# ========================

class MemoryContext(BaseModel):
    """Memory context model."""
    session_memory: Optional[Dict[str, Any]] = Field(None, description="Current session context")
    short_term_memory: Optional[Dict[str, Any]] = Field(None, description="Recent interactions")
    long_term_memory: Optional[Dict[str, Any]] = Field(None, description="User preferences and history")
    conversation_memory: Optional[List[Dict[str, Any]]] = Field(None, description="Relevant past conversations")


class MemoryUpdate(BaseModel):
    """Memory update model."""
    session_id: str = Field(..., description="Session identifier")
    user_id: Optional[str] = Field(None, description="User identifier")
    memory_type: str = Field(..., description="Type of memory to update")
    data: Dict[str, Any] = Field(..., description="Memory data to store")


# ========================
# Document Sync Models
# ========================

class DocumentSyncStatus(BaseModel):
    """Document sync status model."""
    document_id: str = Field(..., description="Document identifier")
    file_name: str = Field(..., description="File name")
    sync_status: str = Field(..., description="Sync status")
    last_sync: Optional[datetime] = Field(None, description="Last sync time")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class SyncRequest(BaseModel):
    """Document sync request model."""
    force_sync: bool = Field(False, description="Force synchronization")
    document_ids: Optional[List[str]] = Field(None, description="Specific documents to sync")


class SyncResponse(BaseModel):
    """Document sync response model."""
    total_documents: int = Field(..., description="Total documents processed")
    synced_documents: int = Field(..., description="Successfully synced documents")
    failed_documents: int = Field(..., description="Failed documents")
    processing_time: float = Field(..., description="Processing time in seconds")
    errors: List[str] = Field(default_factory=list, description="Error messages")


# ========================
# Health & Status Models
# ========================

class HealthCheck(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = Field(..., description="Application version")
    components: Dict[str, str] = Field(..., description="Component status")


# Alias for backward compatibility
HealthCheckResponse = HealthCheck


class SystemStats(BaseModel):
    """System statistics model."""
    total_queries: int = Field(..., description="Total queries processed")
    total_users: int = Field(..., description="Total users")
    active_sessions: int = Field(..., description="Active sessions")
    documents_synced: int = Field(..., description="Documents synced")
    avg_response_time: float = Field(..., description="Average response time")
    uptime: float = Field(..., description="System uptime in seconds")


# ========================
# Error Models
# ========================

class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
