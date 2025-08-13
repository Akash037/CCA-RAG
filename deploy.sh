#!/bin/bash

# Deployment script for RAG System to Google Cloud Run
# Usage: ./deploy.sh [environment] [project-id]

set -e

# Configuration
ENVIRONMENT=${1:-production}
PROJECT_ID=${2:-$GOOGLE_CLOUD_PROJECT}
SERVICE_NAME="rag-system"
REGION="us-central1"
IMAGE_NAME="$REGION-docker.pkg.dev/$PROJECT_ID/rag-system/$SERVICE_NAME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Validate inputs
if [ -z "$PROJECT_ID" ]; then
    log_error "PROJECT_ID is required. Set GOOGLE_CLOUD_PROJECT or pass as second argument."
    exit 1
fi

if [ "$ENVIRONMENT" != "production" ] && [ "$ENVIRONMENT" != "staging" ]; then
    log_error "ENVIRONMENT must be 'production' or 'staging'"
    exit 1
fi

log_info "Starting deployment to $ENVIRONMENT environment"
log_info "Project ID: $PROJECT_ID"
log_info "Service Name: $SERVICE_NAME"
log_info "Region: $REGION"

# Check if user is authenticated with gcloud
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1 > /dev/null; then
    log_error "Not authenticated with gcloud. Run 'gcloud auth login'"
    exit 1
fi

# Set the project
log_info "Setting project to $PROJECT_ID"
gcloud config set project $PROJECT_ID

# Enable required APIs
log_info "Enabling required Google Cloud APIs"
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    aiplatform.googleapis.com \
    redis.googleapis.com \
    sqladmin.googleapis.com

# Create Artifact Registry repository if it doesn't exist
log_info "Creating Artifact Registry repository"
gcloud artifacts repositories create rag-system \
    --repository-format=docker \
    --location=$REGION \
    --description="RAG System Docker repository" \
    --quiet || log_warn "Repository may already exist"

# Configure Docker to use gcloud as credential helper
log_info "Configuring Docker authentication"
gcloud auth configure-docker $REGION-docker.pkg.dev

# Build and push Docker image
log_info "Building Docker image"
docker build -t $IMAGE_NAME:latest .

log_info "Pushing Docker image to Artifact Registry"
docker push $IMAGE_NAME:latest

# Set service name based on environment
if [ "$ENVIRONMENT" = "staging" ]; then
    SERVICE_NAME="$SERVICE_NAME-staging"
fi

# Deploy to Cloud Run
log_info "Deploying to Cloud Run"

# Base deployment command
DEPLOY_CMD="gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --timeout 300 \
    --set-env-vars ENVIRONMENT=$ENVIRONMENT"

# Environment-specific configurations
if [ "$ENVIRONMENT" = "production" ]; then
    DEPLOY_CMD="$DEPLOY_CMD \
        --memory 2Gi \
        --cpu 2 \
        --min-instances 1 \
        --max-instances 10 \
        --concurrency 80"
else
    DEPLOY_CMD="$DEPLOY_CMD \
        --memory 1Gi \
        --cpu 1 \
        --min-instances 0 \
        --max-instances 5 \
        --concurrency 40"
fi

# Add environment variables from .env file if it exists
if [ -f ".env.$ENVIRONMENT" ]; then
    log_info "Loading environment variables from .env.$ENVIRONMENT"
    
    # Read environment variables and add them to the deploy command
    while IFS= read -r line; do
        if [[ $line && $line != \#* ]]; then
            VAR_NAME=$(echo $line | cut -d'=' -f1)
            DEPLOY_CMD="$DEPLOY_CMD --set-env-vars $line"
        fi
    done < ".env.$ENVIRONMENT"
fi

# Execute deployment
eval $DEPLOY_CMD

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

log_info "Deployment completed successfully!"
log_info "Service URL: $SERVICE_URL"

# Run health check
log_info "Running health check"
sleep 10  # Wait for service to be ready

if curl -f "$SERVICE_URL/health" > /dev/null 2>&1; then
    log_info "Health check passed ✅"
else
    log_warn "Health check failed ❌"
    log_warn "Service might still be starting up. Check Cloud Run logs:"
    log_warn "gcloud run services logs read $SERVICE_NAME --region $REGION"
fi

# Show logs command
log_info "To view logs:"
echo "gcloud run services logs read $SERVICE_NAME --region $REGION --follow"

# Show metrics command
log_info "To view metrics:"
echo "gcloud run services describe $SERVICE_NAME --region $REGION"

log_info "Deployment script completed!"
