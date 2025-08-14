"""
Startup script for Cloud Run deployment - more resilient initialization.
"""
import asyncio
import logging
import os
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

async def initialize_services():
    """Initialize services with error handling."""
    services_status = {
        "database": False,
        "memory_manager": False, 
        "rag_service": False,
        "google_drive": False,
        "google_sheets": False
    }
    
    try:
        # Import services
        from app.core.database import db_manager
        from app.services.memory_manager import memory_manager
        from app.services.rag_service import rag_service
        from app.services.google_drive_service import drive_sync_service
        from app.services.google_sheets_service import query_logger
        from app.utils.auth import create_temp_credentials_file
        
        # Setup Google Cloud credentials if needed
        temp_credentials_file = None
        if settings.gcp_sa_key_base64 and not settings.google_application_credentials:
            try:
                temp_credentials_file = create_temp_credentials_file()
                if temp_credentials_file:
                    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = temp_credentials_file
                    logger.info("Set up temporary credentials file for Google services")
            except Exception as e:
                logger.warning("Failed to setup Google credentials", error=str(e))
        
        # Initialize database with timeout
        try:
            await asyncio.wait_for(db_manager.create_tables(), timeout=30.0)
            services_status["database"] = True
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error("Database initialization failed", error=str(e))
        
        # Initialize memory manager with timeout
        try:
            await asyncio.wait_for(memory_manager.initialize(), timeout=20.0)
            services_status["memory_manager"] = True
            logger.info("Memory manager initialized successfully")
        except Exception as e:
            logger.error("Memory manager initialization failed", error=str(e))
        
        # Initialize RAG service with timeout
        try:
            await asyncio.wait_for(rag_service.initialize(), timeout=30.0)
            services_status["rag_service"] = True
            logger.info("RAG service initialized successfully")
        except Exception as e:
            logger.error("RAG service initialization failed", error=str(e))
        
        # Initialize Google services (optional)
        if settings.enable_google_drive_sync:
            try:
                await asyncio.wait_for(drive_sync_service.initialize(), timeout=15.0)
                services_status["google_drive"] = True
                logger.info("Google Drive service initialized successfully")
            except Exception as e:
                logger.warning("Google Drive service initialization failed", error=str(e))
        
        if settings.enable_google_sheets_logging:
            try:
                await asyncio.wait_for(query_logger.initialize(), timeout=15.0)
                services_status["google_sheets"] = True
                logger.info("Google Sheets logging initialized successfully")
            except Exception as e:
                logger.warning("Google Sheets logging initialization failed", error=str(e))
        
        # Log overall status
        initialized_count = sum(services_status.values())
        total_count = len(services_status)
        logger.info(f"Service initialization complete: {initialized_count}/{total_count} services initialized")
        
        return services_status
        
    except Exception as e:
        logger.error("Critical error during service initialization", error=str(e))
        return services_status

# Run the initialization if called directly
if __name__ == "__main__":
    asyncio.run(initialize_services())
