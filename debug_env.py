#!/usr/bin/env python3
"""
Debug script to check environment variables and identify missing configurations.
This helps troubleshoot Cloud Run deployment issues with missing environment variables.
"""

import os
import sys
from typing import Dict, List


def check_required_env_vars() -> Dict[str, str]:
    """Check all required environment variables from config.py"""
    
    required_vars = {
        # GCP Configuration  
        'GOOGLE_CLOUD_PROJECT': 'Google Cloud Project ID',
        'GOOGLE_CLOUD_LOCATION': 'GCP region (default: us-central1)',
        
        # Vertex AI Configuration
        'RAG_DOCUMENT_CORPUS_ID': 'Document corpus ID',
        'RAG_MEMORY_CORPUS_ID': 'Memory corpus ID', 
        'VERTEX_AI_LOCATION': 'Vertex AI region (default: us-central1)',
        'EMBEDDING_MODEL': 'Embedding model (default: text-embedding-005)',
        'GENERATION_MODEL': 'Generation model (default: gemini-2.0-flash)',
        
        # Google Drive Integration
        'GOOGLE_DRIVE_FOLDER_ID': 'Google Drive folder ID',
        
        # Google Sheets Logging
        'GOOGLE_SHEETS_ID': 'Google Sheets ID for logging',
        
        # Database Configuration  
        'DATABASE_URL': 'Database connection URL',
        'REDIS_URL': 'Redis connection URL (default: redis://localhost:6379/0)',
        
        # Application Settings
        'SECRET_KEY': 'Secret key for sessions',
        'DEBUG': 'Debug mode (default: False)',
        'LOG_LEVEL': 'Logging level (default: INFO)',
        'PORT': 'Port to bind to (default: 8080)'
    }
    
    missing_vars = []
    empty_vars = []
    present_vars = []
    
    print("🔍 Environment Variable Check Report")
    print("=" * 50)
    
    for var_name, description in required_vars.items():
        value = os.getenv(var_name)
        
        if value is None:
            missing_vars.append(var_name)
            print(f"❌ {var_name}: MISSING")
        elif value.strip() == "":
            empty_vars.append(var_name) 
            print(f"⚠️  {var_name}: EMPTY")
        else:
            present_vars.append(var_name)
            # Mask sensitive values
            if 'SECRET' in var_name or 'URL' in var_name or 'KEY' in var_name:
                masked_value = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
                print(f"✅ {var_name}: {masked_value}")
            else:
                print(f"✅ {var_name}: {value}")
    
    print("\n📊 Summary:")
    print(f"✅ Present: {len(present_vars)}")
    print(f"⚠️  Empty: {len(empty_vars)}")  
    print(f"❌ Missing: {len(missing_vars)}")
    
    if missing_vars:
        print(f"\n🚨 CRITICAL: Missing environment variables:")
        for var in missing_vars:
            print(f"   - {var}: {required_vars[var]}")
            
    if empty_vars:
        print(f"\n⚠️  WARNING: Empty environment variables:")
        for var in empty_vars:
            print(f"   - {var}: {required_vars[var]}")
    
    # Check for GitHub secrets format
    print(f"\n🔍 GitHub Secrets Check:")
    github_secrets = [
        'GCP_PROJECT_ID',
        'GCP_SA_KEY', 
        'SERVICE_NAME',
        'REGION',
        'DATABASE_URL',
        'REDIS_URL', 
        'VERTEX_CORPUS_ID',
        'VERTEX_INDEX_ID',
        'RAG_DOCUMENT_CORPUS_ID',
        'RAG_MEMORY_CORPUS_ID',
        'GOOGLE_DRIVE_FOLDER_ID',
        'GOOGLE_SHEETS_SPREADSHEET_ID',
        'SECRET_KEY'
    ]
    
    for secret in github_secrets:
        value = os.getenv(secret)
        if value:
            masked = value[:4] + "..." if len(value) > 4 else "***"
            print(f"✅ {secret}: {masked}")
        else:
            print(f"❌ {secret}: NOT SET")
    
    return {
        'missing': missing_vars,
        'empty': empty_vars, 
        'present': present_vars
    }


def main():
    """Main function to run environment check"""
    print("🚀 Cloud Run Environment Variables Debug Tool")
    print("=" * 60)
    
    result = check_required_env_vars()
    
    if result['missing'] or result['empty']:
        print(f"\n❌ DEPLOYMENT WILL FAIL!")
        print("Fix the missing/empty environment variables before deploying.")
        sys.exit(1)
    else:
        print(f"\n✅ ALL ENVIRONMENT VARIABLES CONFIGURED!")
        print("Deployment should succeed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
