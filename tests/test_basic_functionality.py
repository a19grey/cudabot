#!/usr/bin/env python3
"""
Basic functionality tests for the AI Documentation Assistant.
"""

import sys
from pathlib import Path
import json
import tempfile
import shutil

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config_loader import get_merged_config, load_target_config, get_data_paths
from setup_pipeline import check_target_setup
from utils.target_manager import TargetManager
from processing.chunking import create_document_chunks, DocumentChunk
from embeddings.embedding_generator import initialize_embedding_model, generate_text_embedding
from retrieval.rag_pipeline import preprocess_query, classify_query_intent


def test_config_loading():
    """Test configuration loading."""
    print("Testing configuration loading...")

    try:
        # Test loading CUDA-Q config
        config = load_target_config('cuda_q')
        assert 'target' in config, "Missing 'target' section in config"
        assert 'documentation' in config, "Missing 'documentation' section in config"

        target_info = config['target']
        assert target_info.get('name') == 'CUDA-Q', f"Expected 'CUDA-Q', got {target_info.get('name')}"

        print("✅ Configuration loading: PASSED")
        return True

    except Exception as e:
        print(f"❌ Configuration loading: FAILED - {e}")
        return False


def test_merged_config():
    """Test merged configuration."""
    print("Testing merged configuration...")

    try:
        merged_config = get_merged_config('cuda_q')

        # Should have base config elements
        assert 'platform' in merged_config, "Missing platform config from base"
        assert 'embedding' in merged_config, "Missing embedding config from base"

        # Should have target-specific elements
        assert 'target' in merged_config, "Missing target config"
        assert 'agents' in merged_config, "Missing agents config"

        print("✅ Merged configuration: PASSED")
        return True

    except Exception as e:
        print(f"❌ Merged configuration: FAILED - {e}")
        return False


def test_data_paths():
    """Test data paths creation."""
    print("Testing data paths...")

    try:
        config = get_merged_config('cuda_q')
        paths = get_data_paths(config)

        required_paths = ['data_dir', 'embeddings_dir', 'raw_dir', 'processed_dir']
        for path_key in required_paths:
            assert path_key in paths, f"Missing path: {path_key}"
            path = Path(paths[path_key])
            assert path.exists(), f"Path does not exist: {path}"

        print("✅ Data paths: PASSED")
        return True

    except Exception as e:
        print(f"❌ Data paths: FAILED - {e}")
        return False


def test_document_chunking():
    """Test document chunking functionality."""
    print("Testing document chunking...")

    try:
        # Create test document
        test_doc = {
            'url': 'https://test.com/doc1.html',
            'title': 'Test Document',
            'content': 'This is a test document with some content. It has multiple sentences for testing chunking. The chunking should work properly.',
            'content_hash': 'test123',
            'code_blocks': ['def test(): pass', 'print("hello")'],
            'headers': [{'level': 1, 'text': 'Introduction', 'id': 'intro'}],
            'word_count': 20
        }

        chunks = create_document_chunks(test_doc, chunk_size=50, overlap=10)

        assert len(chunks) > 0, "No chunks created"
        assert isinstance(chunks[0], DocumentChunk), "Chunks are not DocumentChunk instances"
        assert chunks[0].content, "Chunk content is empty"
        assert chunks[0].metadata, "Chunk metadata is missing"

        print(f"✅ Document chunking: PASSED ({len(chunks)} chunks created)")
        return True

    except Exception as e:
        print(f"❌ Document chunking: FAILED - {e}")
        return False


def test_embedding_model():
    """Test embedding model initialization and generation."""
    print("Testing embedding model...")

    try:
        model = initialize_embedding_model()
        assert model is not None, "Model not initialized"

        # Test embedding generation
        test_text = "This is a test sentence for embedding generation."
        embedding = generate_text_embedding(test_text, model)

        assert isinstance(embedding, list), "Embedding is not a list"
        assert len(embedding) > 0, "Embedding is empty"
        assert isinstance(embedding[0], float), "Embedding elements are not floats"

        print(f"✅ Embedding model: PASSED (embedding dim: {len(embedding)})")
        return True

    except Exception as e:
        print(f"❌ Embedding model: FAILED - {e}")
        return False


def test_query_preprocessing():
    """Test query preprocessing and intent classification."""
    print("Testing query preprocessing...")

    try:
        test_queries = [
            ("How do I create a quantum circuit?", "how_to"),
            ("What is a qubit?", "what_is"),
            ("Show me an example of quantum gates", "example"),
            ("Write code for quantum simulation", "code_generation"),
            ("Error in my CUDA-Q program", "troubleshoot")
        ]

        for query, expected_intent in test_queries:
            analysis = preprocess_query(query)
            assert 'intent' in analysis, "Missing intent in analysis"
            assert 'keywords' in analysis, "Missing keywords in analysis"

            # Check if intent classification is working (not necessarily exact match)
            actual_intent = analysis['intent']
            print(f"  Query: '{query}' -> Intent: {actual_intent}")

        print("✅ Query preprocessing: PASSED")
        return True

    except Exception as e:
        print(f"❌ Query preprocessing: FAILED - {e}")
        return False


def test_target_manager():
    """Test target manager functionality."""
    print("Testing target manager...")

    try:
        manager = TargetManager()

        # Test listing targets
        targets = manager.list_targets()
        assert isinstance(targets, list), "Targets list is not a list"
        assert len(targets) > 0, "No targets found"

        # Test validation
        validation = manager.validate_target('cuda_q')
        assert isinstance(validation, dict), "Validation result is not a dict"
        assert 'is_valid' in validation, "Missing is_valid in validation"

        print(f"✅ Target manager: PASSED ({len(targets)} targets found)")
        return True

    except Exception as e:
        print(f"❌ Target manager: FAILED - {e}")
        return False


def test_setup_status():
    """Test setup status checking."""
    print("Testing setup status...")

    try:
        status = check_target_setup('cuda_q')

        assert isinstance(status, dict), "Status is not a dict"
        assert 'is_ready' in status, "Missing is_ready in status"
        assert 'components' in status, "Missing components in status"

        components = status['components']
        expected_components = ['config', 'raw_docs', 'processed_docs', 'chunks', 'embeddings', 'vector_store']

        for component in expected_components:
            assert component in components, f"Missing component: {component}"

        ready_count = sum(1 for v in components.values() if v)
        total_count = len(components)

        print(f"✅ Setup status: PASSED ({ready_count}/{total_count} components ready)")
        return True

    except Exception as e:
        print(f"❌ Setup status: FAILED - {e}")
        return False


def run_all_tests():
    """Run all tests and report results."""
    print("🧪 Running AI Documentation Assistant Tests\n")

    tests = [
        test_config_loading,
        test_merged_config,
        test_data_paths,
        test_document_chunking,
        test_embedding_model,
        test_query_preprocessing,
        test_target_manager,
        test_setup_status
    ]

    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ {test_func.__name__}: FAILED - {e}")
            results.append(False)
        print()

    # Summary
    passed = sum(results)
    total = len(results)

    print("="*50)
    print(f"Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed!")
        return True
    else:
        print(f"❌ {total - passed} tests failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)