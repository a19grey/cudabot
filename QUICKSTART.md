# Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Setup (First Time Only)
```bash
# Setup CUDA-Q target (crawls docs, creates embeddings)
./run.sh setup
```

### Step 2: Start Chatting
```bash
# Interactive chat with CUDA-Q assistant
./run.sh chat
```

### Step 3: Ask Questions!
```
cuda_q> How do I create a quantum circuit?
cuda_q> Show me an example of quantum gates
cuda_q> Generate code for quantum Fourier transform
cuda_q> What are CUDA-Q best practices?
```

## 🛠️ Commands

- `./run.sh setup` - Setup CUDA-Q documentation (first time only)
- `./run.sh chat` - Start interactive chat session
- `./run.sh info` - Show target information
- `./run.sh test` - Run validation tests

## 🔧 Manual Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Setup target
python src/main.py setup --target cuda_q

# Chat interactively
python src/main.py chat --target cuda_q

# Single query
python src/main.py chat --target cuda_q --query "How do I create a quantum circuit?"

# Show all available commands
python src/main.py --help
```

## 📚 Example Queries

### Basic Concepts
- "What is a qubit in CUDA-Q?"
- "Explain quantum gates"
- "How does quantum measurement work?"

### Code Examples
- "Show me how to create a quantum circuit"
- "Generate code for a Bell state"
- "Write a quantum Fourier transform"
- "Create a quantum kernel example"

### Practical Implementation
- "How do I compile CUDA-Q programs?"
- "What are the best practices for CUDA-Q?"
- "How do I handle quantum errors?"
- "Show me quantum algorithm patterns"

## 🎯 Adding New Targets

Want to use this with other documentation? Easy!

1. **Create target config:**
   ```bash
   cp config/targets/cuda_q.yaml config/targets/my_framework.yaml
   ```

2. **Edit the configuration:**
   - Set `base_url` to your documentation site
   - Update crawl patterns
   - Customize agent descriptions

3. **Setup and use:**
   ```bash
   python src/main.py setup --target my_framework
   python src/main.py chat --target my_framework
   ```

## 🔍 Troubleshooting

### Dependencies Issue
```bash
# If virtual environment missing
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Setup Issues
```bash
# Check target status
python src/main.py info --target cuda_q

# Force recrawl if needed
python src/main.py setup --target cuda_q --force-crawl
```

### Permission Errors
```bash
# Make scripts executable
chmod +x run.sh
chmod +x src/main.py
```

## 💡 Tips

- Use **specific questions** for better results
- Ask for **code examples** when you need implementations
- The system remembers **conversation history** during each session
- Type `history` in chat mode to see previous queries
- Type `help` in chat mode for available commands

## 🎉 You're Ready!

The AI Documentation Assistant is now ready to help you with CUDA-Q development. Happy coding! 🚀