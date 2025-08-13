#!/bin/bash

# 🔧 Post-Deployment Configuration Script
# This script adds environment variables to the deployed Cloud Run service

set -e

echo "🚀 Post-Deployment Configuration for RAG System"
echo "================================================"

# Configuration
PROJECT_ID="your-project-id"  # Replace with actual project ID
SERVICE_NAME="precision-farm-rag"
REGION="us-central1"

# Check if service exists
echo "🔍 Checking if service is deployed..."
if ! gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID >/dev/null 2>&1; then
    echo "❌ Service not found. Please ensure the deployment completed successfully."
    exit 1
fi

echo "✅ Service found. Adding environment variables..."

# Add environment variables
echo "📝 Setting production environment variables..."

gcloud run services update $SERVICE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    --update-env-vars="DATABASE_URL=${DATABASE_URL}" \
    --update-env-vars="REDIS_URL=${REDIS_URL}" \
    --update-env-vars="SECRET_KEY=${SECRET_KEY}" \
    --update-env-vars="RAG_DOCUMENT_CORPUS_ID=${RAG_DOCUMENT_CORPUS_ID}" \
    --update-env-vars="RAG_MEMORY_CORPUS_ID=${RAG_MEMORY_CORPUS_ID}" \
    --update-env-vars="GOOGLE_DRIVE_FOLDER_ID=${GOOGLE_DRIVE_FOLDER_ID}" \
    --update-env-vars="GOOGLE_SHEETS_ID=${GOOGLE_SHEETS_ID}" \
    --update-env-vars="GCP_SA_KEY_BASE64=${GCP_SA_KEY_BASE64}" \
    --update-env-vars="ENABLE_GOOGLE_DRIVE_SYNC=true" \
    --update-env-vars="ENABLE_GOOGLE_SHEETS_LOGGING=true" \
    --update-env-vars="MAX_RETRIEVAL_DOCUMENTS=10" \
    --update-env-vars="SIMILARITY_THRESHOLD=0.7" \
    --update-env-vars="HYBRID_SEARCH_ALPHA=0.6" \
    --update-env-vars="ENABLE_RERANKING=true" \
    --update-env-vars="MEMORY_TTL_HOURS=24" \
    --update-env-vars="SESSION_TIMEOUT_MINUTES=30" \
    --update-env-vars="MAX_CONVERSATION_HISTORY=50"

echo "✅ Environment variables added successfully!"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --format='value(status.url)')

echo ""
echo "🎉 Configuration Complete!"
echo "📍 Service URL: $SERVICE_URL"
echo "🔍 Health Check: $SERVICE_URL/health"
echo "📚 API Documentation: $SERVICE_URL/docs"

# Test the service
echo ""
echo "🧪 Testing configured service..."
if curl -f "$SERVICE_URL/health" -m 30 >/dev/null 2>&1; then
    echo "✅ Service is healthy and responding!"
else
    echo "⚠️  Service may still be starting up. Check logs if issues persist."
fi

echo ""
echo "📊 To monitor the service:"
echo "   gcloud run services logs read $SERVICE_NAME --region=$REGION --project=$PROJECT_ID"
echo ""
echo "🔧 To update environment variables:"
echo "   gcloud run services update $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --update-env-vars='KEY=VALUE'"
