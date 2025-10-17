#!/bin/bash
# Re-index CUDA-Q documentation with aggressive context settings
# This applies the new 5000 token chunk size and 30K token context window

echo "🔄 Re-indexing CUDA-Q documentation with aggressive context settings"
echo ""
echo "Configuration:"
echo "  • Chunk size: 5000 tokens (was 512)"
echo "  • Chunk overlap: 500 tokens (was 50)"
echo "  • Max chunks: 10 (was 5)"
echo "  • Max tokens: 30,000 (was 2,000)"
echo ""

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Clean old processed data and embeddings
echo ""
echo "🧹 Cleaning old chunks and embeddings..."
rm -f data/processed/cuda_q_chunks.json
rm -f data/processed/cuda_q_processed_docs.json
rm -f data/embeddings/cuda_q_*
rm -rf data/embeddings/*cuda_q*

echo "✅ Old data removed"
echo ""

# Re-run setup (will use existing crawled docs)
echo "🚀 Starting re-indexing process..."
echo "   (Using existing crawled docs from data/raw/cuda_q_docs.json)"
echo ""
python src/main.py setup --target cuda_q

echo ""
echo "✅ Re-indexing complete!"
echo ""

# Show statistics
echo "📊 New chunk statistics:"
python -c "
import json
from pathlib import Path

chunks_file = Path('data/processed/cuda_q_chunks.json')
if chunks_file.exists():
    chunks = json.load(open(chunks_file))
    tokens = [c['token_count'] for c in chunks]
    print(f'  Total chunks: {len(chunks)}')
    print(f'  Avg tokens per chunk: {sum(tokens) / len(tokens):.0f}')
    print(f'  Max tokens: {max(tokens)}')
    print(f'  Min tokens: {min(tokens)}')
    print(f'  Total tokens indexed: {sum(tokens):,}')
else:
    print('  ⚠️  Chunks file not found - indexing may have failed')
"

echo ""
echo "🎉 Ready to use! Try a query:"
echo "   python src/main.py chat --target cuda_q --query 'How do I create a quantum circuit?'"
