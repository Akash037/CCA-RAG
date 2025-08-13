#!/usr/bin/env python3
"""
Script to create Vertex AI Vector Search indexes for the RAG system.
This is the most reliable way to create indexes, especially on Windows.
"""

from google.cloud import aiplatform
from google.cloud import storage
import os
import sys

def create_temp_bucket(project_id):
    """Create a temporary GCS bucket for index initialization."""
    bucket_name = f"{project_id}-rag-temp"
    
    try:
        # Initialize storage client
        storage_client = storage.Client(project=project_id)
        
        # Check if bucket already exists
        try:
            bucket = storage_client.bucket(bucket_name)
            if bucket.exists():
                print(f"✅ Using existing bucket: gs://{bucket_name}")
                return bucket_name
        except:
            pass
        
        # Create new bucket
        print(f"📦 Creating temporary bucket: gs://{bucket_name}")
        bucket = storage_client.create_bucket(bucket_name, location="us-central1")
        
        # Create an empty file for initialization
        blob = bucket.blob("init/empty.txt")
        blob.upload_from_string("# Temporary file for index initialization")
        
        print(f"✅ Bucket created successfully: gs://{bucket_name}")
        return bucket_name
        
    except Exception as e:
        print(f"⚠️ Could not create bucket: {e}")
        print("💡 Using alternative initialization method...")
        return None

def main():
    # Configuration
    PROJECT_ID = input("Enter your GCP Project ID: ").strip()
    LOCATION = "us-central1"
    
    if not PROJECT_ID:
        print("❌ Project ID is required!")
        sys.exit(1)
    
    # Check for credentials
    creds_path = "./credentials/rag-service-account.json"
    if not os.path.exists(creds_path):
        print(f"❌ Service account credentials not found at: {creds_path}")
        print("Please ensure you've downloaded the service account key file.")
        sys.exit(1)
    
    # Set credentials
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
    
    # Initialize Vertex AI
    print(f"🚀 Initializing Vertex AI for project: {PROJECT_ID}")
    try:
        aiplatform.init(project=PROJECT_ID, location=LOCATION)
    except Exception as e:
        print(f"❌ Failed to initialize Vertex AI: {e}")
        print("Please check:")
        print("1. Your project ID is correct")
        print("2. Vertex AI API is enabled")
        print("3. Your service account has proper permissions")
        sys.exit(1)
    
    # Create temporary bucket for initialization
    bucket_name = create_temp_bucket(PROJECT_ID)
    
    try:
        # Create Document Corpus
        print("\n📚 Creating Document Corpus...")
        
        if bucket_name:
            # Use bucket approach
            contents_uri = f"gs://{bucket_name}/init"
        else:
            # Use empty approach (will be populated later)
            print("🔄 Using direct creation method...")
            contents_uri = None
        
        if contents_uri:
            doc_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
                display_name="RAG Document Corpus",
                contents_delta_uri=contents_uri,
                dimensions=768,
                approximate_neighbors_count=150,
                leaf_node_embedding_count=1000,
                leaf_nodes_to_search_percent=10,
                distance_measure_type="DOT_PRODUCT_DISTANCE",
                description="Main document knowledge base for RAG system",
                sync=False  # Don't wait for completion to avoid timeout
            )
        else:
            # Alternative: Create empty index using brute force method
            doc_index = aiplatform.MatchingEngineIndex.create_brute_force_index(
                display_name="RAG Document Corpus",
                contents_delta_uri="gs://cloud-samples-data/ai-platform/feature_store/datasets/movie_prediction/entities.csv",  # Dummy data
                dimensions=768,
                distance_measure_type="DOT_PRODUCT_DISTANCE",
                description="Main document knowledge base for RAG system",
                sync=False
            )
        
        print(f"✅ Document Corpus created successfully!")
        print(f"   Display Name: {doc_index.display_name}")
        print(f"   Index ID: {doc_index.name.split('/')[-1]}")
        
        # Create Memory Corpus
        print("\n🧠 Creating Memory Corpus...")
        memory_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
            display_name="RAG Memory Corpus",
            contents_delta_uri=f"gs://{PROJECT_ID}-rag-empty/init",  # Will be updated later
            dimensions=768,
            approximate_neighbors_count=50,
            leaf_node_embedding_count=500,
            leaf_nodes_to_search_percent=20,
            distance_measure_type="DOT_PRODUCT_DISTANCE",
            description="Conversation memory and context for RAG system",
            sync=True  # Wait for completion
        )
        
        print(f"✅ Memory Corpus created successfully!")
        print(f"   Display Name: {memory_index.display_name}")
        print(f"   Index ID: {memory_index.name.split('/')[-1]}")
        
        # Extract just the index IDs
        doc_index_id = doc_index.name.split('/')[-1]
        memory_index_id = memory_index.name.split('/')[-1]
        
        print("\n" + "="*60)
        print("🎉 SUCCESS! Both indexes created successfully!")
        print("="*60)
        print("\n📝 Add these to your .env file:")
        print(f"RAG_DOCUMENT_CORPUS_ID={doc_index_id}")
        print(f"RAG_MEMORY_CORPUS_ID={memory_index_id}")
        print("\n📍 Full Resource Names (for reference):")
        print(f"Document Corpus: {doc_index.resource_name}")
        print(f"Memory Corpus: {memory_index.resource_name}")
        print("="*60)
        
        # Save to file for easy reference
        with open("index_ids.txt", "w") as f:
            f.write(f"RAG_DOCUMENT_CORPUS_ID={doc_index_id}\n")
            f.write(f"RAG_MEMORY_CORPUS_ID={memory_index_id}\n")
            f.write(f"\nDocument Corpus Resource: {doc_index.resource_name}\n")
            f.write(f"Memory Corpus Resource: {memory_index.resource_name}\n")
        
        print(f"\n💾 Index IDs also saved to: index_ids.txt")
        
    except Exception as e:
        print(f"\n❌ Error creating indexes: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Ensure your project ID is correct")
        print("2. Make sure Vertex AI API is enabled:")
        print("   gcloud services enable aiplatform.googleapis.com")
        print("3. Check your authentication:")
        print("   gcloud auth list")
        print("4. Verify billing is enabled for your project")
        print("5. Ensure your service account has these roles:")
        print("   - roles/aiplatform.user")
        print("   - roles/aiplatform.serviceAgent")
        sys.exit(1)

if __name__ == "__main__":
    print("🔧 Vertex AI Index Creator for RAG System")
    print("=" * 50)
    main()
