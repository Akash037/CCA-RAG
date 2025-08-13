"""
Google Cloud Authentication Utilities
"""

import base64
import json
import os
import tempfile
from typing import Optional
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


def get_service_account_credentials(scopes: list[str]) -> service_account.Credentials:
    """
    Get service account credentials from environment variable or file.
    
    Args:
        scopes: List of required OAuth scopes
        
    Returns:
        Service account credentials
        
    Raises:
        Exception: If no valid credentials are found
    """
    try:
        # Method 1: Use base64 encoded key from environment variable
        if settings.gcp_sa_key_base64:
            logger.info("Loading service account credentials from environment variable")
            
            # Decode the base64 key
            key_data = base64.b64decode(settings.gcp_sa_key_base64).decode('utf-8')
            key_info = json.loads(key_data)
            
            # Create credentials from the key info
            credentials = service_account.Credentials.from_service_account_info(
                key_info, scopes=scopes
            )
            
            logger.info("Successfully loaded service account credentials from environment")
            return credentials
            
        # Method 2: Use file path
        elif settings.google_application_credentials:
            logger.info(f"Loading service account credentials from file: {settings.google_application_credentials}")
            
            if not os.path.exists(settings.google_application_credentials):
                raise FileNotFoundError(f"Service account file not found: {settings.google_application_credentials}")
                
            credentials = service_account.Credentials.from_service_account_file(
                settings.google_application_credentials, scopes=scopes
            )
            
            logger.info("Successfully loaded service account credentials from file")
            return credentials
            
        # Method 3: Use default ADC (Application Default Credentials)
        else:
            logger.info("No explicit credentials configured, using default ADC")
            from google.auth import default
            credentials, _ = default(scopes=scopes)
            
            # Ensure it's a service account credential
            if not isinstance(credentials, service_account.Credentials):
                raise Exception("Default credentials are not service account credentials")
                
            logger.info("Successfully loaded default service account credentials")
            return credentials
            
    except Exception as e:
        logger.error(f"Failed to load service account credentials: {str(e)}")
        raise


def create_temp_credentials_file() -> Optional[str]:
    """
    Create a temporary service account credentials file from base64 env var.
    
    Returns:
        Path to temporary credentials file or None if not available
    """
    try:
        if not settings.gcp_sa_key_base64:
            return None
            
        # Decode the base64 key
        key_data = base64.b64decode(settings.gcp_sa_key_base64).decode('utf-8')
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        temp_file.write(key_data)
        temp_file.close()
        
        logger.info(f"Created temporary credentials file: {temp_file.name}")
        return temp_file.name
        
    except Exception as e:
        logger.error(f"Failed to create temporary credentials file: {str(e)}")
        return None


def cleanup_temp_file(file_path: str) -> None:
    """
    Clean up temporary credentials file.
    
    Args:
        file_path: Path to temporary file to delete
    """
    try:
        if file_path and os.path.exists(file_path):
            os.unlink(file_path)
            logger.info(f"Cleaned up temporary credentials file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temporary file {file_path}: {str(e)}")
