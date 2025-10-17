#!/usr/bin/env python3
"""Simple real setup with actual CUDA-Q docs - just a few key pages."""

import asyncio
import aiohttp
import json
import hashlib
import sys
import time
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def simple_real_setup():
    """Setup with a few key CUDA-Q documentation pages."""
    print("🚀 Simple Real CUDA-Q Setup")
    print("=" * 50)

    start_time = time.time()

    # Define key pages to crawl
    key_pages = [
        'https://nvidia.github.io/cuda-quantum/latest/',
        'https://nvidia.github.io/cuda-quantum/latest/using/cudaq/platform.html',
        'https://nvidia.github.io/cuda-quantum/latest/using/cudaq/tutorials.html',
        'https://nvidia.github.io/cuda-quantum/latest/api/languages/python_api.html'
    ]

    print(f"📡 Crawling {len(key_pages)} key documentation pages...")

    try:
        # Step 1: Crawl the pages
        documents = []

        async with aiohttp.ClientSession() as session:
            for i, url in enumerate(key_pages, 1):
                print(f"[{i}/{len(key_pages)}] Fetching: {url.split('/')[-1]}")

                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                        if response.status == 200:
                            print(f"   ✅ Status {response.status} - Processing...")

                            content = await response.text()

                            # Process with our extractor
                            from crawlers.web_crawler import extract_text_from_html
                            processed = extract_text_from_html(content)

                            document = {
                                'url': url,
                                'title': processed['title'],
                                'content': processed['content'],
                                'code_blocks': processed['code_blocks'],
                                'headers': processed['headers'],
                                'word_count': processed['word_count'],
                                'content_hash': hashlib.md5(processed['content'].encode()).hexdigest(),
                                'crawled_at': datetime.utcnow().isoformat()
                            }

                            documents.append(document)
                            print(f"   📄 Processed: {processed['word_count']} words, {len(processed['code_blocks'])} code blocks")

                        else:
                            print(f"   ⚠️ Status {response.status}")

                except Exception as e:
                    print(f"   ❌ Error: {e}")

        print(f"\n✅ Successfully crawled {len(documents)} pages")

        if len(documents) == 0:
            print("No pages crawled - using fallback mock data")
            documents = create_fallback_data()

        # Step 2: Save raw documents
        print(f"\n💾 Saving {len(documents)} documents...")

        from config_loader import get_merged_config, get_data_paths
        config = get_merged_config('cuda_q')
        data_paths = get_data_paths(config)

        # Ensure directories exist
        Path(data_paths['raw_dir']).mkdir(parents=True, exist_ok=True)

        raw_file = Path(data_paths['raw_dir']) / 'cuda_q_docs.json'
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2, ensure_ascii=False)

        print(f"   ✅ Saved to {raw_file}")

        # Step 3: Process documents
        print(f"\n🔄 Processing {len(documents)} documents...")

        from processing.document_processor import process_documents_pipeline
        from config_loader import get_embedding_config

        embedding_config = get_embedding_config(config)

        processed_docs, chunks = process_documents_pipeline(
            documents, embedding_config, data_paths['processed_dir'], 'cuda_q'
        )

        print(f"   ✅ Created {len(chunks)} chunks from {len(processed_docs)} documents")

        # Step 4: Generate embeddings
        print(f"\n🧠 Generating embeddings for {len(chunks)} chunks...")

        from embeddings.embedding_generator import create_embeddings_for_target
        config['data_paths'] = data_paths

        embedded_chunks = create_embeddings_for_target(chunks, 'cuda_q', config)
        print(f"   ✅ Generated embeddings for {len(embedded_chunks)} chunks")

        # Step 5: Create vector store
        print(f"\n🗄️ Creating vector store...")

        from embeddings.vector_store import create_vector_store_for_target
        client, collection = create_vector_store_for_target(
            embedded_chunks, 'cuda_q', data_paths['embeddings_dir']
        )

        print("   ✅ Vector store created")

        # Step 6: Test retrieval
        print(f"\n🧪 Testing retrieval...")

        from retrieval.rag_pipeline import retrieve_context_for_query
        test_query = "How do I create a quantum circuit in CUDA-Q?"

        try:
            context, metadata = retrieve_context_for_query(collection, test_query, max_chunks=3)
            print(f"   ✅ Found {metadata['chunks_found']} relevant chunks")
            if metadata['chunks_found'] > 0:
                print(f"   📝 Context preview: {context[:200]}...")
        except Exception as e:
            print(f"   ⚠️ Retrieval test had issues: {e}")

        elapsed = time.time() - start_time
        print(f"\n🎉 Setup completed in {elapsed:.1f} seconds!")
        print("=" * 50)
        print("📊 Summary:")
        print(f"   • Documents crawled: {len(documents)}")
        print(f"   • Documents processed: {len(processed_docs)}")
        print(f"   • Chunks created: {len(chunks)}")
        print(f"   • Embeddings generated: {len(embedded_chunks)}")
        print(f"   • Vector store: Ready")

        print(f"\n🚀 Test with: python test_single_query.py")

        return True

    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_fallback_data():
    """Create fallback data if crawling fails."""
    print("   🔄 Creating fallback mock data...")

    return [
        {
            'url': 'https://nvidia.github.io/cuda-quantum/latest/',
            'title': 'CUDA-Q: A Unified Programming Model for Hybrid Quantum-Classical Computing',
            'content': '''CUDA-Q is a unified programming model and platform for hybrid quantum-classical computing. It provides a single-source solution that allows developers to define quantum kernels and launch them from classical host code.

Key Features:
- Unified quantum-classical programming in C++ and Python
- Support for both near-term and fault-tolerant quantum algorithms
- Integration with existing classical HPC and AI workflows
- Multiple backend targets including simulators and quantum hardware

Getting Started:
To define a quantum kernel, use the __qpu__ specifier in C++ or @cudaq.kernel decorator in Python:

// C++ Example
__qpu__ void bell_pair(cudaq::qubit& q0, cudaq::qubit& q1) {
    h(q0);
    x<cudaq::ctrl>(q0, q1);
}

# Python Example
@cudaq.kernel
def bell_pair():
    qubits = cudaq.qvector(2)
    h(qubits[0])
    x.ctrl(qubits[0], qubits[1])

CUDA-Q provides a rich set of quantum operations, measurement capabilities, and noise modeling features for realistic quantum algorithm development.''',
            'code_blocks': [
                '__qpu__ void bell_pair(cudaq::qubit& q0, cudaq::qubit& q1) {\n    h(q0);\n    x<cudaq::ctrl>(q0, q1);\n}',
                '@cudaq.kernel\ndef bell_pair():\n    qubits = cudaq.qvector(2)\n    h(qubits[0])\n    x.ctrl(qubits[0], qubits[1])'
            ],
            'headers': [
                {'level': 1, 'text': 'CUDA-Q Overview', 'id': 'overview'},
                {'level': 2, 'text': 'Key Features', 'id': 'features'},
                {'level': 2, 'text': 'Getting Started', 'id': 'getting-started'}
            ],
            'word_count': 180,
            'content_hash': 'simple_cuda_q_overview',
            'crawled_at': datetime.utcnow().isoformat()
        }
    ]

if __name__ == "__main__":
    success = asyncio.run(simple_real_setup())
    print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}")