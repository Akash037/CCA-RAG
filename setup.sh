#!/bin/bash

# Setup script for Advanced RAG System
# This script helps set up the development environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

echo "🚀 Advanced RAG System Setup"
echo "============================="

# Check if Python 3.11+ is installed
log_step "Checking Python version"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    log_info "Python $PYTHON_VERSION found"
    
    if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
        log_info "Python version is compatible ✅"
    else
        log_error "Python 3.11+ is required. Please upgrade Python."
        exit 1
    fi
else
    log_error "Python3 not found. Please install Python 3.11+"
    exit 1
fi

# Check if Poetry is installed
log_step "Checking Poetry installation"
if command -v poetry &> /dev/null; then
    POETRY_VERSION=$(poetry --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    log_info "Poetry $POETRY_VERSION found ✅"
else
    log_warn "Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
    
    if command -v poetry &> /dev/null; then
        log_info "Poetry installed successfully ✅"
    else
        log_error "Poetry installation failed. Please install manually: https://python-poetry.org/docs/#installation"
        exit 1
    fi
fi

# Check if Docker is installed
log_step "Checking Docker installation"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    log_info "Docker $DOCKER_VERSION found ✅"
    
    # Check if Docker is running
    if docker info > /dev/null 2>&1; then
        log_info "Docker is running ✅"
    else
        log_warn "Docker is installed but not running. Please start Docker."
    fi
else
    log_warn "Docker not found. Docker is required for local development with Redis."
    log_info "Install Docker from: https://docs.docker.com/get-docker/"
fi

# Check if gcloud CLI is installed
log_step "Checking Google Cloud CLI"
if command -v gcloud &> /dev/null; then
    GCLOUD_VERSION=$(gcloud version --format="value(Google Cloud SDK)" 2>/dev/null || echo "unknown")
    log_info "Google Cloud CLI $GCLOUD_VERSION found ✅"
    
    # Check if authenticated
    if gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1 > /dev/null 2>&1; then
        ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1)
        log_info "Authenticated as: $ACTIVE_ACCOUNT ✅"
    else
        log_warn "Not authenticated with Google Cloud. Run 'gcloud auth login'"
    fi
else
    log_warn "Google Cloud CLI not found. Required for deployment."
    log_info "Install from: https://cloud.google.com/sdk/docs/install"
fi

# Create project directories
log_step "Creating project directories"
mkdir -p data logs credentials

log_info "Project directories created ✅"

# Install Python dependencies
log_step "Installing Python dependencies"
log_info "This may take a few minutes..."

poetry config virtualenvs.in-project true
poetry install

log_info "Python dependencies installed ✅"

# Copy environment configuration
log_step "Setting up environment configuration"
if [ ! -f ".env" ]; then
    cp .env.development .env
    log_info "Development environment file created (.env) ✅"
    log_warn "Please edit .env file with your configuration values"
else
    log_info "Environment file (.env) already exists ✅"
fi

# Create database
log_step "Setting up database"
if [ ! -f "data/rag_dev.db" ]; then
    poetry run python -c "
import asyncio
from app.core.database import database_manager

async def init_db():
    await database_manager.create_tables()
    print('Database tables created successfully')

asyncio.run(init_db())
"
    log_info "Development database created ✅"
else
    log_info "Development database already exists ✅"
fi

# Setup pre-commit hooks (if in git repo)
if [ -d ".git" ]; then
    log_step "Setting up pre-commit hooks"
    poetry run pre-commit install
    log_info "Pre-commit hooks installed ✅"
fi

# Print next steps
echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Edit the .env file with your configuration:"
echo "   - Google Cloud Project ID"
echo "   - Vertex AI settings"
echo "   - Google Drive folder ID"
echo "   - Google Sheets spreadsheet ID"
echo ""
echo "2. Set up Google Cloud credentials:"
echo "   - Place service account key in credentials/ directory"
echo "   - Or run: gcloud auth application-default login"
echo ""
echo "3. Start the development server:"
echo "   poetry run uvicorn app.main:app --reload"
echo ""
echo "4. Or use Docker Compose for full stack:"
echo "   docker-compose up"
echo ""
echo "5. Access the API documentation:"
echo "   http://localhost:8000/docs"
echo ""
echo "For more information, see README.md"
