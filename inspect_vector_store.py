#!/usr/bin/env python3
"""Inspect what's in the vector store."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from config_loader import get_merged_config, get_data_paths
from embeddings.vector_store import initialize_chroma_client, create_collection

def inspect_vector_store():
    """Show what's in the vector store."""
    print("🔍 Inspecting Vector Store\n")

    config = get_merged_config('cuda_q')
    data_paths = get_data_paths(config)

    client = initialize_chroma_client(data_paths['embeddings_dir'])
    collection = create_collection(client, "cuda_q_docs")

    # Get total count
    try:
        count = collection.count()
        print(f"📊 Total chunks in vector store: {count:,}\n")
    except Exception as e:
        print(f"❌ Error getting count: {e}\n")
        return

    if count == 0:
        print("⚠️  Vector store is empty! Run setup first.")
        return

    # Sample some documents
    print("📄 Sample documents in vector store:\n")

    try:
        # Get a few random samples
        results = collection.get(
            limit=10,
            include=['metadatas', 'documents']
        )

        if results and results['ids']:
            for i, (doc_id, metadata, document) in enumerate(zip(
                results['ids'],
                results['metadatas'],
                results['documents']
            ), 1):
                print(f"[{i}] Chunk ID: {doc_id}")
                print(f"    URL: {metadata.get('document_url', 'Unknown')}")
                print(f"    Title: {metadata.get('document_title', 'Unknown')}")
                print(f"    Section: {metadata.get('section_title', 'N/A')}")
                print(f"    Tokens: {metadata.get('token_count', 0)}")
                print(f"    Content preview: {document[:100]}...")
                print()

        # Check for releases page
        print("\n🔍 Searching for GitHub releases page...")
        releases_results = collection.get(
            where={"document_url": {"$contains": "github.com"}},
            include=['metadatas', 'documents']
        )

        if releases_results and releases_results['ids']:
            print(f"✅ Found {len(releases_results['ids'])} chunks from GitHub!\n")
            for i, (doc_id, metadata, document) in enumerate(zip(
                releases_results['ids'][:3],
                releases_results['metadatas'][:3],
                releases_results['documents'][:3]
            ), 1):
                print(f"[GitHub {i}]")
                print(f"    URL: {metadata.get('document_url', 'Unknown')}")
                print(f"    Title: {metadata.get('document_title', 'Unknown')}")
                print(f"    Tokens: {metadata.get('token_count', 0)}")
                print(f"    Content preview: {document[:150]}...")
                print()
        else:
            print("❌ No chunks from GitHub releases found!\n")
            print("This might be why the model says it doesn't have release info.")

    except Exception as e:
        print(f"❌ Error querying: {e}")
        import traceback
        traceback.print_exc()

    # Test a search
    print("\n🧪 Test Search: 'latest release'")
    try:
        from retrieval.rag_pipeline import preprocess_query, retrieve_relevant_chunks

        query = "What's in the latest release?"
        query_analysis = preprocess_query(query)

        chunks = retrieve_relevant_chunks(
            collection=collection,
            query_analysis=query_analysis,
            max_chunks=5,
            max_tokens=10000,
            similarity_threshold=0.5
        )

        print(f"Found {len(chunks)} chunks:\n")
        for i, chunk in enumerate(chunks, 1):
            metadata = chunk.get('metadata', {})
            print(f"[{i}] Similarity: {chunk.get('similarity_score', 0):.3f}")
            print(f"    URL: {metadata.get('document_url', 'Unknown')}")
            print(f"    Title: {metadata.get('document_title', 'Unknown')[:60]}...")
            print()

    except Exception as e:
        print(f"❌ Search error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_vector_store()
