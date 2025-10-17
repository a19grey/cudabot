#!/usr/bin/env python3
"""Test basic chat functionality without full CrewAI flow."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_chat():
    """Test basic chat functionality."""
    print("🧪 Testing basic chat functionality...")

    try:
        # Load configuration and vector store
        from config_loader import get_merged_config, get_data_paths
        from embeddings.vector_store import initialize_chroma_client, create_collection

        config = get_merged_config('cuda_q')
        data_paths = get_data_paths(config)

        # Initialize vector store
        client = initialize_chroma_client(data_paths['embeddings_dir'])
        collection = create_collection(client, "cuda_q_docs")

        print("1. ✅ Vector store loaded")

        # Test basic retrieval
        from retrieval.rag_pipeline import retrieve_context_for_query

        test_query = "What is CUDA-Q?"
        context, metadata = retrieve_context_for_query(collection, test_query)

        print("2. ✅ Context retrieval working")
        print(f"   Found {metadata['chunks_found']} chunks")
        print(f"   Context preview: {context[:200]}...")

        # Test query analysis
        from retrieval.rag_pipeline import preprocess_query
        query_analysis = preprocess_query(test_query)

        print("3. ✅ Query analysis working")
        print(f"   Intent: {query_analysis['intent']}")
        print(f"   Keywords: {query_analysis['keywords']}")

        print("\n🎉 Basic chat functionality working!")
        print("The system can:")
        print("  - Load vector store")
        print("  - Retrieve relevant context")
        print("  - Analyze user queries")

        print("\nNote: Full CrewAI agents need LLM setup (OpenAI API key)")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_chat()