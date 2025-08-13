#!/usr/bin/env python3
"""
Deployment Monitoring Script for Precision Farm RAG System
"""

import time
import requests
import sys
from datetime import datetime

def check_github_workflow(repo_url: str = "https://api.github.com/repos/Akash037/CCA-RAG/actions/runs"):
    """Check the latest GitHub Actions workflow status"""
    try:
        response = requests.get(repo_url)
        if response.status_code == 200:
            data = response.json()
            if data.get('workflow_runs'):
                latest_run = data['workflow_runs'][0]
                return {
                    'status': latest_run.get('status'),
                    'conclusion': latest_run.get('conclusion'),
                    'created_at': latest_run.get('created_at'),
                    'html_url': latest_run.get('html_url')
                }
    except Exception as e:
        print(f"Error checking GitHub workflow: {e}")
    return None

def check_cloud_run_service(service_url: str = None):
    """Check if the Cloud Run service is responding"""
    if not service_url:
        return None
        
    try:
        health_url = f"{service_url}/health"
        response = requests.get(health_url, timeout=10)
        return {
            'status_code': response.status_code,
            'healthy': response.status_code == 200,
            'response_time': response.elapsed.total_seconds()
        }
    except Exception as e:
        return {
            'status_code': None,
            'healthy': False,
            'error': str(e)
        }

def monitor_deployment():
    """Monitor the deployment process"""
    print("🚀 Monitoring RAG System Deployment")
    print("=" * 50)
    
    start_time = datetime.now()
    service_url = None
    
    while True:
        print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Checking status...")
        
        # Check GitHub Actions
        workflow_status = check_github_workflow()
        if workflow_status:
            status = workflow_status['status']
            conclusion = workflow_status['conclusion']
            
            print(f"📋 GitHub Actions: {status}")
            if conclusion:
                print(f"   Result: {conclusion}")
            
            if status == 'completed':
                if conclusion == 'success':
                    print("✅ Deployment completed successfully!")
                    # Try to get service URL from logs or provide default
                    service_url = "https://precision-farm-rag-YOUR_HASH.a.run.app"  # Will be updated in workflow
                    break
                else:
                    print(f"❌ Deployment failed with conclusion: {conclusion}")
                    print(f"🔗 Check logs: {workflow_status.get('html_url')}")
                    sys.exit(1)
        
        # If we have a service URL, check health
        if service_url:
            health_status = check_cloud_run_service(service_url)
            if health_status:
                if health_status['healthy']:
                    print(f"💚 Service health: OK (response time: {health_status['response_time']:.2f}s)")
                else:
                    error = health_status.get('error', 'Unknown error')
                    print(f"💔 Service health: FAILED - {error}")
        
        time.sleep(30)  # Check every 30 seconds
    
    # Final verification
    if service_url:
        print(f"\n🎯 Final Service Check...")
        health_status = check_cloud_run_service(service_url)
        if health_status and health_status['healthy']:
            print(f"✅ Service is live and healthy!")
            print(f"🌐 Service URL: {service_url}")
            print(f"🔍 Health check: {service_url}/health")
            print(f"📚 API docs: {service_url}/docs")
        else:
            print(f"⚠️  Service deployed but health check failed")
    
    end_time = datetime.now()
    duration = end_time - start_time
    print(f"\n⏱️  Total deployment time: {duration}")

if __name__ == "__main__":
    monitor_deployment()
