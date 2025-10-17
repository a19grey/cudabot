# Hierarchical RAG + GREP Architecture

## Overview

This document describes the improved preprocessing and retrieval architecture that enhances the documentation assistant with hierarchical document mapping, intelligent routing, and hybrid RAG + GREP search capabilities.

## Architecture Components

### 1. Hierarchical Document Processor (`src/preprocessing/hierarchical_processor.py`)

Creates a multi-layered understanding of the documentation:

#### Document Relationship Map
- **Purpose**: Organizes documents in a hierarchical tree based on URL structure
- **Output**: `{target}_doc_map.json`
- **Structure**:
  ```json
  {
    "metadata": {...},
    "hierarchy": {
      "path/": {
        "_subdirs": {...},
        "_documents": [...]
      }
    },
    "documents": {
      "doc_0": {...},
      "doc_1": {...}
    }
  }
  ```

#### Document Summaries
- **Purpose**: 100-word summaries of each document for quick lookup
- **Output**: `{target}_summaries.json`
- **Generation**: Uses Claude Haiku for high-quality, concise summaries
- **Fallback**: Extracts first sentences if API unavailable

#### Project Overview
- **Purpose**: ~1000-word comprehensive overview of the entire project
- **Output**: `{target}_overview.txt`
- **Usage**: Injected into agent system prompts for context
- **Generation**: Uses Claude Sonnet to synthesize from all summaries

#### Combined Lookup
- **Purpose**: Single file with all metadata for agent access
- **Output**: `{target}_lookup.json`
- **Contains**: Overview, summaries, document count, hierarchy reference

### 2. GREP Search Tool (`src/tools/grep_search.py`)

Provides precise keyword-based search complementing RAG's semantic capabilities:

#### Features

**Exact Pattern Matching**:
```python
grep_search(
    pattern="cudaq.sample",
    case_sensitive=False,
    use_regex=True,
    context_chars=150
)
```

**BM25 Ranked Keyword Search**:
```python
keyword_search_ranked(
    query="quantum circuit measurement",
    top_k=10
)
```

**Code Example Finder**:
```python
find_code_examples(
    keyword="qvector",
    doc_ids=["doc_5", "doc_10"],
    max_examples=10
)
```

**Header Search**:
```python
search_headers(
    keyword="installation",
    doc_ids=None
)
```

#### When to Use GREP vs RAG

**Use GREP for**:
- Exact function/class names (e.g., `cudaq.sample`)
- Error codes or messages (e.g., `CUDA error 404`)
- Specific API terms (e.g., `@cudaq.kernel`)
- Code examples with particular imports
- Precise technical terminology

**Use RAG for**:
- Conceptual questions (e.g., "What is entanglement?")
- "How to" queries (e.g., "How do I create a quantum circuit?")
- Explanations and overviews
- Related topic discovery

### 3. Document Routing Agent (`src/agents/routing_agent.py`)

Intelligently narrows down document search space before detailed retrieval:

#### Tools

**explore_document_structure**:
- Navigates hierarchical document tree
- Shows available paths and documents
- Usage: `explore_document_structure("latest/api/")`

**search_summaries**:
- Keyword search across all document summaries
- Much faster than full-text search
- Returns relevant doc_ids with context
- Usage: `search_summaries("quantum gates hadamard")`

**get_document_list_by_path**:
- Get all doc_ids matching a path pattern
- Enables focused searches on specific sections
- Usage: `get_document_list_by_path("examples/")`

#### Routing Workflow

1. **Understand Query** → Identify what user needs
2. **Explore Structure** → Find relevant documentation sections
3. **Search Summaries** → Identify specific documents
4. **Get Doc IDs** → Compile targeted list (5-20 docs)
5. **Recommend Strategy** → GREP vs RAG, specific search terms

### 4. Enhanced Researcher Agent

Now supports hybrid RAG + GREP search:

#### Available Tools

**From RAG**:
- `smart_search` - Semantic vector search
- `evaluate_results` - Assess result quality

**From GREP**:
- `grep_search` - Exact keyword matching
- `find_code_examples` - Code block search
- `keyword_ranked_search` - BM25 ranking

#### Agent Intelligence

The researcher agent is prompted to:
- Choose GREP for exact matches (functions, errors, APIs)
- Choose RAG for concepts (explanations, tutorials, overviews)
- Iterate and refine searches
- Combine results from multiple strategies
- Present clean, user-friendly documentation

### 5. Project Context Manager (`src/utils/context_manager.py`)

Injects project overview into agent backstories:

```python
context_manager = ProjectContextManager(target_name, processed_dir)
enhanced_backstory = context_manager.enhance_agent_backstory(original_backstory)
```

Benefits:
- All agents understand what project they're documenting
- Consistent context across conversations
- Better query understanding
- Improved response relevance

## Setup Pipeline Integration

### Updated Setup Process

The setup pipeline now includes hierarchical preprocessing:

```
Step 1: Crawl Documentation
  → Downloads HTML pages from target site
  → Saves to {target}_docs.json

Step 2: Process Documents & Create Chunks
  → Extracts content, code blocks, headers
  → Splits into semantic chunks
  → Saves processed_docs.json and chunks.json

Step 2.5: Hierarchical Preprocessing ✨ NEW
  → Builds document relationship map
  → Generates summaries with Claude
  → Creates project overview
  → Saves doc_map.json, summaries.json, overview.txt, lookup.json

Step 3: Generate Embeddings
  → Creates vector embeddings for chunks
  → Saves embedding_index.json

Step 4: Create Vector Store
  → Populates ChromaDB with embeddings
  → Ready for RAG queries

Step 5: Validation
  → Checks all components present
  → Verifies setup complete
```

### Running Setup

```bash
# Full setup with hierarchical preprocessing
./run.sh setup

# Or manually
python src/main.py setup --target cuda_q

# Force regeneration of all artifacts
python src/main.py setup --target cuda_q --force-crawl
```

## Using the System

### Interactive Chat (Recommended)

```bash
# Normal mode (clean output)
./run.sh chat

# Debug mode (see all agent thinking)
./run.sh chat --debug
```

### Single Query

```bash
python src/main.py chat --target cuda_q --query "How do I use cudaq.sample?"
```

### Direct Python Usage

```python
from orchestration.crew_flow import run_documentation_assistant

result = run_documentation_assistant(
    target_name='cuda_q',
    query='Show me a 5-qubit entanglement example',
    debug_mode=False
)

print(result['documentation_context'])
print(result['generated_code'])
```

## Testing the System

Run the comprehensive test suite:

```bash
python test_hierarchical_system.py
```

Tests:
1. Hierarchical preprocessing artifacts
2. GREP search functionality
3. Hybrid RAG + GREP integration
4. Project overview context

## File Locations

### Input Data
- Raw docs: `data/raw/{target}_docs.json`

### Processed Data
- Processed docs: `data/processed/{target}_processed_docs.json`
- Chunks: `data/processed/{target}_chunks.json`
- **Document map**: `data/processed/{target}_doc_map.json` ✨
- **Summaries**: `data/processed/{target}_summaries.json` ✨
- **Overview**: `data/processed/{target}_overview.txt` ✨
- **Lookup**: `data/processed/{target}_lookup.json` ✨

### Embeddings
- Embeddings index: `data/embeddings/{target}_embedding_index.json`
- ChromaDB: `data/embeddings/chroma.sqlite3`

### Logs
- Debug logs: `logs/cudabot_{timestamp}.log`

## Performance Improvements

### Faster Searches
- **Document routing** narrows search space from 100s to 5-20 documents
- **Summary search** provides instant relevance check
- **GREP** for exact matches avoids slow semantic search
- **BM25** ranks keyword results efficiently

### Better Results
- **Hierarchical understanding** helps find correct sections
- **Hybrid RAG + GREP** combines semantic and exact matching
- **Project context** improves query understanding
- **Summaries** enable quick document assessment

### Cost Efficiency
- **Summary caching** prevents repeated API calls
- **Haiku for summaries** (cheap, fast)
- **Sonnet for overview** (better quality, one-time cost)
- **GREP first** for simple queries saves embedding lookups

## Dependencies

New dependencies added:
```
rank-bm25>=0.2.2      # BM25 ranking for keyword search
anthropic>=0.39.0     # Claude API for summarization
```

## Configuration

No configuration changes needed - the system automatically uses hierarchical preprocessing if artifacts are available.

To disable (fallback to basic RAG only):
- Don't run hierarchical preprocessing step
- System gracefully degrades to RAG-only mode

## Troubleshooting

### Missing Hierarchical Artifacts

**Problem**: `grep_tool not available` or `doc_map not found`

**Solution**:
```bash
# Regenerate hierarchical artifacts
python src/main.py setup --target cuda_q --force-crawl
```

### Slow Summary Generation

**Problem**: Setup takes a long time at hierarchical preprocessing

**Reason**: Generating summaries with Claude API for each document

**Solutions**:
- Set `ANTHROPIC_API_KEY` for faster Claude summarization
- Or: Use fallback mode (extracts first sentences, no API needed)
- Cache is preserved - only runs once unless force-crawled

### No GREP Results

**Problem**: GREP search returns no matches for known terms

**Possible Causes**:
- Case sensitivity: Try `case_sensitive=False`
- Typo in search term
- Term only in code examples: Use `find_code_examples` instead
- Document not in subset: Check `doc_ids` parameter

## Future Enhancements

Potential improvements:
1. **Graph-based relationships** - Link related documents
2. **Topic clustering** - Group documents by theme
3. **Query expansion** - Automatic synonym search
4. **Caching** - Cache frequent query results
5. **Analytics** - Track which documents are most useful
6. **Auto-routing** - ML model to predict best search strategy

## References

- Original architecture: `docs/improved_rag_grep_arch.md`
- CrewAI docs: https://docs.crewai.com/
- ChromaDB docs: https://docs.trychroma.com/
- BM25 algorithm: https://en.wikipedia.org/wiki/Okapi_BM25
