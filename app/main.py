"""
Main FastAPI Application for Advanced RAG System.

Implements:
- Chat endpoints with advanced memory management
- Document synchronization endpoints
- Analytics and monitoring endpoints
- Health checks and system status
- Real-time logging and error handling
- WebSocket support for real-time interactions
"""

import asyncio
import os
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .core.config import settings
from .core.logging import get_logger
from .core.database import database_manager
from .models.schemas import (
    QueryRequest, QueryResponse, MemoryContext, UserResponse,
    FeedbackRequest, FeedbackResponse, HealthCheckResponse,
    SyncRequest, SyncResponse, AnalyticsResponse
)
from .services.memory_manager import memory_manager
from .services.rag_service import rag_service
from .services.google_drive_service import drive_sync_service
from .services.google_sheets_service import query_logger, analytics_tracker
from .utils.auth import create_temp_credentials_file, cleanup_temp_file

logger = get_logger(__name__)

# Security
security = HTTPBearer(auto_error=False)

# Global variable to track temp credentials file
temp_credentials_file = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    global temp_credentials_file
    
    # Startup
    logger.info("Starting RAG application")
    
    try:
        # Setup Google Cloud credentials if needed
        if settings.gcp_sa_key_base64 and not settings.google_application_credentials:
            temp_credentials_file = create_temp_credentials_file()
            if temp_credentials_file:
                # Set environment variable for Google clients
                os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_credentials_file
                logger.info("Set up temporary credentials file for Google services")
        
        # Initialize database
        await database_manager.initialize()
        logger.info("Database initialized")
        
        # Initialize memory manager
        await memory_manager.initialize()
        logger.info("Memory manager initialized")
        
        # Initialize RAG service
        await rag_service.initialize()
        logger.info("RAG service initialized")
        
        # Initialize Google services
        if settings.enable_google_drive_sync:
            try:
                await drive_sync_service.initialize()
                logger.info("Google Drive service initialized")
                
                # Start periodic sync in background
                if settings.auto_sync_drive:
                    asyncio.create_task(
                        drive_sync_service.setup_periodic_sync(
                            settings.drive_sync_interval_hours
                        )
                    )
                    logger.info("Periodic Google Drive sync started")
            except Exception as e:
                logger.warning("Google Drive service initialization failed", error=str(e))
        
        if settings.enable_google_sheets_logging:
            try:
                await query_logger.initialize()
                logger.info("Google Sheets logging initialized")
            except Exception as e:
                logger.warning("Google Sheets logging initialization failed", error=str(e))
        
        logger.info("RAG application startup complete")
        
    except Exception as e:
        logger.error("Application startup failed", error=str(e))
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down RAG application")
    
    try:
        # Cleanup memory manager
        await memory_manager.cleanup()
        
        # Shutdown query logger
        if settings.enable_google_sheets_logging:
            await query_logger.shutdown()
        
        # Close database connections
        await database_manager.close_all()
        
        # Cleanup temporary credentials file
        if temp_credentials_file:
            cleanup_temp_file(temp_credentials_file)
            if 'GOOGLE_APPLICATION_CREDENTIALS' in os.environ:
                del os.environ['GOOGLE_APPLICATION_CREDENTIALS']
        
        logger.info("RAG application shutdown complete")
        
    except Exception as e:
        logger.error("Application shutdown failed", error=str(e))


# Create FastAPI application
app = FastAPI(
    title="Advanced RAG System",
    description="Production-ready RAG system with Google Cloud Vertex AI, memory management, and intelligent document sync",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[str]:
    """Get current user from authentication token."""
    if not credentials:
        return None
    
    # TODO: Implement proper token validation
    # For now, return a mock user ID
    return "user_123"


# Health check endpoints
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        db_healthy = await database_manager.health_check()
        
        # Check memory manager
        memory_healthy = memory_manager.initialized
        
        # Check RAG service
        rag_healthy = rag_service.initialized
        
        # Overall health
        healthy = db_healthy and memory_healthy and rag_healthy
        
        return HealthCheckResponse(
            status="healthy" if healthy else "unhealthy",
            timestamp=time.time(),
            services={
                "database": "healthy" if db_healthy else "unhealthy",
                "memory_manager": "healthy" if memory_healthy else "unhealthy",
                "rag_service": "healthy" if rag_healthy else "unhealthy",
                "google_drive": "enabled" if settings.enable_google_drive_sync else "disabled",
                "google_sheets": "enabled" if settings.enable_google_sheets_logging else "disabled"
            }
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=time.time(),
            services={},
            error=str(e)
        )


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with metrics."""
    try:
        health_data = {
            "timestamp": time.time(),
            "uptime": time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0,
            "memory_usage": await memory_manager.get_memory_usage(),
            "active_sessions": await memory_manager.get_active_sessions_count(),
            "database_connections": await database_manager.get_connection_count(),
        }
        
        if settings.enable_google_sheets_logging:
            health_data["queued_logs"] = {
                "query_logs": len(query_logger.log_queue),
                "interaction_logs": len(query_logger.interaction_queue),
                "analytics_logs": len(query_logger.analytics_queue)
            }
        
        return health_data
    except Exception as e:
        logger.error("Detailed health check failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


# Main chat endpoints
@app.post("/chat/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = Depends(get_current_user)
):
    """Process a RAG query with advanced memory integration."""
    start_time = time.time()
    
    try:
        # Set user ID if authenticated
        if user_id:
            request.user_id = user_id
        
        # Track session start if new session
        if request.session_id and settings.enable_google_sheets_logging:
            if request.session_id not in analytics_tracker.session_metrics:
                background_tasks.add_task(
                    analytics_tracker.track_session_start,
                    request.session_id,
                    user_id
                )
        
        # Process the query
        response = await rag_service.process_query(request)
        
        # Log query and response
        if settings.enable_google_sheets_logging:
            background_tasks.add_task(
                query_logger.log_query_response,
                request,
                response
            )
            
            # Track metrics
            background_tasks.add_task(
                analytics_tracker.track_query_metrics,
                request.session_id or "default",
                response.processing_time,
                response.confidence_score,
                response.query_type.value if response.query_type else "unknown"
            )
        
        return response
        
    except Exception as e:
        logger.error("Query processing failed", 
                    query=request.query, 
                    session_id=request.session_id,
                    error=str(e))
        
        # Track error
        if settings.enable_google_sheets_logging:
            background_tasks.add_task(
                analytics_tracker.track_error,
                "query_processing",
                str(e),
                request.session_id,
                user_id
            )
        
        raise HTTPException(status_code=500, detail="Query processing failed")


@app.post("/chat/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    request: FeedbackRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = Depends(get_current_user)
):
    """Submit feedback for a query response."""
    try:
        # Process feedback (store in database, update models, etc.)
        # For now, just log it
        
        if settings.enable_google_sheets_logging:
            background_tasks.add_task(
                query_logger.log_interaction,
                request.session_id,
                user_id,
                "feedback",
                {
                    "query_id": request.query_id,
                    "rating": request.rating,
                    "feedback_text": request.feedback_text,
                    "improvement_suggestions": request.improvement_suggestions
                }
            )
        
        return FeedbackResponse(
            success=True,
            message="Feedback received successfully"
        )
        
    except Exception as e:
        logger.error("Feedback submission failed", error=str(e))
        raise HTTPException(status_code=500, detail="Feedback submission failed")


# Memory management endpoints
@app.get("/memory/context/{session_id}")
async def get_memory_context(
    session_id: str,
    user_id: Optional[str] = Depends(get_current_user)
) -> MemoryContext:
    """Get comprehensive memory context for a session."""
    try:
        return await memory_manager.get_comprehensive_memory(session_id, user_id)
    except Exception as e:
        logger.error("Failed to get memory context", 
                    session_id=session_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve memory context")


@app.delete("/memory/session/{session_id}")
async def clear_session_memory(
    session_id: str,
    user_id: Optional[str] = Depends(get_current_user)
):
    """Clear memory for a specific session."""
    try:
        await memory_manager.clear_session_memory(session_id)
        
        # Track session end
        if settings.enable_google_sheets_logging:
            await analytics_tracker.track_session_end(session_id)
        
        return {"message": "Session memory cleared successfully"}
    except Exception as e:
        logger.error("Failed to clear session memory", 
                    session_id=session_id, 
                    error=str(e))
        raise HTTPException(status_code=500, detail="Failed to clear session memory")


@app.get("/memory/stats")
async def get_memory_stats(user_id: Optional[str] = Depends(get_current_user)):
    """Get memory usage statistics."""
    try:
        return {
            "memory_usage": await memory_manager.get_memory_usage(),
            "active_sessions": await memory_manager.get_active_sessions_count(),
            "redis_info": await memory_manager.get_redis_info() if hasattr(memory_manager, 'get_redis_info') else None
        }
    except Exception as e:
        logger.error("Failed to get memory stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve memory statistics")


# Document synchronization endpoints
@app.post("/documents/sync", response_model=SyncResponse)
async def sync_documents(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
    user_id: Optional[str] = Depends(get_current_user)
):
    """Sync documents from Google Drive to RAG corpus."""
    try:
        if not settings.enable_google_drive_sync:
            raise HTTPException(status_code=503, detail="Google Drive sync is disabled")
        
        # Start sync in background if requested
        if request.background:
            background_tasks.add_task(
                drive_sync_service.sync_drive_folder,
                request.folder_id
            )
            return SyncResponse(
                success=True,
                message="Document sync started in background",
                sync_id=f"background_{int(time.time())}"
            )
        else:
            # Synchronous sync
            result = await drive_sync_service.sync_drive_folder(request.folder_id)
            return SyncResponse(
                success=True,
                message="Document sync completed",
                sync_id=f"sync_{int(time.time())}",
                details=result
            )
            
    except Exception as e:
        logger.error("Document sync failed", error=str(e))
        raise HTTPException(status_code=500, detail="Document sync failed")


@app.get("/documents/status")
async def get_sync_status(user_id: Optional[str] = Depends(get_current_user)):
    """Get document synchronization status."""
    try:
        # TODO: Implement sync status tracking
        return {
            "last_sync": "2024-01-01T00:00:00Z",
            "sync_enabled": settings.enable_google_drive_sync,
            "auto_sync": settings.auto_sync_drive,
            "sync_interval_hours": settings.drive_sync_interval_hours,
            "documents_indexed": 0  # TODO: Get from database
        }
    except Exception as e:
        logger.error("Failed to get sync status", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve sync status")


# Analytics endpoints
@app.get("/analytics/summary", response_model=AnalyticsResponse)
async def get_analytics_summary(
    days: int = 7,
    user_id: Optional[str] = Depends(get_current_user)
):
    """Get analytics summary for the specified period."""
    try:
        # TODO: Implement analytics aggregation from Google Sheets or database
        return AnalyticsResponse(
            total_queries=0,
            unique_users=0,
            avg_response_time=0.0,
            avg_confidence_score=0.0,
            top_query_types=[],
            period_days=days
        )
    except Exception as e:
        logger.error("Failed to get analytics summary", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics")


# WebSocket endpoint for real-time chat
@app.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat interactions."""
    await websocket.accept()
    
    try:
        # Track session start
        if settings.enable_google_sheets_logging:
            await analytics_tracker.track_session_start(session_id)
        
        while True:
            # Receive message
            data = await websocket.receive_json()
            
            try:
                # Create query request
                request = QueryRequest(
                    query=data.get("query", ""),
                    session_id=session_id,
                    user_id=data.get("user_id"),
                    max_results=data.get("max_results", 5),
                    include_sources=data.get("include_sources", True)
                )
                
                # Process query
                response = await rag_service.process_query(request)
                
                # Send response
                await websocket.send_json({
                    "type": "response",
                    "data": response.dict()
                })
                
                # Log interaction
                if settings.enable_google_sheets_logging:
                    await query_logger.log_query_response(request, response)
                    await analytics_tracker.track_query_metrics(
                        session_id,
                        response.processing_time,
                        response.confidence_score,
                        response.query_type.value if response.query_type else "unknown"
                    )
                
            except Exception as e:
                logger.error("WebSocket query processing failed", error=str(e))
                await websocket.send_json({
                    "type": "error",
                    "message": "Query processing failed"
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", session_id=session_id)
        
        # Track session end
        if settings.enable_google_sheets_logging:
            await analytics_tracker.track_session_end(session_id)
    
    except Exception as e:
        logger.error("WebSocket error", session_id=session_id, error=str(e))


# User management endpoints
@app.get("/users/profile", response_model=UserResponse)
async def get_user_profile(user_id: str = Depends(get_current_user)):
    """Get user profile information."""
    try:
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        # TODO: Implement user profile retrieval from database
        return UserResponse(
            user_id=user_id,
            created_at="2024-01-01T00:00:00Z",
            total_queries=0,
            avg_session_length=0.0,
            preferences={}
        )
    except Exception as e:
        logger.error("Failed to get user profile", user_id=user_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve user profile")


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail, "status_code": exc.status_code}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error("Unhandled exception", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"message": "Internal server error", "status_code": 500}
    )


# Startup event to set start time
@app.on_event("startup")
async def set_start_time():
    """Set application start time."""
    app.state.start_time = time.time()


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )
