# Quick Reference: Hierarchical RAG + GREP System

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key (optional but recommended for better summaries)
export ANTHROPIC_API_KEY="your-key-here"
```

## Setup

```bash
# Run complete setup (includes hierarchical preprocessing)
./run.sh setup

# Or manually
python src/main.py setup --target cuda_q

# Force regenerate everything
python src/main.py setup --target cuda_q --force-crawl
```

## Usage

```bash
# Interactive chat (normal mode - clean output)
./run.sh chat

# Interactive chat (debug mode - see all agent thinking)
./run.sh chat --debug

# Single query
python src/main.py chat --target cuda_q --query "How do I use cudaq.sample?"
```

## Testing

```bash
# Run test suite
python test_hierarchical_system.py

# Check setup status
python src/main.py info --target cuda_q
```

## Architecture Overview

### Data Flow
```
User Query
    ↓
Load: doc_map.json, summaries.json, overview.txt
Initialize: ChromaDB (RAG) + GrepSearchTool
    ↓
Researcher Agent (Hybrid Search)
    - GREP tools: grep_search, find_code_examples, keyword_ranked_search
    - RAG tools: smart_search, evaluate_results
    ↓
Retrieve Documentation
    ↓
Generate Code (if needed)
    ↓
Validate Code
    ↓
Format & Return Response
```

### When to Use What

| Query Type | Tool | Example |
|------------|------|---------|
| Exact function name | GREP | "How to use cudaq.sample" |
| Error code | GREP | "CUDA error 404" |
| API syntax | GREP | "Show @cudaq.kernel examples" |
| Code examples | GREP | "Code using qvector" |
| Concept | RAG | "What is entanglement?" |
| How-to | RAG | "How do I create a circuit?" |
| Explanation | RAG | "Explain measurement" |
| Overview | RAG | "Overview of CUDA-Q" |

## File Locations

### Input
- `data/raw/{target}_docs.json` - Crawled documentation

### Processed
- `data/processed/{target}_processed_docs.json` - Processed documents
- `data/processed/{target}_chunks.json` - Document chunks
- `data/processed/{target}_doc_map.json` ✨ - Hierarchical structure
- `data/processed/{target}_summaries.json` ✨ - Document summaries
- `data/processed/{target}_overview.txt` ✨ - Project overview
- `data/processed/{target}_lookup.json` ✨ - Combined lookup

### Embeddings
- `data/embeddings/{target}_embedding_index.json` - Embedding index
- `data/embeddings/chroma.sqlite3` - Vector database

### Logs
- `logs/cudabot_{timestamp}.log` - Debug logs (when not in --debug mode)

## Key Components

### 1. Hierarchical Processor
**File**: `src/preprocessing/hierarchical_processor.py`
- Builds document hierarchy from URLs
- Generates summaries with Claude API
- Creates project overview

### 2. GREP Search Tool
**File**: `src/tools/grep_search.py`
- Exact keyword matching
- BM25 ranking
- Code example search

### 3. Routing Agent
**File**: `src/agents/routing_agent.py`
- Document navigation
- Summary search
- Path-based filtering

### 4. Researcher Agent
**File**: `src/agents/researcher_agent.py`
- Hybrid RAG + GREP
- 5 total tools
- Intelligent strategy selection

## Common Commands

```bash
# Setup
./run.sh setup                    # Initial setup
./run.sh setup --force-crawl      # Regenerate everything

# Chat
./run.sh chat                     # Normal mode
./run.sh chat --debug             # Debug mode

# Info
./run.sh info                     # Show all targets
python src/main.py info --target cuda_q  # Specific target

# Test
python test_hierarchical_system.py  # Run tests
./run.sh test                       # Validation
```

## Troubleshooting

### Missing hierarchical artifacts
```bash
# Regenerate
python src/main.py setup --target cuda_q --force-crawl
```

### GREP not working
- Check if `doc_map.json` exists in `data/processed/`
- System falls back to RAG-only if missing

### Slow setup
- Summaries generated with Claude API (one-time)
- Use `--skip-crawl` to avoid re-crawling docs

### No results
- Try debug mode: `./run.sh chat --debug`
- Check logs in `logs/` directory

## Performance Tips

1. **Use GREP for exact matches** - Faster than RAG
2. **Set ANTHROPIC_API_KEY** - Better summaries
3. **Don't force-crawl unnecessarily** - Caches are preserved
4. **Use --debug sparingly** - Normal mode is faster

## Dependencies

Core:
- crewai>=0.70.0
- chromadb>=0.5.0
- sentence-transformers>=3.0.0

New:
- rank-bm25>=0.2.2 (BM25 ranking)
- anthropic>=0.39.0 (Claude API)

## Documentation

- **Architecture**: `docs/HIERARCHICAL_RAG_ARCHITECTURE.md`
- **Implementation**: `IMPLEMENTATION_SUMMARY.md`
- **Original Spec**: `docs/improved_rag_grep_arch.md`
