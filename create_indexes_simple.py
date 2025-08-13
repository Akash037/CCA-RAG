#!/usr/bin/env python3
"""
Script to create Vertex AI Vector Search indexes for the RAG system.
Simplified version that doesn't require bucket creation.
"""

from google.cloud import aiplatform
import os
import sys

def main():
    print("🔧 Vertex AI Index Creator for RAG System")
    print("=" * 50)
    
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
        alt_path = input("Enter alternative path to credentials file (or press Enter to skip): ").strip()
        if alt_path and os.path.exists(alt_path):
            creds_path = alt_path
        else:
            print("⚠️ Proceeding without explicit credentials file...")
            print("Make sure you're authenticated with: gcloud auth login")
    else:
        # Set credentials
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path
        print(f"✅ Using credentials from: {creds_path}")
    
    # Initialize Vertex AI
    print(f"🚀 Initializing Vertex AI for project: {PROJECT_ID}")
    try:
        aiplatform.init(project=PROJECT_ID, location=LOCATION)
        print("✅ Vertex AI initialized successfully!")
    except Exception as e:
        print(f"❌ Failed to initialize Vertex AI: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Check your project ID is correct")
        print("2. Ensure Vertex AI API is enabled:")
        print("   gcloud services enable aiplatform.googleapis.com")
        print("3. Check authentication:")
        print("   gcloud auth list")
        print("4. Verify billing is enabled")
        sys.exit(1)
    
    try:
        print("\n" + "="*50)
        print("📝 Creating Vector Search Indexes...")
        print("This may take a few minutes...")
        print("="*50)
        
        # Method 1: Try creating with minimal configuration
        print("\n📚 Creating Document Corpus...")
        
        try:
            # Use the REST API approach through aiplatform
            doc_index_config = {
                "display_name": "RAG Document Corpus",
                "description": "Main document knowledge base for RAG system",
                "metadata": {
                    "config": {
                        "dimensions": 768,
                        "algorithm_config": {
                            "tree_ah_config": {
                                "leaf_node_embedding_count": 1000,
                                "leaf_nodes_to_search_percent": 10
                            }
                        },
                        "distance_measure_type": "DOT_PRODUCT_DISTANCE"
                    }
                }
            }
            
            # Create using direct API call
            from google.cloud.aiplatform_v1 import IndexServiceClient
            from google.cloud.aiplatform_v1.types import Index
            
            client = IndexServiceClient()
            parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
            
            # Create Document Index
            print("   🔄 Submitting document corpus creation request...")
            doc_operation = client.create_index(
                parent=parent,
                index=Index(
                    display_name="RAG Document Corpus",
                    description="Main document knowledge base for RAG system",
                    metadata=doc_index_config["metadata"]
                )
            )
            
            print("   ✅ Document corpus creation started!")
            print(f"   Operation: {doc_operation.operation.name}")
            
            # Create Memory Index
            print("\n🧠 Creating Memory Corpus...")
            print("   🔄 Submitting memory corpus creation request...")
            
            memory_operation = client.create_index(
                parent=parent,
                index=Index(
                    display_name="RAG Memory Corpus", 
                    description="Conversation memory and context for RAG system",
                    metadata={
                        "config": {
                            "dimensions": 768,
                            "algorithm_config": {
                                "tree_ah_config": {
                                    "leaf_node_embedding_count": 500,
                                    "leaf_nodes_to_search_percent": 20
                                }
                            },
                            "distance_measure_type": "DOT_PRODUCT_DISTANCE"
                        }
                    }
                )
            )
            
            print("   ✅ Memory corpus creation started!")
            print(f"   Operation: {memory_operation.operation.name}")
            
            print("\n" + "="*60)
            print("🎉 SUCCESS! Index creation requests submitted!")
            print("="*60)
            
            print("\n⏳ Indexes are being created in the background...")
            print("This process typically takes 10-30 minutes to complete.")
            print("\n📍 Check status in Google Cloud Console:")
            print(f"https://console.cloud.google.com/vertex-ai/search?project={PROJECT_ID}")
            
            print("\n💡 Once indexes are ready, you can find their IDs in the console.")
            print("Look for indexes named:")
            print("- RAG Document Corpus")
            print("- RAG Memory Corpus")
            
            print("\n📝 Add the Index IDs to your .env file as:")
            print("RAG_DOCUMENT_CORPUS_ID=<document_corpus_index_id>")
            print("RAG_MEMORY_CORPUS_ID=<memory_corpus_index_id>")
            
        except Exception as api_error:
            print(f"❌ API method failed: {api_error}")
            print("\n💡 Trying alternative method...")
            
            # Fallback: Use console instructions
            print("\n" + "="*60)
            print("🔧 MANUAL SETUP REQUIRED")
            print("="*60)
            print("\nPlease create the indexes manually via Google Cloud Console:")
            print(f"1. Go to: https://console.cloud.google.com/vertex-ai/search?project={PROJECT_ID}")
            print("2. Click 'Create Index'")
            print("3. Create two indexes with these settings:")
            print("\n📚 Document Corpus:")
            print("   - Display Name: RAG Document Corpus")
            print("   - Description: Main document knowledge base for RAG system")
            print("   - Dimensions: 768")
            print("   - Algorithm: Tree-AH")
            print("   - Leaf Node Embedding Count: 1000")
            print("   - Leaf Nodes to Search: 10%")
            print("\n🧠 Memory Corpus:")
            print("   - Display Name: RAG Memory Corpus") 
            print("   - Description: Conversation memory and context for RAG system")
            print("   - Dimensions: 768")
            print("   - Algorithm: Tree-AH")
            print("   - Leaf Node Embedding Count: 500")
            print("   - Leaf Nodes to Search: 20%")
            
            print("\n📝 After creation, copy the Index IDs to your .env file:")
            print("RAG_DOCUMENT_CORPUS_ID=<your_document_index_id>")
            print("RAG_MEMORY_CORPUS_ID=<your_memory_index_id>")
            
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
        print("\n💡 If issues persist, try the manual console method above.")

if __name__ == "__main__":
    main()
