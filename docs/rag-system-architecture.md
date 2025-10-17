# RAG System Architecture

This document explains how the Retrieval-Augmented Generation (RAG) system works in the cudabot.

## Overview

The RAG system retrieves relevant chunks of documentation based on user queries and provides them as context to the LLM for generating answers.

---

## 🔢 Key Parameters

### RAG Retrieval Parameters
**Location**: `config/base_config.yaml`

```yaml
embedding:
  model: "sentence-transformers/all-MiniLM-L6-v2"
  chunk_size: 512              # Tokens per chunk
  chunk_overlap: 50            # Token overlap between chunks
  similarity_threshold: 0.6    # Minimum similarity score (0-1)
  max_results: 5               # Default max chunks to return
```

### Runtime Retrieval Parameters
**Location**: `src/retrieval/rag_pipeline.py` - `retrieve_relevant_chunks()`

```python
def retrieve_relevant_chunks(
    collection: chromadb.Collection,
    query_analysis: Dict[str, Any],
    max_chunks: int = 5,           # Top N chunks to retrieve
    max_tokens: int = 2000,        # Maximum total tokens in context
    similarity_threshold: float = 0.7  # Minimum similarity score
)
```

**Current Defaults:**
- **`max_chunks`**: `5` chunks
- **`max_tokens`**: `2000` tokens total
- **`similarity_threshold`**: `0.7` (70% similarity minimum)

---

## 📄 How Chunks Work

### 1. **Document Chunking** (`src/processing/chunking.py`)

When a document is processed:

```
Original Document (e.g., 5000 words)
    ↓
Split by sections using headers (H1, H2, H3, etc.)
    ↓
Split sections into chunks of ~512 tokens with 50 token overlap
    ↓
Extract code blocks separately
    ↓
Result: Multiple chunks (e.g., 30 chunks from one document)
```

**Chunk Structure:**
```python
DocumentChunk:
    content: str              # The actual text (512 tokens)
    metadata: {
        'document_url': str   # Original page URL
        'document_title': str # Page title
        'section_title': str  # Section within page
        'section_level': int  # Header level (1-6)
        'is_code': bool       # Is this a code chunk?
        'token_count': int    # Actual tokens in chunk
    }
    chunk_id: str             # Unique identifier
    token_count: int          # Number of tokens
    embedding_vector: List[float]  # 384-dim vector
```

### 2. **Chunk vs Full Page**

**❌ Does NOT load full pages**
**✅ Only retrieves specific chunks**

When a match is found:
1. Only the **matching chunk** (512 tokens) is retrieved
2. NOT the entire page
3. Multiple chunks from the same page can be retrieved if they match

**Example:**
```
Query: "How do I create a quantum circuit?"

Match Found:
  ✅ Chunk 3 from "quick_start.html" (512 tokens)
     Section: "Creating Your First Circuit"

  ✅ Chunk 7 from "examples.html" (480 tokens)
     Section: "Circuit Examples"

Total returned: 2 chunks, ~992 tokens
NOT: Full pages (which might be 5000+ tokens each)
```

---

## 🔍 Retrieval Process

### Step 1: Query Processing
**Location**: `src/retrieval/rag_pipeline.py` - `preprocess_query()`

```python
query = "How do I implement a Bell state?"

# Extracts:
query_analysis = {
    'intent': 'how_to',              # Detected intent
    'keywords': ['implement', 'bell', 'state'],
    'tech_terms': ['quantum'],
    'is_code_query': True,
    'difficulty_preference': 'intermediate'
}
```

### Step 2: Vector Search
**Location**: `src/embeddings/vector_store.py` - `hybrid_search()`

1. Generate embedding for query
2. Search ChromaDB for similar embeddings
3. Initial retrieval: `top_k * 2` (e.g., 10 candidates)
4. Filter by `similarity_threshold` (0.7)

### Step 3: Ranking & Selection
**Location**: `src/retrieval/rag_pipeline.py` - `rank_and_select_chunks()`

Chunks are ranked by:
- **Base similarity score** (from vector search)
- **Intent boost** (+0.2 for matching content type)
- **Code boost** (+0.1 if query is code-related)
- **Keyword boost** (+0.15 max based on matched keywords)
- **Difficulty match** (+0.1 if difficulty levels match)
- **Length penalty** (-0.1 for very short chunks)

### Step 4: Token Budget Management

```python
selected_chunks = []
total_tokens = 0
max_tokens = 2000

for chunk in ranked_chunks:
    chunk_tokens = chunk['metadata']['token_count']

    if (len(selected_chunks) < max_chunks and
        total_tokens + chunk_tokens <= max_tokens):
        selected_chunks.append(chunk)
        total_tokens += chunk_tokens
```

**Result**: Up to 5 chunks, not exceeding 2000 tokens total

---

## 📊 Example Query Flow

```
User Query: "Show me an example of a quantum Fourier transform"

1️⃣ Query Analysis:
   - Intent: example
   - Keywords: [quantum, fourier, transform]
   - Is code query: True

2️⃣ Vector Search (top_k=10):
   - Found 10 candidate chunks with similarity > 0.7

3️⃣ Ranking (with boosts):
   Chunk 1: similarity=0.89, intent_boost=0.2 (example), code_boost=0.1
            → Final score: 0.99

   Chunk 2: similarity=0.85, intent_boost=0.0, code_boost=0.1
            → Final score: 0.95

   Chunk 3: similarity=0.82, intent_boost=0.2, code_boost=0.1
            → Final score: 0.92

   [... 7 more chunks ...]

4️⃣ Selection (max_chunks=5, max_tokens=2000):
   ✅ Chunk 1: 485 tokens (total: 485)
   ✅ Chunk 2: 512 tokens (total: 997)
   ✅ Chunk 3: 420 tokens (total: 1417)
   ✅ Chunk 4: 395 tokens (total: 1812)
   ✅ Chunk 5: 178 tokens (total: 1990)
   ❌ Chunk 6: 510 tokens (would exceed 2000) → SKIPPED

5️⃣ Format for LLM:
   ## Context 1: Quantum Fourier Transform
   [485 tokens of content...]
   *Source: https://nvidia.github.io/cuda-quantum/latest/examples.html*

   ## Context 2: Building Kernels
   [512 tokens of content...]
   *Source: https://nvidia.github.io/cuda-quantum/latest/using/kernels.html*

   [... 3 more contexts ...]

6️⃣ Send to LLM:
   Context + User Query → GPT-4 → Generated Answer
```

---

## 🎛️ Tuning Parameters

### Where to Change Each Parameter

#### 1. **Chunking Parameters** (affects indexing)
**File**: `config/base_config.yaml`

```yaml
embedding:
  chunk_size: 512        # Change to 256, 512, 1024, etc.
  chunk_overlap: 50      # Change to 0, 50, 100, etc.
```

**⚠️ Requires Re-indexing:**
```bash
python src/main.py setup --target cuda_q --force-crawl
```

#### 2. **Retrieval Parameters** (affects queries)
**File**: `src/retrieval/rag_pipeline.py`

**Option A - Change defaults:**
```python
def retrieve_relevant_chunks(
    collection: chromadb.Collection,
    query_analysis: Dict[str, Any],
    max_chunks: int = 10,          # ← Change default
    max_tokens: int = 4000,        # ← Change default
    similarity_threshold: float = 0.6  # ← Change default
)
```

**Option B - Pass at runtime:**
```python
chunks = retrieve_relevant_chunks(
    collection=collection,
    query_analysis=query_analysis,
    max_chunks=10,              # Override
    max_tokens=4000,            # Override
    similarity_threshold=0.6    # Override
)
```

#### 3. **Similarity Threshold**
**File**: `config/base_config.yaml`

```yaml
embedding:
  similarity_threshold: 0.6   # Lower = more results (less strict)
                              # Higher = fewer results (more strict)
```

---

## 📈 Current Configuration Summary

| Parameter | Current Value | Location | Effect |
|-----------|---------------|----------|--------|
| **Chunk Size** | 512 tokens | `base_config.yaml` | Size of each text chunk |
| **Chunk Overlap** | 50 tokens | `base_config.yaml` | Overlap between chunks |
| **Max Chunks** | 5 | `rag_pipeline.py:129` | Top N chunks retrieved |
| **Max Tokens** | 2000 | `rag_pipeline.py:130` | Total token budget |
| **Similarity Threshold** | 0.7 | `rag_pipeline.py:131` | Min similarity score |
| **Config Threshold** | 0.6 | `base_config.yaml:9` | Default from config |

---

## 🔧 Common Adjustments

### Get More Context (More chunks)
```python
# In rag_pipeline.py:129
max_chunks: int = 10,          # Was 5
max_tokens: int = 4000,        # Was 2000
```

### Get Higher Quality Results (Stricter)
```python
similarity_threshold: float = 0.8  # Was 0.7
```

### Get More Results (Less strict)
```python
similarity_threshold: float = 0.5  # Was 0.7
```

### Larger Chunks (More context per chunk)
```yaml
# In base_config.yaml
embedding:
  chunk_size: 1024         # Was 512
  chunk_overlap: 100       # Was 50
```
⚠️ Requires re-running setup!

---

## 🎯 Recommendations

### Current Setup (Good for most queries)
- **5 chunks**, **2000 tokens** total
- Each chunk ~400 tokens average
- Covers 2-5 different sections/pages

### For Complex Queries (Need more context)
- **10 chunks**, **4000 tokens** total
- More comprehensive coverage
- Better for multi-step tutorials

### For Quick Answers (Less context needed)
- **3 chunks**, **1000 tokens** total
- Faster retrieval
- Good for simple "what is X?" queries

### For Code-Heavy Queries
- Keep **5 chunks** but increase `chunk_size` to **1024**
- Code examples often need more context
- Requires re-indexing

---

## 📚 Related Files

- **RAG Pipeline**: `src/retrieval/rag_pipeline.py`
- **Chunking**: `src/processing/chunking.py`
- **Embeddings**: `src/embeddings/embedding_generator.py`
- **Vector Store**: `src/embeddings/vector_store.py`
- **Config**: `config/base_config.yaml`
