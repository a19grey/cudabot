# Aggressive Context Configuration

This document describes the aggressive context retrieval configuration for maximum documentation coverage.

## 📊 Configuration Changes

### Previous (Conservative) Settings
```yaml
chunk_size: 512 tokens        # Small chunks
chunk_overlap: 50 tokens      # Small overlap
max_chunks: 5                 # Top 5 chunks
max_tokens: 2000              # 2K total context
llm_max_tokens: 2000          # 2K response limit
```

### New (Aggressive) Settings
```yaml
chunk_size: 5000 tokens       # Large chunks (~10x larger)
chunk_overlap: 500 tokens     # Large overlap for continuity
max_chunks: 10                # Up to 10 chunks
max_tokens: 30000             # 30K total context (15x increase)
llm_max_tokens: 4000          # 4K response limit
```

## 🎯 What This Means

### Before (Conservative)
```
Query: "How to create quantum circuits?"

Retrieved:
  • Chunk 1: 485 tokens (small snippet)
  • Chunk 2: 512 tokens (small snippet)
  • Chunk 3: 420 tokens (small snippet)
  • Chunk 4: 390 tokens (small snippet)
  • Chunk 5: 193 tokens (small snippet)

Total: 5 chunks, ~2000 tokens
Coverage: Small snippets from different pages
```

### After (Aggressive)
```
Query: "How to create quantum circuits?"

Retrieved:
  • Chunk 1: 4850 tokens (entire section with context)
  • Chunk 2: 4920 tokens (complete tutorial)
  • Chunk 3: 4100 tokens (full API reference)
  • Chunk 4: 3800 tokens (comprehensive examples)
  • Chunk 5: 4500 tokens (related concepts)
  • Chunk 6: 3200 tokens (troubleshooting guide)

Total: 6 chunks, ~25,370 tokens
Coverage: Complete sections with full context around matches
```

## 📋 Changes Made

### 1. **Chunking Configuration** (`config/base_config.yaml`)
```yaml
embedding:
  chunk_size: 5000           # Was 512 (10x increase)
  chunk_overlap: 500         # Was 50 (10x increase)
  max_results: 10            # Was 5 (2x increase)
```

### 2. **Retrieval Limits** (`src/retrieval/rag_pipeline.py`)
```python
def retrieve_relevant_chunks(
    max_chunks: int = 10,      # Was 5
    max_tokens: int = 30000,   # Was 2000
    ...
)

def retrieve_context_for_query(
    max_chunks: int = 10,      # Was 5
    max_tokens: int = 30000,   # Was 2000
    ...
)
```

### 3. **Initial Candidate Retrieval**
```python
# Increased candidate pool for better selection
top_k=max_chunks * 3,  # Get 30 candidates initially (was 10)
```

### 4. **LLM Response Limit** (`config/base_config.yaml`)
```yaml
llm:
  max_tokens: 4000           # Was 2000
```

## 🔄 Required Steps to Apply

### ⚠️ **IMPORTANT: Must Re-index Everything**

The chunking changes require reprocessing all documents:

```bash
# 1. Clean existing data
rm -rf data/processed/cuda_q_chunks.json
rm -rf data/embeddings/cuda_q_*

# 2. Re-run setup with new chunking
source venv/bin/activate
python src/main.py setup --target cuda_q --force-crawl
```

**Why?**
- Chunk size changed from 512 → 5000 tokens
- All documents need to be re-chunked
- All embeddings need to be regenerated
- Vector store needs to be rebuilt

### Expected Re-indexing Time
```
Documents: 308 pages
Old chunks: ~9,166 chunks (512 tokens each)
New chunks: ~1,000 chunks (5000 tokens each)

Estimated time:
  - Chunking: ~2 minutes
  - Embeddings: ~15-20 minutes (1000 chunks)
  - Total: ~20-25 minutes
```

## 📈 Expected Results

### Query Performance
| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Chunks per query** | 5 | 6-10 | +2-5 chunks |
| **Tokens per query** | ~2,000 | ~25,000 | +12.5x |
| **Context coverage** | Snippets | Full sections | Complete |
| **Pages covered** | 3-5 | 6-10 | +2-5 pages |

### Example Context Sizes

**Small Query** (e.g., "What is CUDA-Q?")
- Before: 2 chunks, 1,000 tokens
- After: 2 chunks, 8,000 tokens

**Medium Query** (e.g., "How to implement Bell state?")
- Before: 5 chunks, 2,000 tokens
- After: 5 chunks, 22,000 tokens

**Complex Query** (e.g., "Explain quantum Fourier transform with examples and error handling")
- Before: 5 chunks, 2,000 tokens (incomplete)
- After: 10 chunks, 30,000 tokens (comprehensive)

## 💡 Benefits

### ✅ Advantages
1. **Complete Context**: Each chunk contains ~10x more context around the match
2. **Better Continuity**: Larger overlap (500 tokens) ensures no information gaps
3. **More Coverage**: Up to 10 chunks means covering more related topics
4. **Fewer Truncations**: Large chunks reduce mid-sentence cuts
5. **Better Code Examples**: Code blocks stay complete within chunks

### ⚠️ Considerations
1. **Storage**: Vector DB will be smaller (~1K chunks vs ~9K chunks)
2. **Memory**: Each query uses ~30K tokens of context (vs 2K)
3. **LLM Costs**: More input tokens per query (~15x increase)
4. **Processing Time**: Slightly longer embedding generation (larger chunks)
5. **Precision**: Larger chunks may include some less-relevant content

## 🎛️ Fine-Tuning Options

### If 30K is Too Much
```python
# In rag_pipeline.py
max_tokens: int = 20000,  # Reduce to 20K
```

### If You Want Even More Context
```python
# In rag_pipeline.py
max_chunks: int = 15,     # Allow up to 15 chunks
max_tokens: int = 50000,  # 50K tokens
```

### If Chunks Are Too Large
```yaml
# In base_config.yaml
embedding:
  chunk_size: 3000        # Reduce to 3K tokens per chunk
  chunk_overlap: 300      # Adjust overlap proportionally
```

## 📊 Context Window Limits

### Model Limits
| Model | Context Window | Usable for Input | Safe Context Budget |
|-------|----------------|------------------|---------------------|
| GPT-4 | 8,192 tokens | ~6,000 tokens | 30K too large! |
| GPT-4-32K | 32,768 tokens | ~28,000 tokens | ✅ 30K fits |
| GPT-4-Turbo | 128,000 tokens | ~120,000 tokens | ✅ 30K fits easily |
| Claude 2 | 100,000 tokens | ~95,000 tokens | ✅ 30K fits easily |

### ⚠️ **Important**: Update Model if Needed

If using standard GPT-4 (8K context), update to GPT-4-Turbo:

```yaml
# In base_config.yaml
llm:
  model: "gpt-4-turbo"     # or "gpt-4-turbo-preview"
  # or
  model: "gpt-4-32k"       # if you have access
```

## 🧪 Testing After Re-indexing

```bash
# Test a query
python src/main.py chat --target cuda_q --query "How do I create a quantum circuit with error correction?"

# Check chunk statistics
python -c "
import json
chunks = json.load(open('data/processed/cuda_q_chunks.json'))
print(f'Total chunks: {len(chunks)}')
print(f'Avg tokens: {sum(c[\"token_count\"] for c in chunks) / len(chunks):.0f}')
print(f'Max tokens: {max(c[\"token_count\"] for c in chunks)}')
print(f'Min tokens: {min(c[\"token_count\"] for c in chunks)}')
"
```

## 📚 Summary

**Configuration**: Aggressive context retrieval for maximum documentation coverage

**Key Numbers**:
- **5,000 tokens** per chunk (was 512)
- **30,000 tokens** total context (was 2,000)
- **10 chunks** maximum (was 5)

**Action Required**: Re-index all documentation with new chunking parameters

**Expected Benefit**: 12-15x more context per query, with complete sections instead of snippets
