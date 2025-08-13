# 🚨 DEPLOYMENT FAILURE ANALYSIS & SOLUTION

## Problem Summary

**Issue**: Cloud Run service deployment fails with "Service Unavailable" and container startup errors.

**Root Cause**: GitHub repository secrets are **NOT CONFIGURED**, causing all environment variables to be passed as empty values to Cloud Run.

## Error Analysis

### Container Logs Show:
```
pydantic.ValidationError: 7 validation errors for Settings
google_sheets_id
  Field required [type=missing, input_value={...}, input_type=dict]
database_url  
  Field required [type=missing, input_value={...}, input_type=dict]
secret_key
  Field required [type=missing, input_value={...}, input_type=dict]
google_drive_folder_id
  Field required [type=missing, input_value={...}, input_type=dict]
rag_memory_corpus_id
  Field required [type=missing, input_value={...}, input_type=dict]
```

### Infrastructure Status:
- ✅ GitHub Actions workflow: **SUCCESSFUL**
- ✅ Docker build/push: **SUCCESSFUL** 
- ✅ Cloud Run deployment: **SUCCESSFUL**
- ✅ Container image: **RUNNING**
- ❌ Application startup: **FAILED** (missing env vars)

## 🔧 SOLUTION: Configure GitHub Secrets

### Step 1: Access GitHub Repository Settings
1. Go to GitHub repository: `https://github.com/Akash037/CCA-RAG`
2. Click **Settings** tab
3. Click **Secrets and variables** → **Actions**
4. Click **New repository secret**

### Step 2: Add Required Secrets

**CRITICAL**: Add these 13 secrets exactly as shown:

| Secret Name | Value | Notes |
|-------------|-------|--------|
| `GCP_PROJECT_ID` | `cca-rag` | Google Cloud project ID |
| `SERVICE_NAME` | `precision-farm-rag` | Cloud Run service name |
| `REGION` | `us-central1` | GCP deployment region |
| `GCP_SA_KEY` | `{...full JSON...}` | Service account key JSON |
| `DATABASE_URL` | `postgresql+asyncpg://raguser:SecurePassword123!@/ragdb?host=/cloudsql/cca-rag:us-central1:rag-database` | PostgreSQL connection |
| `REDIS_URL` | `redis://10.236.14.75:6379/0` | Redis connection |
| `SECRET_KEY` | `p6AV5VCF1Kszf-hG3_09WAR1xIB4EvzYnoIS6HDZhiI` | App secret key |
| `VERTEX_CORPUS_ID` | `3379056517876547584` | Vertex AI corpus ID |
| `VERTEX_INDEX_ID` | `<get from Vertex AI console>` | Vector search index |
| `RAG_DOCUMENT_CORPUS_ID` | `3379056517876547584` | Document corpus |
| `RAG_MEMORY_CORPUS_ID` | `3379056517876547585` | Memory corpus |
| `GOOGLE_DRIVE_FOLDER_ID` | `1U0saoSD6e8fhLNcWc8LERC5kUtPtzvrA` | Drive folder |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | `1SD7d_rK0jplIuHbw8yHc0NrQW7qpNw9L0H7O-8RQhcQ` | Sheets ID |

### Step 3: Get Service Account Key
```bash
gcloud iam service-accounts keys create rag-service-account.json \
    --iam-account=rag-system-sa@cca-rag.iam.gserviceaccount.com

cat rag-service-account.json
```
Copy the entire JSON output as the `GCP_SA_KEY` secret.

### Step 4: Trigger New Deployment
After setting all secrets:
1. Make any small commit to trigger the workflow
2. Or manually trigger via GitHub Actions "Run workflow"

## Expected Timeline After Fix
1. **Immediate**: GitHub Actions starts with access to secrets
2. **2-3 minutes**: Container build/push completes
3. **1-2 minutes**: Cloud Run deploys with proper environment variables
4. **30 seconds**: Application starts successfully
5. **Total**: ~5 minutes from commit to working service

## Verification Steps
1. **Check GitHub Actions**: No more "Service Unavailable" in test step
2. **Test health endpoint**: `curl https://precision-farm-rag-329644318816.us-central1.run.app/health`
3. **Check logs**: No more pydantic validation errors
4. **Test API**: Access `/docs` endpoint for API documentation

## Prevention for Future
- Always verify secrets are configured before deploying
- Use the provided `debug_env.py` script to test environment variables
- Monitor the GitHub Secrets Setup documentation

---

**Next Steps**: Configure the GitHub secrets and the deployment will succeed immediately.
