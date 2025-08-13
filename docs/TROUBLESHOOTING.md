# GitHub Actions CI/CD Troubleshooting Guide

## 🚀 Overview
This document provides comprehensive troubleshooting steps for the Precision Farm RAG System's GitHub Actions CI/CD pipeline.

## 🔧 Common Issues and Solutions

### 1. Environment Variable Escaping Issues

**Problem**: `Bad syntax for dict arg` errors when passing environment variables to gcloud
**Solution**: Use file-based approach instead of command-line arguments

```yaml
# ❌ Problematic approach
--update-env-vars="KEY=${{ secrets.VALUE }}"

# ✅ Fixed approach  
cat > env_vars.txt << 'EOF'
KEY=${{ secrets.VALUE }}
EOF
gcloud run deploy --set-env-vars "$(tr '\n' ',' < env_vars.txt | sed 's/,$//')"
```

### 2. Service Account Authentication

**Problem**: Authentication failures in Cloud Run
**Cause**: Incorrect service account key handling
**Solution**: Multiple authentication methods implemented

```python
# Priority order:
1. GCP_SA_KEY_PATH (direct file path)
2. GCP_SA_KEY_BASE64 (base64 encoded key)
3. GOOGLE_APPLICATION_CREDENTIALS
4. Default ADC
```

### 3. Docker Build Failures

**Problem**: Package installation or dependency conflicts
**Solution**: Use specific package versions and multi-stage builds

```dockerfile
# Use tested package versions from requirements.txt
# Multi-stage build for smaller images
# Proper dependency caching
```

### 4. Cloud Run Deployment Timeouts

**Problem**: Deployment takes too long or fails
**Solutions**:
- Increase timeout to 300s
- Use health checks
- Implement proper logging
- Monitor resource usage

## 📋 Pre-Deployment Checklist

### GitHub Secrets
Ensure all required secrets are configured:

- [x] `GCP_PROJECT_ID`: Your Google Cloud Project ID
- [x] `GCP_SA_KEY`: Base64 encoded service account key
- [x] `DATABASE_URL`: PostgreSQL connection string
- [x] `REDIS_URL`: Redis connection string
- [x] `SECRET_KEY`: Application secret key
- [x] `RAG_DOCUMENT_CORPUS_ID`: Vertex AI document corpus
- [x] `RAG_MEMORY_CORPUS_ID`: Vertex AI memory corpus
- [x] `GOOGLE_DRIVE_FOLDER_ID`: Source documents folder
- [x] `GOOGLE_SHEETS_SPREADSHEET_ID`: Logging spreadsheet

### GCP Resources
Verify all resources are created and configured:

- [x] Vertex AI RAG Engine enabled
- [x] Document and Memory Corpus created
- [x] Cloud SQL PostgreSQL instance
- [x] Memorystore Redis instance
- [x] Artifact Registry repository
- [x] Cloud Run service permissions
- [x] Service account with required roles

### Local Testing
Before deployment, verify locally:

```bash
# Test Docker build
docker build -t rag-test .
docker run -p 8000:8000 rag-test

# Test health endpoint
curl http://localhost:8000/health

# Test environment variables
python -c "from app.core.config import settings; print('Config loaded successfully')"
```

## 🔍 Debugging Commands

### Check GitHub Actions Status
```python
import requests
response = requests.get('https://api.github.com/repos/Akash037/CCA-RAG/actions/runs')
latest = response.json()['workflow_runs'][0]
print(f"Status: {latest['status']} - {latest['conclusion']}")
```

### Check Cloud Run Service
```bash
gcloud run services list --region=us-central1
gcloud run services describe precision-farm-rag --region=us-central1
```

### Check Service Logs
```bash
gcloud logs read "resource.type=cloud_run_revision AND resource.labels.service_name=precision-farm-rag" --limit=50
```

### Test Service Health
```bash
SERVICE_URL=$(gcloud run services describe precision-farm-rag --region=us-central1 --format='value(status.url)')
curl -f "$SERVICE_URL/health"
```

## 🚨 Emergency Procedures

### Rollback Deployment
```bash
# List revisions
gcloud run revisions list --service=precision-farm-rag --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic precision-farm-rag --to-revisions=REVISION-NAME=100 --region=us-central1
```

### Manual Deployment
If GitHub Actions fails, deploy manually:

```bash
# Build and push image
docker build -t us-central1-docker.pkg.dev/PROJECT_ID/rag-system/precision-farm-rag:manual .
docker push us-central1-docker.pkg.dev/PROJECT_ID/rag-system/precision-farm-rag:manual

# Deploy to Cloud Run
gcloud run deploy precision-farm-rag \
  --image us-central1-docker.pkg.dev/PROJECT_ID/rag-system/precision-farm-rag:manual \
  --region us-central1 \
  --set-env-vars="ENVIRONMENT=production,DEBUG=false,..."
```

## 📊 Monitoring and Observability

### Health Checks
- Service health: `GET /health`
- Database health: `GET /health/db`
- Redis health: `GET /health/redis`
- Vertex AI health: `GET /health/vertex`

### Logs and Metrics
- Cloud Run logs: Google Cloud Console > Cloud Run > Logs
- Application logs: Structured JSON format
- Error tracking: Google Cloud Error Reporting
- Performance: Google Cloud Monitoring

### Alerts
Set up alerts for:
- Service downtime
- High error rates
- Memory/CPU usage
- Database connection issues
- API rate limits

## 🔄 Continuous Improvement

### Performance Optimization
- Monitor response times
- Optimize database queries
- Implement caching strategies
- Scale resources based on usage

### Security Updates
- Regularly update dependencies
- Rotate service account keys
- Monitor security alerts
- Review access permissions

### Feature Deployment
- Use feature flags
- Implement blue-green deployments
- Test in staging environment
- Monitor rollout metrics

## 📞 Support and Contact

For issues not covered in this guide:
1. Check GitHub Actions logs
2. Review Cloud Run service logs
3. Verify GCP resource status
4. Contact system administrator

---

*Last updated: 2025-01-13*
*Version: 1.0*
