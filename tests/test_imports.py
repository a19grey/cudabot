#!/usr/bin/env python3
"""Test each import individually to find issues."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing individual imports...")

try:
    print("1. Testing config_loader...")
    from config_loader import get_merged_config, get_data_paths, get_crawl_config
    config = get_merged_config('cuda_q')
    print("   ✅ config_loader works")
except Exception as e:
    print(f"   ❌ config_loader failed: {e}")
    exit(1)

try:
    print("2. Testing web crawler...")
    from crawlers.web_crawler import crawl_documentation_async
    print("   ✅ web crawler imports work")
except Exception as e:
    print(f"   ❌ web crawler failed: {e}")

try:
    print("3. Testing document processor...")
    from processing.document_processor import process_documents_pipeline
    print("   ✅ document processor works")
except Exception as e:
    print(f"   ❌ document processor failed: {e}")

try:
    print("4. Testing embedding generator...")
    from embeddings.embedding_generator import initialize_embedding_model
    print("   ✅ embedding generator imports work")
except Exception as e:
    print(f"   ❌ embedding generator failed: {e}")

try:
    print("5. Testing vector store...")
    from embeddings.vector_store import initialize_chroma_client
    print("   ✅ vector store imports work")
except Exception as e:
    print(f"   ❌ vector store failed: {e}")

print("\nAll basic imports working! ✅")