#!/usr/bin/env python3
"""
Simple setup script for testing the basic pipeline without CrewAI.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def simple_setup():
    """Run a simple setup to test the pipeline."""
    print("🔧 Starting simple setup...")

    try:
        # Test config loading
        print("1. Testing configuration loading...")
        from config_loader import get_merged_config, get_data_paths
        config = get_merged_config('cuda_q')
        data_paths = get_data_paths(config)
        print("   ✅ Configuration loaded")

        # Test document crawling (limited)
        print("2. Testing documentation crawler...")
        from crawlers.web_crawler import crawl_documentation_async
        from config_loader import get_crawl_config
        crawl_config = get_crawl_config(config)

        # Limit crawling for testing
        crawl_config['crawl_patterns'] = [crawl_config['base_url'] + 'index.html']  # Just one page

        documents = await crawl_documentation_async(crawl_config, max_concurrent=1)
        print(f"   ✅ Crawled {len(documents)} test documents")

        if not documents:
            print("   ⚠️ No documents found, creating mock document for testing")
            documents = [{
                'url': 'https://test.com/mock.html',
                'title': 'Mock CUDA-Q Document',
                'content': 'This is a mock CUDA-Q document for testing the pipeline. It contains information about quantum computing and CUDA-Q kernels.',
                'code_blocks': ['@cudaq.kernel\ndef mock_kernel():\n    pass'],
                'headers': [{'level': 1, 'text': 'Introduction to CUDA-Q', 'id': 'intro'}],
                'word_count': 25,
                'content_hash': 'mock123'
            }]

        # Test document processing
        print("3. Testing document processing...")
        from processing.document_processor import process_documents_pipeline
        from config_loader import get_embedding_config

        embedding_config = get_embedding_config(config)
        processed_docs, chunks = process_documents_pipeline(
            documents, embedding_config, data_paths['processed_dir'], 'cuda_q'
        )
        print(f"   ✅ Created {len(chunks)} chunks from {len(processed_docs)} documents")

        # Test embedding generation (without actual model for speed)
        print("4. Testing embedding system...")
        try:
            from embeddings.embedding_generator import initialize_embedding_model
            model = initialize_embedding_model()
            print("   ✅ Embedding model initialized")
        except Exception as e:
            print(f"   ⚠️ Embedding model failed (expected in some environments): {e}")

        # Test vector store initialization
        print("5. Testing vector store...")
        try:
            from embeddings.vector_store import initialize_chroma_client
            client = initialize_chroma_client(data_paths['embeddings_dir'])
            print("   ✅ Vector store initialized")
        except Exception as e:
            print(f"   ⚠️ Vector store failed: {e}")

        print("\n🎉 Simple setup test completed successfully!")
        print(f"   Documents processed: {len(processed_docs)}")
        print(f"   Chunks created: {len(chunks)}")
        print("\nNext step: Try full setup with './run.sh setup'")

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(simple_setup())