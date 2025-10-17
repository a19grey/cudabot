#!/usr/bin/env python3
"""
Test script for the improved hierarchical RAG + GREP system.

Tests:
1. Hierarchical document map creation
2. Document summarization
3. Project overview generation
4. GREP search functionality
5. Hybrid RAG + GREP retrieval
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config_loader import get_merged_config, get_data_paths
from preprocessing.hierarchical_processor import (
    HierarchicalDocumentProcessor,
    load_doc_map,
    load_summaries,
    load_project_overview,
    load_lookup_data
)
from tools.grep_search import GrepSearchTool
import json


def test_hierarchical_artifacts(target_name='cuda_q'):
    """Test that hierarchical preprocessing artifacts exist and are valid."""
    print("="*60)
    print("TEST 1: Hierarchical Preprocessing Artifacts")
    print("="*60)

    config = get_merged_config(target_name)
    data_paths = get_data_paths(config)

    # Check for artifacts
    processed_dir = Path(data_paths['processed_dir'])

    artifacts = {
        'doc_map': processed_dir / f"{target_name}_doc_map.json",
        'summaries': processed_dir / f"{target_name}_summaries.json",
        'overview': processed_dir / f"{target_name}_overview.txt",
        'lookup': processed_dir / f"{target_name}_lookup.json"
    }

    print("\n📁 Checking for artifacts...")
    for name, path in artifacts.items():
        exists = path.exists()
        status = "✅" if exists else "❌"
        print(f"  {status} {name}: {path}")

        if exists and name == 'doc_map':
            with open(path, 'r') as f:
                data = json.load(f)
                doc_count = len(data.get('documents', {}))
                print(f"      → {doc_count} documents in map")

        if exists and name == 'summaries':
            with open(path, 'r') as f:
                data = json.load(f)
                summary_count = len(data)
                print(f"      → {summary_count} summaries")

        if exists and name == 'overview':
            with open(path, 'r') as f:
                overview = f.read()
                word_count = len(overview.split())
                print(f"      → {word_count} words in overview")

    return all(path.exists() for path in artifacts.values())


def test_grep_search_tool(target_name='cuda_q'):
    """Test GREP search functionality."""
    print("\n" + "="*60)
    print("TEST 2: GREP Search Tool")
    print("="*60)

    config = get_merged_config(target_name)
    data_paths = get_data_paths(config)

    # Load document map
    doc_map = load_doc_map(target_name, data_paths['processed_dir'])

    if not doc_map:
        print("❌ Document map not found")
        return False

    print("\n🔍 Initializing GREP tool...")
    grep_tool = GrepSearchTool(doc_map)
    print("✅ GREP tool initialized")

    # Test 1: Exact keyword search
    print("\n--- Test 2a: Exact keyword search for 'cudaq.sample' ---")
    matches = grep_tool.grep_search("cudaq.sample", case_sensitive=False, max_total_matches=5)
    print(f"Found {len(matches)} matches")
    if matches:
        print(f"First match: {matches[0].doc_title}")
        print(f"Context: ...{matches[0].context_before} [{matches[0].match_text}] {matches[0].context_after}...")

    # Test 2: Find code examples
    print("\n--- Test 2b: Find code examples with 'kernel' ---")
    examples = grep_tool.find_code_examples("kernel", max_examples=3)
    print(f"Found {len(examples)} code examples")
    if examples:
        print(f"First example from: {examples[0]['doc_title']}")

    # Test 3: BM25 ranked search
    print("\n--- Test 2c: BM25 ranked search for 'quantum circuit' ---")
    results = grep_tool.keyword_search_ranked("quantum circuit", top_k=5)
    print(f"Found {len(results)} ranked results")
    for i, (doc_id, score) in enumerate(results[:3], 1):
        doc = grep_tool.documents.get(doc_id, {})
        print(f"{i}. {doc.get('title', 'Unknown')} (score: {score:.2f})")

    return len(matches) > 0


def test_hybrid_search(target_name='cuda_q'):
    """Test hybrid RAG + GREP search through the researcher agent."""
    print("\n" + "="*60)
    print("TEST 3: Hybrid RAG + GREP Search")
    print("="*60)

    # This would require running the full crew, which is slow
    # For now, just verify the components are loadable
    from agents.researcher_agent import create_researcher_agent
    from embeddings.vector_store import initialize_chroma_client, create_collection
    from tools.grep_search import GrepSearchTool

    config = get_merged_config(target_name)
    data_paths = get_data_paths(config)

    print("\n🔧 Setting up hybrid search components...")

    # Initialize RAG
    print("  → Initializing RAG (vector store)...")
    chroma_client = initialize_chroma_client(data_paths['embeddings_dir'])
    collection = create_collection(chroma_client, f"{target_name}_docs")
    print(f"    ✅ Collection has {collection.count()} documents")

    # Initialize GREP
    print("  → Initializing GREP...")
    doc_map = load_doc_map(target_name, data_paths['processed_dir'])
    if doc_map:
        grep_tool = GrepSearchTool(doc_map)
        print(f"    ✅ GREP tool ready with {len(grep_tool.documents)} documents")
    else:
        grep_tool = None
        print("    ⚠️  GREP tool not available")

    # Create researcher agent with both tools
    print("  → Creating researcher agent...")
    researcher_agent = create_researcher_agent(collection, config, grep_tool=grep_tool)
    print(f"    ✅ Agent created with {len(researcher_agent.tools)} tools")

    # List available tools
    print("\n🛠️  Available search tools:")
    for tool in researcher_agent.tools:
        tool_name = getattr(tool, 'name', str(tool))
        print(f"    - {tool_name}")

    return True


def test_project_overview(target_name='cuda_q'):
    """Test project overview context."""
    print("\n" + "="*60)
    print("TEST 4: Project Overview Context")
    print("="*60)

    config = get_merged_config(target_name)
    data_paths = get_data_paths(config)

    overview = load_project_overview(target_name, data_paths['processed_dir'])

    if overview:
        word_count = len(overview.split())
        print(f"\n✅ Project overview loaded: {word_count} words")
        print("\n📄 First 200 characters:")
        print(overview[:200] + "...")
        return True
    else:
        print("\n❌ Project overview not found")
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("HIERARCHICAL RAG + GREP SYSTEM TEST SUITE")
    print("="*60)

    target_name = 'cuda_q'

    results = {
        'artifacts': test_hierarchical_artifacts(target_name),
        'grep': test_grep_search_tool(target_name),
        'hybrid': test_hybrid_search(target_name),
        'overview': test_project_overview(target_name)
    }

    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name.upper()}: {status}")

    all_passed = all(results.values())
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️  SOME TESTS FAILED")
    print("="*60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
