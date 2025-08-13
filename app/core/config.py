"""
Core configuration and settings for the Advanced RAG System.
"""

from functools import lru_cache
from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # ========================
    # GCP Configuration
    # ========================
    google_cloud_project: str = Field(..., description="Google Cloud Project ID")
    google_cloud_location: str = Field(default="us-central1", description="GCP region")
    google_application_credentials: Optional[str] = Field(default=None, description="Path to service account JSON")
    gcp_sa_key_base64: Optional[str] = Field(default=None, description="Base64 encoded service account key")
    gcp_sa_key_path: Optional[str] = Field(default=None, description="Path to service account key file")
    
    # ========================
    # Vertex AI Configuration
    # ========================
    vertex_ai_location: str = Field(default="us-central1", description="Vertex AI region")
    rag_document_corpus_id: str = Field(..., description="Document corpus ID")
    rag_memory_corpus_id: str = Field(..., description="Memory corpus ID")
    embedding_model: str = Field(default="text-embedding-005", description="Embedding model")
    generation_model: str = Field(default="gemini-2.0-flash", description="Generation model")
    
    # ========================
    # Google Drive Integration
    # ========================
    google_drive_folder_id: str = Field(..., description="Google Drive folder ID")
    drive_sync_interval: int = Field(default=300, description="Drive sync interval in seconds")
    
    # ========================
    # Google Sheets Logging
    # ========================
    google_sheets_id: str = Field(..., description="Google Sheets ID for logging")
    sheets_worksheet_name: str = Field(default="RAG_Logs", description="Worksheet name")
    
    # ========================
    # Database Configuration
    # ========================
    database_url: str = Field(..., description="Database connection URL")
    
    # ========================
    # Redis Configuration
    # ========================
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    
    # ========================
    # Application Settings
    # ========================
    app_name: str = Field(default="Advanced RAG System", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    debug: bool = Field(default=False, description="Debug mode")
    secret_key: str = Field(..., description="Secret key for sessions")
    
    # API Configuration
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 prefix")
    max_query_length: int = Field(default=1000, description="Maximum query length")
    max_response_length: int = Field(default=4000, description="Maximum response length")
    
    # ========================
    # Memory Configuration
    # ========================
    session_timeout: int = Field(default=3600, description="Session timeout in seconds")
    short_term_memory_ttl: int = Field(default=86400, description="Short-term memory TTL")
    max_conversation_history: int = Field(default=50, description="Max conversation history")
    
    # ========================
    # RAG Configuration
    # ========================
    max_retrieval_documents: int = Field(default=10, description="Max documents to retrieve")
    similarity_threshold: float = Field(default=0.7, description="Similarity threshold")
    hybrid_search_alpha: float = Field(default=0.6, description="Hybrid search alpha")
    enable_reranking: bool = Field(default=True, description="Enable result reranking")
    
    # ========================
    # Performance & Limits
    # ========================
    max_concurrent_requests: int = Field(default=100, description="Max concurrent requests")
    request_timeout: int = Field(default=30, description="Request timeout in seconds")
    rate_limit_per_minute: int = Field(default=60, description="Rate limit per minute")
    
    # ========================
    # Monitoring & Logging
    # ========================
    log_level: str = Field(default="INFO", description="Logging level")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    sentry_dsn: Optional[str] = Field(default=None, description="Sentry DSN for error tracking")
    
    # ========================
    # Development Settings
    # ========================
    reload: bool = Field(default=False, description="Auto-reload on changes")
    host: str = Field(default="0.0.0.0", description="Host to bind to")
    port: int = Field(default=8080, description="Port to bind to")
    
    @validator("hybrid_search_alpha")
    def validate_alpha(cls, v):
        """Validate hybrid search alpha is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("hybrid_search_alpha must be between 0 and 1")
        return v
    
    @validator("similarity_threshold")
    def validate_similarity_threshold(cls, v):
        """Validate similarity threshold is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("similarity_threshold must be between 0 and 1")
        return v
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
