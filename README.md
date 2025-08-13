# Advanced RAG System with Google Cloud Vertex AI

A production-ready Retrieval-Augmented Generation (RAG) system built with FastAPI, Google Cloud Vertex AI, and advanced memory management capabilities.

## 🌟 Features

### Core RAG Capabilities
- **Advanced Multi-Source Retrieval**: Semantic, keyword, and hybrid search across multiple corpora
- **Intelligent Query Processing**: LLM-powered query classification, expansion, and routing
- **Multi-Agent Response Generation**: Specialized agents for different query types (factual, conversational, analytical, multimodal)
- **Advanced Ranking & Reranking**: Sophisticated document scoring and relevance optimization

### Memory Management
- **Multi-Layer Memory Architecture**: 4-tier memory system for comprehensive context retention
- **Session Memory**: In-memory conversation context with real-time updates
- **Short-Term Memory**: Redis-based recent interaction caching with TTL management
- **Long-Term Memory**: Database-persisted user profiles and conversation history
- **Conversation Memory**: Vertex AI Memory Corpus integration for advanced conversation tracking

### Google Integrations
- **Google Drive Sync**: Intelligent document discovery and synchronization from Google Drive folders
- **Document Processing**: Support for multiple formats (PDF, DOCX, TXT, MD, HTML, Google Workspace files)
- **Google Sheets Logging**: Real-time query and response logging with analytics tracking
- **Google Cloud Vertex AI**: Latest 2025 RAG Engine with Memory Corpus and hybrid search

### Production Features
- **FastAPI Framework**: Modern async web framework with automatic API documentation
- **Cloud Run Deployment**: Serverless container deployment with auto-scaling
- **GitHub Actions CI/CD**: Automated testing, building, and deployment pipeline
- **Comprehensive Monitoring**: Health checks, metrics, and error tracking
- **WebSocket Support**: Real-time chat interactions
- **Security**: Authentication, authorization, and secure credential management

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │────│   FastAPI App   │────│  Memory Manager │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                         │
                                ▼                         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   RAG Service   │────│ Google Services │    │  Redis + SQLite │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                        │
        ▼                        ▼
┌─────────────────┐    ┌─────────────────────────────────────────┐
│  Vertex AI RAG  │    │  Google Drive + Google Sheets          │
│  Corpus System  │    │  Document Sync + Logging               │
└─────────────────┘    └─────────────────────────────────────────┘
```

### Memory Architecture
```
┌─────────────────────────────────────────────────────────┐
│                Advanced Memory Manager                  │
├─────────────────┬─────────────────┬─────────────────────┤
│ Session Memory  │ Short-term      │ Long-term Memory    │
│ (In-Memory)     │ Memory (Redis)  │ (Database)          │
│ - Current conv  │ - Recent inter  │ - User profiles     │
│ - User prefs    │ - Topic trends  │ - Conv summaries    │
│ - Context vars  │ - Search hist   │ - Learning data     │
└─────────────────┴─────────────────┴─────────────────────┘
                            │
                            ▼
                ┌─────────────────────────┐
                │  Conversation Memory    │
                │  (Vertex AI Corpus)     │
                │  - Vector embeddings    │
                │  - Semantic search      │
                │  - Context retrieval    │
                └─────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Poetry (for dependency management)
- Docker (for local development)
- Google Cloud Project with Vertex AI enabled
- Google Drive folder with documents
- Google Sheets spreadsheet for logging

### Setup

1. **Clone and setup the project**:
```bash
git clone <repository-url>
cd rag-system
chmod +x setup.sh
./setup.sh
```

2. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. **Set up Google Cloud credentials**:
```bash
# Place service account key in credentials/ directory
# Or use application default credentials
gcloud auth application-default login
```

4. **Start the development server**:
```bash
# Option 1: Direct Python
poetry run uvicorn app.main:app --reload

# Option 2: Docker Compose (recommended)
docker-compose up

# Option 3: Production-like with Docker
docker-compose --profile production up
```

5. **Access the application**:
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health
- Redis Commander: http://localhost:8081 (if using tools profile)

## 📝 API Usage

### Basic Query
```python
import httpx

response = httpx.post("http://localhost:8000/chat/query", json={
    "query": "What are the benefits of precision agriculture?",
    "session_id": "user_session_123",
    "user_id": "user_456",
    "max_results": 5,
    "include_sources": True
})

print(response.json())
```

### WebSocket Chat
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/session_123');

ws.onopen = function() {
    ws.send(JSON.stringify({
        query: "Hello, what can you help me with?",
        user_id: "user_123"
    }));
};

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    console.log('Response:', data);
};
```

### Memory Management
```python
# Get comprehensive memory context
response = httpx.get("http://localhost:8000/memory/context/session_123")

# Clear session memory
response = httpx.delete("http://localhost:8000/memory/session/session_123")

# Get memory statistics
response = httpx.get("http://localhost:8000/memory/stats")
```

### Document Synchronization
```python
# Trigger document sync
response = httpx.post("http://localhost:8000/documents/sync", json={
    "folder_id": "your_google_drive_folder_id",
    "background": True
})

# Check sync status
response = httpx.get("http://localhost:8000/documents/status")
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GOOGLE_CLOUD_PROJECT` | GCP Project ID | Required |
| `VERTEX_AI_LOCATION` | Vertex AI region | us-central1 |
| `RAG_DOCUMENT_CORPUS_ID` | Document corpus ID | Required |
| `RAG_MEMORY_CORPUS_ID` | Memory corpus ID | Required |
| `GOOGLE_DRIVE_FOLDER_ID` | Drive folder ID | Required |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | Sheets ID | Required |
| `DATABASE_URL` | Database connection | sqlite+aiosqlite:///./data/rag.db |
| `REDIS_URL` | Redis connection | redis://localhost:6379/0 |

### Google Cloud Setup

1. **Create Vertex AI RAG Corpora**:
```bash
# Document corpus for knowledge base
gcloud ai indexes create --display-name="rag-documents" \
    --metadata-schema-uri="gs://google-cloud-aiplatform/schema/metadataSchema/1.0.0" \
    --region=us-central1

# Memory corpus for conversations
gcloud ai indexes create --display-name="rag-memory" \
    --metadata-schema-uri="gs://google-cloud-aiplatform/schema/metadataSchema/1.0.0" \
    --region=us-central1
```

2. **Set up Google Drive API**:
   - Enable Google Drive API in GCP Console
   - Create OAuth 2.0 credentials or service account
   - Download credentials JSON file

3. **Set up Google Sheets API**:
   - Enable Google Sheets API in GCP Console
   - Use same credentials as Drive API
   - Create a spreadsheet and note its ID

## 🚢 Deployment

### Cloud Run Deployment

1. **Automated deployment**:
```bash
chmod +x deploy.sh
./deploy.sh production your-gcp-project-id
```

2. **Manual deployment**:
```bash
# Build and push image
gcloud builds submit --tag gcr.io/your-project/rag-system

# Deploy to Cloud Run
gcloud run deploy rag-system \
    --image gcr.io/your-project/rag-system \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

### GitHub Actions CI/CD

The project includes a complete CI/CD pipeline that:
- Runs code quality checks (Black, isort, flake8, mypy)
- Executes unit and integration tests
- Performs security scanning
- Builds and pushes Docker images
- Deploys to staging and production environments

Configure these GitHub secrets:
- `GCP_PROJECT_ID`
- `GCP_SA_KEY` (service account JSON)
- `DATABASE_URL`
- `REDIS_URL`
- And other environment-specific variables

## 🧪 Testing

### Run Tests
```bash
# All tests
poetry run pytest

# Unit tests only
poetry run pytest tests/unit/

# Integration tests
poetry run pytest tests/integration/

# With coverage
poetry run pytest --cov=app --cov-report=html
```

### Test Categories
- **Unit Tests**: Individual component testing with mocks
- **Integration Tests**: API endpoint and service integration testing
- **Performance Tests**: Load testing and performance benchmarks

## 📊 Monitoring and Analytics

### Health Checks
- `/health` - Basic health status
- `/health/detailed` - Comprehensive system metrics

### Analytics Dashboard
The system automatically logs to Google Sheets:
- Query and response data
- User interaction patterns
- Performance metrics
- Error tracking
- Usage analytics

### Monitoring
- Cloud Run metrics and logs
- Redis performance monitoring
- Database query performance
- Memory usage tracking

## 🔒 Security

### Authentication
- Optional JWT token authentication
- Service account-based GCP authentication
- Secure credential management

### Data Protection
- Environment variable encryption
- Secure API key handling
- Database connection security
- Redis AUTH support

## 🛠️ Development

### Project Structure
```
app/
├── core/           # Core configuration and utilities
├── models/         # Pydantic models and schemas
├── services/       # Business logic and external integrations
└── main.py         # FastAPI application
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
└── conftest.py     # Test configuration
```

### Code Quality
The project uses:
- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking
- **pre-commit** hooks for automated checks

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Run quality checks: `poetry run pre-commit run --all-files`
5. Submit a pull request

## 📚 Documentation

### API Documentation
- Interactive docs: `/docs` (Swagger UI)
- Alternative docs: `/redoc` (ReDoc)
- OpenAPI spec: `/openapi.json`

### Architecture Documentation
- Memory management patterns
- RAG pipeline design
- Integration patterns
- Deployment strategies

## 🔧 Troubleshooting

### Common Issues

1. **Google Cloud Authentication**:
```bash
gcloud auth application-default login
export GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"
```

2. **Redis Connection**:
```bash
# Check Redis is running
docker-compose ps redis
# View Redis logs
docker-compose logs redis
```

3. **Database Issues**:
```bash
# Reset development database
rm data/rag_dev.db
poetry run python -c "from app.core.database import database_manager; import asyncio; asyncio.run(database_manager.create_tables())"
```

4. **Memory Issues**:
```bash
# Check memory usage
curl http://localhost:8000/memory/stats
# Clear all sessions
curl -X DELETE http://localhost:8000/memory/session/all
```

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the documentation at `/docs`
- Review the troubleshooting section above

---

**Built with ❤️ using FastAPI, Google Cloud Vertex AI, and modern Python practices.**

- **Conversation Memory**: Persistent chat history (Vertex AI Memory Corpus)



### 🔍 Advanced RAG

- **Document Corpus**: Knowledge from Google Drive

- **Memory Corpus**: Conversation history and learned patterns

- **Hybrid Search**: Combines semantic and keyword search

- **Smart Ranking**: Context-aware result reranking

- **Multi-Modal**: Handle text, images, PDFs



### 🤖 AI Capabilities

- **Multi-Agent System**: Specialized agents for different query types

- **Personalization**: Adapts to user communication style

- **Learning**: Improves from user interactions

- **Confidence Scoring**: Reliability indicators

- **Source Attribution**: Transparent information sourcing



## Quick Start



1. **Setup Environment**

   ```bash

   pip install -r requirements.txt

   ```



2. **Configure GCP**

   ```bash

   gcloud auth application-default login

   ```



3. **Run Development Server**

   ```bash

   uvicorn main:app --reload

   ```



## Deployment



Deploy to Cloud Run with GitHub Actions:

```bash

git push origin main  # Triggers automatic deployment

```



## Project Structure



```

/

├── app/

│   ├── core/           # Configuration & settings

│   ├── services/       # Business logic

│   ├── models/         # Pydantic models

│   ├── api/           # API endpoints

│   └── utils/         # Utilities

├── tests/             # Test suite

├── deployment/        # Docker & Cloud Run configs

└── docs/             # Documentation

```



## Environment Variables



See `.env.example` for required configuration.



## License



MIT License

