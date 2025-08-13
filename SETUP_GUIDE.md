# Complete Setup Guide for Advanced RAG System

This guide will walk you through setting up everything needed to run the Advanced RAG System, from Google Cloud Platform to Vertex AI, Google Drive, and all required credentials.

## 📋 Prerequisites

Before starting, ensure you have:
- A Google Cloud Platform account with billing enabled
- Administrative access to your Google Workspace (for Drive and Sheets)
- Basic command line knowledge
- Python 3.11+ installed locally

## 🛠️ Step-by-Step Setup

### 1. Google Cloud Platform (GCP) Setup

#### 1.1 Create a New GCP Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"New Project"**
3. Enter project name: `rag-system-prod` (or your preferred name)
4. Note your **Project ID** (you'll need this for the `.env` file)
5. Click **"Create"**

#### 1.2 Enable Billing
1. Go to **Billing** in the left sidebar
2. Link a billing account to your project
3. Ensure billing is enabled (required for Vertex AI)

#### 1.3 Enable Required APIs
Open **PowerShell as Administrator** and run these commands:

```powershell
# Set your project ID (replace with your actual project ID)
$PROJECT_ID = "your-project-id"
gcloud config set project $PROJECT_ID

# Enable required APIs (run as single commands)
gcloud services enable aiplatform.googleapis.com
gcloud services enable drive.googleapis.com
gcloud services enable sheets.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable redis.googleapis.com
gcloud services enable sqladmin.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable logging.googleapis.com
gcloud services enable monitoring.googleapis.com
```

**Alternative: Enable via Console**
1. Go to [Google Cloud Console APIs](https://console.cloud.google.com/apis/library)
2. Search for and enable each API:
   - Vertex AI API
   - Google Drive API  
   - Google Sheets API
   - Cloud Build API
   - Cloud Run API
   - Artifact Registry API
   - Cloud Memorystore for Redis API
   - Cloud SQL Admin API
   - Secret Manager API
   - Cloud Logging API
   - Cloud Monitoring API

### 2. Service Account Setup

#### 2.1 Create Service Account
Open **PowerShell** and run:

```powershell
# Create service account
gcloud iam service-accounts create rag-system-sa --display-name="RAG System Service Account" --description="Service account for RAG system operations"
```

#### 2.2 Grant Required Permissions
```powershell
# Set your project ID and service account email
$PROJECT_ID = "your-project-id"  # Replace with your actual project ID
$SA_EMAIL = "rag-system-sa@$PROJECT_ID.iam.gserviceaccount.com"

# Grant necessary roles (run each command separately)
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL" --role="roles/aiplatform.user"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL" --role="roles/aiplatform.serviceAgent"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL" --role="roles/storage.objectAdmin"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL" --role="roles/secretmanager.accessor"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL" --role="roles/logging.logWriter"
gcloud projects add-iam-policy-binding $PROJECT_ID --member="serviceAccount:$SA_EMAIL" --role="roles/monitoring.metricWriter"
```

#### 2.3 Create and Download Service Account Key
```powershell
# Create credentials directory
mkdir credentials -Force

# Create key file  
gcloud iam service-accounts keys create .\credentials\rag-service-account.json --iam-account=$SA_EMAIL
```

**⚠️ Important**: Keep this JSON file secure and never commit it to version control!

### 3. Vertex AI Setup

#### 3.1 Initialize Vertex AI
1. Go to [Vertex AI Console](https://console.cloud.google.com/vertex-ai)
2. Select your project
3. Click **"Enable Vertex AI API"** if prompted
4. Choose region: **us-central1** (recommended)

#### 3.2 Create RAG Corpora

**Option A: Create via Google Cloud Console (Recommended for Windows)**

1. Go to [Vertex AI Console](https://console.cloud.google.com/vertex-ai)
2. Navigate to **"Vector Search"** → **"Indexes"**
3. Click **"Create Index"**
4. Fill in the details:
   - **Display Name**: `RAG Document Corpus`
   - **Description**: `Main document knowledge base for RAG system`
   - **Region**: `us-central1`
   - **Dimensions**: `768` (for text-embedding-005)
   - **Index Type**: `Tree-AH`
5. Click **"Create"**
6. Repeat for the Memory Corpus:
   - **Display Name**: `RAG Memory Corpus`
   - **Description**: `Conversation memory and context for RAG system`

**Option B: Create via PowerShell (Windows)**

```powershell
# Install gcloud beta components if not already installed
gcloud components install beta

# Create Document Corpus (single line for Windows)
gcloud ai indexes create --display-name="RAG Document Corpus" --description="Main document knowledge base for RAG system" --dimensions=768 --algorithm-config-tree-ah-config-leaf-node-embedding-count=1000 --algorithm-config-tree-ah-config-leaf-nodes-to-search-percent=10 --region=us-central1

# Create Memory Corpus (single line for Windows)  
gcloud ai indexes create --display-name="RAG Memory Corpus" --description="Conversation memory and context for RAG system" --dimensions=768 --algorithm-config-tree-ah-config-leaf-node-embedding-count=500 --algorithm-config-tree-ah-config-leaf-nodes-to-search-percent=20 --region=us-central1
```

**Option C: Create via Python Script (Most Reliable)**

Create a file called `create_indexes.py`:

```python
from google.cloud import aiplatform
import os

# Set your project ID
PROJECT_ID = "your-project-id"  # Replace with your actual project ID
LOCATION = "us-central1"

# Initialize Vertex AI
aiplatform.init(project=PROJECT_ID, location=LOCATION)

try:
    # Create Document Corpus
    print("Creating Document Corpus...")
    doc_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
        display_name="RAG Document Corpus",
        contents_delta_uri=f"gs://{PROJECT_ID}-rag-temp/empty",  # Temporary empty bucket
        dimensions=768,  # For text-embedding-005
        approximate_neighbors_count=150,
        leaf_node_embedding_count=1000,
        leaf_nodes_to_search_percent=10,
        distance_measure_type="DOT_PRODUCT_DISTANCE",
        description="Main document knowledge base for RAG system"
    )
    
    print(f"✅ Document Corpus created successfully!")
    print(f"   Index ID: {doc_index.name}")
    print(f"   Resource Name: {doc_index.resource_name}")
    
    # Create Memory Corpus
    print("\nCreating Memory Corpus...")
    memory_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
        display_name="RAG Memory Corpus",
        contents_delta_uri=f"gs://{PROJECT_ID}-rag-temp/empty",  # Temporary empty bucket
        dimensions=768,
        approximate_neighbors_count=50,
        leaf_node_embedding_count=500,
        leaf_nodes_to_search_percent=20,
        distance_measure_type="DOT_PRODUCT_DISTANCE",
        description="Conversation memory and context for RAG system"
    )
    
    print(f"✅ Memory Corpus created successfully!")
    print(f"   Index ID: {memory_index.name}")
    print(f"   Resource Name: {memory_index.resource_name}")
    
    print("\n" + "="*50)
    print("📝 IMPORTANT: Save these Index IDs for your .env file:")
    print(f"RAG_DOCUMENT_CORPUS_ID={doc_index.name.split('/')[-1]}")
    print(f"RAG_MEMORY_CORPUS_ID={memory_index.name.split('/')[-1]}")
    print("="*50)
    
except Exception as e:
    print(f"❌ Error creating indexes: {e}")
    print("\nTroubleshooting tips:")
    print("1. Ensure your project ID is correct")
    print("2. Make sure Vertex AI API is enabled")
    print("3. Check your authentication with: gcloud auth list")
    print("4. Verify billing is enabled for your project")
```

Run the script:
```powershell
# Set your credentials
$env:GOOGLE_APPLICATION_CREDENTIALS=".\credentials\rag-service-account.json"

# Run the script
python create_indexes.py
```

**Note the Index IDs** from the output - you'll need these for your `.env` file.

Alternative: Create via Python script:
```python
from google.cloud import aiplatform

# Initialize Vertex AI
aiplatform.init(project="your-project-id", location="us-central1")

# Create Document Corpus
doc_corpus = aiplatform.MatchingEngineIndex.create_tree_ah_index(
    display_name="RAG Document Corpus",
    contents_delta_uri="gs://your-bucket/empty",  # Start with empty
    dimensions=768,  # For text-embedding-005
    approximate_neighbors_count=150,
    leaf_node_embedding_count=500,
    leaf_nodes_to_search_percent=10,
)

# Create Memory Corpus
memory_corpus = aiplatform.MatchingEngineIndex.create_tree_ah_index(
    display_name="RAG Memory Corpus", 
    contents_delta_uri="gs://your-bucket/empty",
    dimensions=768,
    approximate_neighbors_count=50,
    leaf_node_embedding_count=100,
    leaf_nodes_to_search_percent=20,
)

print(f"Document Corpus ID: {doc_corpus.resource_name}")
print(f"Memory Corpus ID: {memory_corpus.resource_name}")
```

### 4. Google Drive Setup

#### 4.1 Create Drive Folder
1. Go to [Google Drive](https://drive.google.com)
2. Create a new folder named **"RAG Documents"**
3. Copy the folder ID from the URL (the long string after `/folders/`)
   - Example: `https://drive.google.com/drive/folders/1ABC123DEF456GHI789JKL` 
   - Folder ID: `1ABC123DEF456GHI789JKL`
4. Upload your documents to this folder (PDFs, DOCX, TXT, etc.)

#### 4.2 Enable Drive API for Service Account
1. Go to [Google Cloud Console APIs](https://console.cloud.google.com/apis/api/drive.googleapis.com)
2. Ensure Google Drive API is enabled
3. Share your Drive folder with the service account email:
   - Right-click the folder → Share
   - Add `rag-system-sa@your-project-id.iam.gserviceaccount.com`
   - Give **Editor** permissions

### 5. Google Sheets Setup

#### 5.1 Create Logging Spreadsheet
1. Go to [Google Sheets](https://sheets.google.com)
2. Create a new spreadsheet named **"RAG System Logs"**
3. Copy the spreadsheet ID from the URL
   - Example: `https://docs.google.com/spreadsheets/d/1XYZ789ABC123DEF456/edit`
   - Sheet ID: `1XYZ789ABC123DEF456`

#### 5.2 Share with Service Account
1. Click **Share** in the top-right
2. Add your service account email: `rag-system-sa@your-project-id.iam.gserviceaccount.com`
3. Give **Editor** permissions

#### 5.3 Prepare Sheet Structure
The system will automatically create these worksheets:
- `Query_Logs` - All queries and responses
- `Interaction_Logs` - User interactions  
- `Analytics` - Performance metrics
- `Performance_Metrics` - System performance data

### 6. Database Setup

#### Option A: Cloud SQL (Production Recommended)

```bash
# Create Cloud SQL instance
gcloud sql instances create rag-database \
    --database-version=POSTGRES_15 \
    --tier=db-f1-micro \
    --region=us-central1 \
    --storage-type=SSD \
    --storage-size=10GB

# Create database
gcloud sql databases create ragdb --instance=rag-database

# Create user
gcloud sql users create raguser --instance=rag-database --password=your-secure-password

# Get connection name
gcloud sql instances describe rag-database --format="value(connectionName)"
```

Your DATABASE_URL will be:
```
postgresql+asyncpg://raguser:your-secure-password@/ragdb?host=/cloudsql/PROJECT_ID:us-central1:rag-database
```

#### Option B: Local Development (SQLite)
For development, you can use SQLite:
```
DATABASE_URL=sqlite+aiosqlite:///./data/rag_system.db
```

### 7. Redis Setup

#### Option A: Cloud Memorystore (Production)

```bash
# Create Redis instance
gcloud redis instances create rag-redis \
    --size=1 \
    --region=us-central1 \
    --redis-version=redis_7_0

# Get IP address
gcloud redis instances describe rag-redis --region=us-central1 --format="value(host)"
```

#### Option B: Local Development
Use Docker for local Redis:
```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### 8. Environment Configuration

#### 8.1 Copy and Configure Environment File
```bash
# Copy template
cp .env.example .env

# Edit with your values
nano .env  # or use your preferred editor
```

#### 8.2 Fill in Your Values

Update `.env` with all the values you collected:

```bash
# ========================
# GCP Configuration  
# ========================
GOOGLE_CLOUD_PROJECT=your-actual-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=./credentials/rag-service-account.json

# ========================
# Vertex AI Configuration
# ========================
VERTEX_AI_LOCATION=us-central1
RAG_DOCUMENT_CORPUS_ID=your-document-corpus-index-id
RAG_MEMORY_CORPUS_ID=your-memory-corpus-index-id
EMBEDDING_MODEL=text-embedding-005
GENERATION_MODEL=gemini-2.0-flash

# ========================
# Google Drive Integration
# ========================
GOOGLE_DRIVE_FOLDER_ID=your-google-drive-folder-id
DRIVE_SYNC_INTERVAL=300

# ========================
# Google Sheets Logging
# ========================
GOOGLE_SHEETS_ID=your-google-sheets-spreadsheet-id
SHEETS_WORKSHEET_NAME=RAG_Logs

# ========================
# Database Configuration
# ========================
# For Cloud SQL:
DATABASE_URL=postgresql+asyncpg://raguser:password@/ragdb?host=/cloudsql/PROJECT_ID:us-central1:rag-database

# For local development:
# DATABASE_URL=sqlite+aiosqlite:///./data/rag_system.db

# ========================
# Redis Configuration
# ========================
# For Cloud Memorystore:
REDIS_URL=redis://your-memorystore-ip:6379/0

# For local development:
# REDIS_URL=redis://localhost:6379/0

# ========================
# Application Settings
# ========================
APP_NAME=Advanced RAG System
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=your-super-secret-key-here
HOST=0.0.0.0
PORT=8000

# ========================
# Performance Settings
# ========================
MAX_RETRIEVAL_DOCUMENTS=10
SIMILARITY_THRESHOLD=0.7
HYBRID_SEARCH_ALPHA=0.6
ENABLE_RERANKING=true
MAX_DOCUMENT_LENGTH=10000

# ========================
# Memory Settings
# ========================
MEMORY_TTL_HOURS=24
SESSION_TIMEOUT_MINUTES=30
MAX_CONVERSATION_HISTORY=50

# ========================
# Google Services Settings
# ========================
ENABLE_GOOGLE_DRIVE_SYNC=true
AUTO_SYNC_DRIVE=true
DRIVE_SYNC_INTERVAL_HOURS=24
ENABLE_GOOGLE_SHEETS_LOGGING=true
SHEETS_BATCH_SIZE=100
SHEETS_FLUSH_INTERVAL=300

# ========================
# Security Settings
# ========================
ALLOWED_ORIGINS=["https://yourdomain.com"]

# ========================
# Logging Settings
# ========================
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### 9. Local Development Setup

#### 9.1 Install Dependencies
```bash
# Make setup script executable
chmod +x setup.sh

# Run setup script
./setup.sh
```

Or manually:
```bash
# Install Poetry if not installed
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies
poetry install

# Create directories
mkdir -p data logs credentials

# Copy environment file
cp .env.example .env
```

#### 9.2 Test Local Setup
```bash
# Start development server
poetry run uvicorn app.main:app --reload

# Test health endpoint
curl http://localhost:8000/health

# Test with Docker Compose
docker-compose up
```

### 10. Cloud Deployment

#### 10.1 Prepare for Deployment
```bash
# Make deploy script executable
chmod +x deploy.sh

# Authenticate with Google Cloud
gcloud auth login
gcloud config set project your-project-id
```

#### 10.2 Deploy to Cloud Run
```bash
# Deploy to production
./deploy.sh production your-project-id

# Or deploy manually
gcloud run deploy rag-system \
    --source . \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

### 11. GitHub Actions Setup (Optional)

#### 11.1 GitHub Secrets
Add these secrets to your GitHub repository:

```
GCP_PROJECT_ID=your-project-id
GCP_SA_KEY=<contents of service account JSON file>
DATABASE_URL=your-database-url
REDIS_URL=your-redis-url
RAG_DOCUMENT_CORPUS_ID=your-document-corpus-id
RAG_MEMORY_CORPUS_ID=your-memory-corpus-id
GOOGLE_DRIVE_FOLDER_ID=your-drive-folder-id
GOOGLE_SHEETS_SPREADSHEET_ID=your-sheets-id
SECRET_KEY=your-secret-key
```

#### 11.2 Push to GitHub
```bash
git init
git add .
git commit -m "Initial RAG system setup"
git branch -M main
git remote add origin https://github.com/yourusername/rag-system.git
git push -u origin main
```

## 🧪 Testing Your Setup

### Test API Endpoints
```bash
# Health check
curl https://your-rag-service-url/health

# Test query
curl -X POST https://your-rag-service-url/chat/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "session_id": "test_session",
    "user_id": "test_user"
  }'
```

### Test Document Sync
```bash
curl -X POST https://your-rag-service-url/documents/sync \
  -H "Content-Type: application/json" \
  -d '{"folder_id": "your-drive-folder-id", "background": true}'
```

## 🔧 Troubleshooting

### Common Issues

1. **Authentication Errors**
   ```bash
   gcloud auth application-default login
   export GOOGLE_APPLICATION_CREDENTIALS="./credentials/rag-service-account.json"
   ```

2. **API Not Enabled**
   ```bash
   gcloud services enable aiplatform.googleapis.com
   ```

3. **Permission Denied**
   - Check service account permissions
   - Verify Drive/Sheets sharing settings

4. **Database Connection Issues**
   - Verify Cloud SQL instance is running
   - Check connection string format

5. **Redis Connection Issues**
   - Ensure Memorystore instance is in same region
   - Check VPC network configuration

### Getting Help

- Check the application logs: `gcloud run services logs read rag-system --region us-central1`
- Test individual components using the health endpoints
- Verify all environment variables are set correctly
- Ensure all Google Cloud APIs are enabled

## 🎉 Next Steps

Once setup is complete:

1. **Upload Documents**: Add files to your Google Drive folder
2. **Test Queries**: Use the API or web interface to ask questions
3. **Monitor Logs**: Check Google Sheets for query logs
4. **Scale Up**: Adjust Cloud Run settings based on usage
5. **Customize**: Modify prompts and settings for your use case

Your Advanced RAG System is now ready for production use! 🚀

## 📚 Additional Resources

- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Google Drive API](https://developers.google.com/drive/api)
- [Google Sheets API](https://developers.google.com/sheets/api)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

**Need help?** Create an issue in the repository or check the troubleshooting section above.
