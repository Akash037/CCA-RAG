# 🔐 GitHub Secrets Setup Guide

## CRITICAL: Set These GitHub Secrets Before Deployment

Go to your GitHub repository → Settings → Secrets and variables → Actions → New repository secret

### Required Secrets:

```
GCP_PROJECT_ID
Value: cca-rag

GCP_SA_KEY
Value: <paste the entire JSON content from your service account key>

DATABASE_URL
Value: postgresql+asyncpg://raguser:SecurePassword123!@/ragdb?host=/cloudsql/cca-rag:us-central1:rag-database

REDIS_URL
Value: redis://10.236.14.75:6379/0

SECRET_KEY
Value: p6AV5VCF1Kszf-hG3_09WAR1xIB4EvzYnoIS6HDZhiI

RAG_DOCUMENT_CORPUS_ID
Value: 3379056517876547584

RAG_MEMORY_CORPUS_ID
Value: 3379056517876547585

GOOGLE_DRIVE_FOLDER_ID
Value: 1U0saoSD6e8fhLNcWc8LERC5kUtPtzvrA

GOOGLE_SHEETS_SPREADSHEET_ID
Value: 1SD7d_rK0jplIuHbw8yHc0NrQW7qpNw9L0H7O-8RQhcQ
```

## 🔑 Getting Your Service Account Key

In Google Cloud Shell, run:

```bash
# Create/download service account key
gcloud iam service-accounts keys create rag-service-account.json \
    --iam-account=rag-system-sa@cca-rag.iam.gserviceaccount.com

# Display the content to copy
cat rag-service-account.json
```

Copy the ENTIRE JSON output (including { and }) and paste it as the `GCP_SA_KEY` secret.

## ⚠️ Security Notes

- ✅ Environment files (.env*) are now properly excluded from git
- ✅ All sensitive data moved to GitHub secrets
- ✅ New secret key generated
- ✅ Safe template provided for local development

## 🚀 Deployment Process

1. Set all GitHub secrets above
2. Push code to main branch
3. GitHub Actions will automatically deploy to Cloud Run
4. Your API will be available at: https://advanced-rag-system-[random].a.run.app

## 🔍 Monitoring Deployment

- Watch deployment: GitHub → Actions tab
- Check logs: Click on the running workflow
- Get deployed URL: Will be shown in deployment output
