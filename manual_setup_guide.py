#!/usr/bin/env python3
"""
Quick guide to create Vertex AI indexes manually via console.
This is the most reliable method for initial setup.
"""

def main():
    print("🔧 Vertex AI Index Setup Guide")
    print("=" * 50)
    
    PROJECT_ID = input("Enter your GCP Project ID: ").strip()
    
    if not PROJECT_ID:
        print("❌ Project ID is required!")
        return
    
    print(f"\n✅ Project ID: {PROJECT_ID}")
    print("\n" + "="*60)
    print("📋 MANUAL SETUP INSTRUCTIONS")
    print("="*60)
    
    print(f"\n🌐 Step 1: Open Google Cloud Console")
    print(f"   URL: https://console.cloud.google.com/vertex-ai/search?project={PROJECT_ID}")
    
    print(f"\n📝 Step 2: Enable APIs (if not already done)")
    print(f"   Go to: https://console.cloud.google.com/apis/library?project={PROJECT_ID}")
    print("   Search for and enable: 'Vertex AI API'")
    
    print(f"\n🔨 Step 3: Create Document Corpus")
    print("   1. Click 'CREATE INDEX' button")
    print("   2. Fill in the details:")
    print("      - Display Name: RAG Document Corpus")
    print("      - Description: Main document knowledge base for RAG system")
    print("      - Region: us-central1")
    print("   3. Configure index:")
    print("      - Index Type: Vector Search") 
    print("      - Dimensions: 768")
    print("      - Distance Measure: DOT_PRODUCT_DISTANCE")
    print("      - Algorithm: TreeAH")
    print("      - Leaf node embedding count: 1000")
    print("      - Leaf nodes to search percent: 10")
    print("   4. Click 'CREATE'")
    print("   5. ⭐ COPY THE INDEX ID - you'll need this!")
    
    print(f"\n🧠 Step 4: Create Memory Corpus")
    print("   1. Click 'CREATE INDEX' again")
    print("   2. Fill in the details:")
    print("      - Display Name: RAG Memory Corpus")
    print("      - Description: Conversation memory and context for RAG system")
    print("      - Region: us-central1")
    print("   3. Configure index:")
    print("      - Index Type: Vector Search")
    print("      - Dimensions: 768") 
    print("      - Distance Measure: DOT_PRODUCT_DISTANCE")
    print("      - Algorithm: TreeAH")
    print("      - Leaf node embedding count: 500")
    print("      - Leaf nodes to search percent: 20")
    print("   4. Click 'CREATE'")
    print("   5. ⭐ COPY THE INDEX ID - you'll need this!")
    
    print(f"\n⏳ Step 5: Wait for Creation")
    print("   - Index creation takes 10-30 minutes")
    print("   - You'll see status in the console")
    print("   - Both indexes should show 'READY' when complete")
    
    print(f"\n📋 Step 6: Update Your .env File")
    print("   Add these lines to your .env file:")
    print("   RAG_DOCUMENT_CORPUS_ID=<your_document_index_id>")
    print("   RAG_MEMORY_CORPUS_ID=<your_memory_index_id>")
    
    print(f"\n💡 Tips:")
    print("   - Keep the Index IDs handy - they're long strings like:")
    print("     projects/123456789/locations/us-central1/indexes/1234567890123456789")
    print("   - You only need the last part (the number) for the .env file")
    print("   - If creation fails, check billing is enabled")
    
    print("\n" + "="*60)
    print("🎉 After completing these steps, your indexes will be ready!")
    print("="*60)
    
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
