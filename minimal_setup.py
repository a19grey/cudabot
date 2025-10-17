#!/usr/bin/env python3
"""
Minimal setup script that creates mock data for testing the system.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def minimal_setup():
    """Create minimal setup with mock data."""
    print("🔧 Creating minimal setup with mock data...")

    try:
        # Load configuration
        from config_loader import get_merged_config, get_data_paths, get_embedding_config
        config = get_merged_config('cuda_q')
        data_paths = get_data_paths(config)

        print("1. ✅ Configuration loaded")

        # Create mock raw documents
        mock_documents = [
            {
                'url': 'https://nvidia.github.io/cuda-quantum/latest/index.html',
                'title': 'CUDA-Q: A Unified Platform for Quantum Computing',
                'content': '''CUDA-Q is NVIDIA's platform for hybrid quantum-classical computing.

CUDA-Q Kernels are the fundamental building blocks for quantum programs. Here's how to define a simple kernel:

@cudaq.kernel
def simple_bell():
    qubits = cudaq.qvector(2)
    h(qubits[0])
    x.ctrl(qubits[0], qubits[1])

Quantum gates are operations that manipulate qubit states. Common gates include:
- Hadamard (h): Creates superposition
- CNOT (x.ctrl): Creates entanglement
- Pauli gates (x, y, z): Basic single-qubit operations

To run quantum programs, you can use cudaq.sample() or cudaq.observe() functions.

Best practices for CUDA-Q development:
1. Always use the @cudaq.kernel decorator
2. Handle measurement results properly
3. Consider noise models for realistic simulations''',
                'code_blocks': [
                    '@cudaq.kernel\ndef simple_bell():\n    qubits = cudaq.qvector(2)\n    h(qubits[0])\n    x.ctrl(qubits[0], qubits[1])',
                    'result = cudaq.sample(simple_bell)\nprint(result)'
                ],
                'headers': [
                    {'level': 1, 'text': 'CUDA-Q Introduction', 'id': 'intro'},
                    {'level': 2, 'text': 'Quantum Kernels', 'id': 'kernels'},
                    {'level': 2, 'text': 'Quantum Gates', 'id': 'gates'},
                    {'level': 2, 'text': 'Best Practices', 'id': 'practices'}
                ],
                'word_count': 150,
                'content_hash': 'mock_cuda_q_doc_1',
                'crawled_at': datetime.utcnow().isoformat()
            },
            {
                'url': 'https://nvidia.github.io/cuda-quantum/latest/examples.html',
                'title': 'CUDA-Q Examples and Tutorials',
                'content': '''This page contains examples of CUDA-Q quantum programs.

Quantum Fourier Transform Example:

@cudaq.kernel
def qft(qubits: cudaq.qvector):
    qubit_count = len(qubits)
    for i in range(qubit_count):
        h(qubits[i])
        for j in range(i + 1, qubit_count):
            angle = math.pi / (2**(j - i))
            r1.ctrl(angle, qubits[j], qubits[i])

Variational Quantum Eigensolver (VQE) example shows how to optimize quantum circuits.

For compilation, use: nvq++ -o program program.cpp
For execution with GPU: ./program --target nvidia''',
                'code_blocks': [
                    '@cudaq.kernel\ndef qft(qubits: cudaq.qvector):\n    qubit_count = len(qubits)\n    for i in range(qubit_count):\n        h(qubits[i])',
                    'nvq++ -o program program.cpp'
                ],
                'headers': [
                    {'level': 1, 'text': 'Examples', 'id': 'examples'},
                    {'level': 2, 'text': 'Quantum Fourier Transform', 'id': 'qft'},
                    {'level': 2, 'text': 'Compilation', 'id': 'compile'}
                ],
                'word_count': 80,
                'content_hash': 'mock_cuda_q_doc_2',
                'crawled_at': datetime.utcnow().isoformat()
            }
        ]

        # Save raw documents
        raw_file = Path(data_paths['raw_dir']) / 'cuda_q_docs.json'
        with open(raw_file, 'w', encoding='utf-8') as f:
            json.dump(mock_documents, f, indent=2, ensure_ascii=False)

        print(f"2. ✅ Created {len(mock_documents)} mock documents")

        # Process documents
        from processing.document_processor import process_documents_pipeline
        embedding_config = get_embedding_config(config)

        processed_docs, chunks = process_documents_pipeline(
            mock_documents, embedding_config, data_paths['processed_dir'], 'cuda_q'
        )

        print(f"3. ✅ Created {len(chunks)} chunks from {len(processed_docs)} documents")

        # Create embeddings (using a simple mock embedding for now)
        print("4. Creating mock embeddings...")

        # Add mock embeddings to chunks
        import random
        for chunk in chunks:
            # Mock 384-dimensional embedding
            chunk.embedding_vector = [random.random() for _ in range(384)]

        # Save chunks with embeddings
        from processing.chunking import save_chunks_to_file
        chunks_file = Path(data_paths['processed_dir']) / 'cuda_q_chunks.json'
        save_chunks_to_file(chunks, str(chunks_file))

        print(f"   ✅ Added mock embeddings to {len(chunks)} chunks")

        # Initialize vector store with mock data
        print("5. Setting up vector store...")
        try:
            from embeddings.vector_store import create_vector_store_for_target
            client, collection = create_vector_store_for_target(
                chunks, 'cuda_q', data_paths['embeddings_dir']
            )
            print("   ✅ Vector store created successfully")
        except Exception as e:
            print(f"   ⚠️ Vector store setup had issues: {e}")

        print("\n🎉 Minimal setup completed successfully!")
        print(f"   Documents: {len(processed_docs)}")
        print(f"   Chunks: {len(chunks)}")
        print(f"   Mock embeddings: ✅")
        print("\nYou can now test the chat functionality!")
        print("Try: source venv/bin/activate && python src/main.py chat --target cuda_q --query 'What is CUDA-Q?'")

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    minimal_setup()