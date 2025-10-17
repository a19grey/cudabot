# AI Documentation Assistant

A multi-agent AI system built with CrewAI that helps users interact with technical documentation through intelligent retrieval and code generation. Initially designed for CUDA-Q but extensible to any documentation target.

## Features

- **🔍 Intelligent Documentation Retrieval**: RAG-powered search through documentation
- **💻 Code Generation**: Contextual code examples based on documentation
- **✅ Code Validation**: Expert review and improvement suggestions
- **🎯 Multi-Target Support**: Configurable for different frameworks/platforms
- **🤖 CrewAI Agents**: Specialized AI agents for different tasks
- **📚 Vector Storage**: Efficient similarity search with ChromaDB

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                     │
├─────────────────────────────────────────────────────────────┤
│                    CrewAI Orchestration                     │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Query Agent     │  │ Code Agent      │  │ Expert Agent │ │
│  │ (Intent & RAG)  │  │ (Code Gen)      │  │ (Validation) │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                    RAG Pipeline Layer                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Embedding Store │  │ Vector Search   │  │ Context Mgmt │ │
│  │ (ChromaDB)      │  │ (Similarity)    │  │ (Relevance)  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│                   Knowledge Base Layer                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ Documentation   │  │ Code Examples   │  │ API Reference│ │
│  │ (Full Text)     │  │ (Patterns)      │  │ (Functions)  │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd cudabot

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup CUDA-Q Target

```bash
# Setup CUDA-Q documentation (initial crawl and processing)
python src/main.py setup --target cuda_q
```

This will:
- Crawl NVIDIA CUDA-Q documentation
- Process and chunk documents
- Generate embeddings
- Create vector store

### 3. Start Chatting

**Option A: Gradio Web UI (Recommended)**

```bash
# Launch the web-based chat interface
python launch_ui.py

# Or with custom settings
python launch_ui.py --port 7860 --share  # Create public share link
```

Then open your browser to `http://localhost:7860`

**Option B: Command Line Interface**

```bash
# Interactive chat mode
python src/main.py chat --target cuda_q

# Or single query
python src/main.py chat --target cuda_q --query "How do I create a quantum circuit?"
```

## Usage Examples

### Gradio Web UI

The Gradio interface provides a modern, user-friendly chat experience:

```bash
$ python launch_ui.py

🚀 Launching AI Documentation Assistant UI
============================================================
✅ Ready targets: cuda_q
🌐 Server will be available at http://0.0.0.0:7860
============================================================

Running on local URL:  http://127.0.0.1:7860
```

Features:
- 🎯 **Target Selection**: Choose from available documentation targets
- 💬 **Chat Interface**: Conversational Q&A with streaming responses
- 📚 **Context Display**: See relevant documentation and code examples
- 🔄 **History Management**: Clear and restart conversations
- 📱 **Responsive Design**: Works on desktop and mobile browsers

### Command Line Chat
```bash
$ python src/main.py chat --target cuda_q

🤖 Starting chat session with cuda_q assistant
Type 'quit', 'exit', or press Ctrl+C to end the session

cuda_q> How do I implement a quantum Fourier transform?
🔍 Processing query...

# Generated response with documentation context and code examples
```

### Single Query
```bash
$ python src/main.py chat --target cuda_q --query "Show me CUDA-Q kernel syntax"
```

### Target Management
```bash
# List available targets
python src/main.py info

# Get specific target info
python src/main.py info --target cuda_q

# Setup with specific options
python src/main.py setup --target cuda_q --force-crawl --max-concurrent 5
```

## Configuration

### Target Configuration

Targets are configured in `config/targets/{target_name}.yaml`. Example for CUDA-Q:

```yaml
target:
  name: "CUDA-Q"
  description: "NVIDIA CUDA-Q quantum computing platform"
  domain: "quantum_computing"

documentation:
  base_url: "https://nvidia.github.io/cuda-quantum/latest/"
  crawl_patterns:
    - "https://nvidia.github.io/cuda-quantum/latest/**/*.html"
  exclude_patterns:
    - "*/genindex.html"
    - "*/search.html"

agents:
  query_agent:
    role: "CUDA-Q Documentation Specialist"
    goal: "Find relevant CUDA-Q documentation and code examples"
    backstory: "Expert in quantum computing documentation"

  code_agent:
    role: "CUDA-Q Code Generator"
    goal: "Generate working CUDA-Q quantum computing code"
    backstory: "Senior quantum software engineer"

  validation_agent:
    role: "CUDA-Q Code Validator"
    goal: "Review code for correctness and best practices"
    backstory: "CUDA-Q expert with deep framework knowledge"
```

### Base Configuration

Global settings in `config/base_config.yaml`:

```yaml
platform:
  name: "AI Documentation Assistant"
  version: "1.0.0"

embedding:
  model: "sentence-transformers/all-MiniLM-L6-v2"
  chunk_size: 512
  chunk_overlap: 50
  similarity_threshold: 0.7

llm:
  provider: "openai"
  model: "gpt-4"
  temperature: 0.1
```

## Creating New Targets

To add support for a new framework/platform:

1. Create target configuration:
```bash
cp config/targets/cuda_q.yaml config/targets/my_target.yaml
# Edit the configuration for your target
```

2. Setup the target:
```bash
python src/main.py setup --target my_target
```

3. Start using:
```bash
python src/main.py chat --target my_target
```

## Project Structure

```
cudabot/
├── config/
│   ├── base_config.yaml          # Global configuration
│   └── targets/
│       └── cuda_q.yaml           # CUDA-Q target config
├── src/
│   ├── agents/                   # CrewAI agents
│   │   ├── query_agent.py
│   │   ├── code_agent.py
│   │   └── validation_agent.py
│   ├── crawlers/                 # Documentation crawling
│   │   └── web_crawler.py
│   ├── processing/               # Document processing
│   │   ├── document_processor.py
│   │   └── chunking.py
│   ├── embeddings/               # Embedding generation
│   │   ├── embedding_generator.py
│   │   └── vector_store.py
│   ├── retrieval/                # RAG pipeline
│   │   └── rag_pipeline.py
│   ├── orchestration/            # Main flow orchestration
│   │   └── crew_flow.py
│   ├── utils/                    # Utilities
│   │   └── target_manager.py
│   ├── config_loader.py          # Configuration management
│   ├── setup_pipeline.py         # Setup automation
│   ├── gradio_app.py             # Gradio web UI
│   └── main.py                   # CLI entry point
├── launch_ui.py                  # Gradio UI launcher
├── data/                         # Data storage
│   ├── raw/                      # Raw crawled documents
│   ├── processed/                # Processed documents & chunks
│   └── embeddings/               # Vector embeddings & store
├── tests/                        # Test suite
│   └── test_basic_functionality.py
├── requirements.txt              # Python dependencies
└── README.md                     # This file
```

## Testing

Run the test suite to verify functionality:

```bash
python tests/test_basic_functionality.py
```

## Development

### Adding New Agents

1. Create agent file in `src/agents/`
2. Implement atomic functions for the agent's tasks
3. Define CrewAI agent and task creation functions
4. Update orchestration flow to include new agent

### Extending RAG Pipeline

1. Add new retrieval strategies in `src/retrieval/rag_pipeline.py`
2. Implement new chunking strategies in `src/processing/chunking.py`
3. Add new embedding models in `src/embeddings/embedding_generator.py`

### Custom Crawlers

1. Implement crawler in `src/crawlers/`
2. Add crawler configuration to target config
3. Update setup pipeline to use new crawler

## Environment Variables

Optional environment variables:

```bash
export OPENAI_API_KEY="your-key"           # For LLM providers
export CUDA_VISIBLE_DEVICES="0"           # For GPU acceleration
export TMPDIR="/tmp/cudabot"               # Custom temp directory
```

## Dependencies

Key dependencies:
- **CrewAI**: Multi-agent orchestration
- **ChromaDB**: Vector database
- **Sentence Transformers**: Embedding generation
- **Gradio**: Web-based UI for chat interface
- **BeautifulSoup**: HTML parsing
- **Pydantic**: Data validation
- **PyYAML**: Configuration management

## Troubleshooting

### Setup Issues

```bash
# Check target status
python src/main.py info --target cuda_q

# Force recrawl if needed
python src/main.py setup --target cuda_q --force-crawl

# Clean and restart
python -c "from src.setup_pipeline import cleanup_target_data; cleanup_target_data('cuda_q', confirm=True)"
python src/main.py setup --target cuda_q
```

### Common Issues

1. **No documents found**: Check crawl patterns in target config
2. **Embedding errors**: Verify sentence-transformers installation
3. **ChromaDB issues**: Clear `data/embeddings/` directory
4. **Memory issues**: Reduce `chunk_size` and `max_concurrent` settings

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit pull request

## License

[License information here]

## Acknowledgments

- Built with CrewAI framework
- CUDA-Q documentation from NVIDIA
- Sentence Transformers for embeddings
- ChromaDB for vector storage