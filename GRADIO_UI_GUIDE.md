# Gradio UI Guide

This guide explains how to use the new Gradio-based conversational interface for the AI Documentation Assistant.

## Overview

The Gradio UI provides a modern, web-based chat interface that makes interacting with your documentation assistant easier and more intuitive than the command-line interface.

### Key Features

- **🎯 Target Selection**: Easy dropdown to switch between documentation targets
- **💬 Conversational Interface**: Natural chat-style Q&A
- **⚡ Streaming Responses**: See answers appear in real-time
- **📚 Rich Formatting**: Markdown support for code blocks and formatting
- **🔄 History Management**: Clear and restart conversations
- **📱 Responsive Design**: Works on desktop, tablet, and mobile
- **🌐 Shareable**: Option to create public share links

## Installation

### Option 1: Using the Installer Script (Recommended)

```bash
./install_gradio.sh
```

### Option 2: Manual Installation

```bash
pip install gradio>=4.0.0
```

Or update all dependencies:

```bash
pip install -r requirements.txt
```

## Launching the UI

### Basic Launch

```bash
python launch_ui.py
```

This will start the server on `http://localhost:7860`

### Custom Port

```bash
python launch_ui.py --port 8080
```

### Public Share Link

Create a temporary public URL (useful for remote access or sharing):

```bash
python launch_ui.py --share
```

This creates a public link like `https://xxxxx.gradio.live` that's valid for 72 hours.

### Custom Host

```bash
python launch_ui.py --host 127.0.0.1 --port 7860
```

### All Options

```bash
python launch_ui.py --help
```

## Using the Interface

### 1. Select a Target

When you first open the UI:
1. Look at the left sidebar for the "Target" dropdown
2. Select your documentation target (e.g., `cuda_q`)
3. The interface will show target information and example queries

### 2. Start Chatting

Type your question in the message box at the bottom and either:
- Press Enter to send
- Click the "Send 🚀" button

### 3. View Responses

Responses will appear in the chat window with:
- Relevant documentation snippets
- Generated code examples (when applicable)
- Code reviews and validation (when applicable)
- Natural language explanations

### 4. Manage Conversation

- **Clear Conversation**: Click "Clear 🗑️" to start fresh
- **Copy Response**: Use the copy button on individual messages
- **Scroll History**: Scroll through previous messages

## Example Queries

Try these types of questions:

### Documentation Questions
```
What is CUDA-Q?
How do I get started with quantum computing?
Explain quantum circuits
```

### Code Generation
```
Show me an example of a quantum circuit
Write code to implement a quantum Fourier transform
How do I create a quantum kernel?
```

### Best Practices
```
What are best practices for quantum programming?
How should I optimize my quantum code?
What are common pitfalls to avoid?
```

## Architecture

The Gradio UI is built on top of the existing infrastructure:

```
┌─────────────────────────────────────┐
│         Gradio Web Interface        │
│    (gradio_app.py / launch_ui.py)   │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      Existing Orchestration         │
│    (crew_flow.py / main.py)         │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
┌──────────────┐  ┌──────────────┐
│ CrewAI Agents│  │  RAG Pipeline│
└──────────────┘  └──────────────┘
```

### Key Components

1. **`src/gradio_app.py`**: Main Gradio application
   - Defines the `GradioDocAssistant` class
   - Handles UI logic and event handlers
   - Manages conversation state

2. **`launch_ui.py`**: Convenient launcher script
   - Command-line argument parsing
   - Quick startup

3. **Integration with Existing System**:
   - Uses `run_documentation_assistant()` for query processing
   - Leverages `format_assistant_response()` for output formatting
   - Integrates with target management and setup checking

## Customization

### Changing Theme

Edit `src/gradio_app.py`:

```python
with gr.Blocks(
    title="AI Documentation Assistant",
    theme=gr.themes.Base()  # Change to Base, Default, Glass, Monochrome, Soft
) as demo:
```

### Adjusting Chat Height

Modify the chatbot component:

```python
chatbot = gr.Chatbot(
    label="Conversation",
    height=600,  # Change height in pixels
    ...
)
```

### Streaming Speed

Adjust the streaming effect in the `chat()` method:

```python
chunk_size = 100  # Larger = faster chunks
time.sleep(0.005)  # Smaller = faster streaming
```

## Troubleshooting

### Port Already in Use

```bash
# Use a different port
python launch_ui.py --port 8080
```

### Target Not Ready

If you see "Target 'xxx' is not set up properly":

1. Exit the UI
2. Run setup:
   ```bash
   python src/main.py setup --target cuda_q
   ```
3. Relaunch the UI

### Gradio Not Found

```bash
# Install Gradio
pip install gradio>=4.0.0

# Or use the installer
./install_gradio.sh
```

### Slow Response Times

- The first query may be slower while models load
- Subsequent queries should be faster
- Check your API keys for LLM providers (if using external APIs)
- Consider using debug mode to see what's happening:
  ```python
  # In gradio_app.py, change:
  result = run_documentation_assistant(target_name, message, debug_mode=True)
  ```

### Interface Not Loading

1. Check that all dependencies are installed:
   ```bash
   pip install -r requirements.txt
   ```

2. Verify Python version (3.8+):
   ```bash
   python --version
   ```

3. Check for error messages in the console

## Advanced Usage

### Running as a Service

You can run the Gradio UI as a background service:

```bash
# Using nohup
nohup python launch_ui.py --host 0.0.0.0 --port 7860 > gradio.log 2>&1 &

# Using screen
screen -S gradio
python launch_ui.py
# Press Ctrl+A, D to detach
```

### Behind a Reverse Proxy

If running behind nginx or another reverse proxy:

```python
# In gradio_app.py, add to launch():
demo.launch(
    share=False,
    server_name="127.0.0.1",  # Local only
    server_port=7860,
    root_path="/assistant"  # If hosted at /assistant path
)
```

### Authentication (Optional)

Add basic authentication:

```python
# In gradio_app.py, modify launch():
demo.launch(
    share=False,
    auth=("username", "password"),  # Basic auth
    server_name="0.0.0.0",
    server_port=7860
)
```

## Comparison: CLI vs Gradio UI

| Feature | CLI | Gradio UI |
|---------|-----|-----------|
| Ease of Use | Moderate | Easy |
| Visual Appeal | Basic | Modern |
| Code Formatting | Limited | Rich markdown |
| Accessibility | Terminal only | Web browser |
| Remote Access | SSH required | Share links |
| Multi-user | No | Yes (with share) |
| History View | Limited | Full scrollable |
| Setup Required | None | Gradio package |

## Performance Tips

1. **Keep Browser Tab Active**: Some browsers throttle inactive tabs
2. **Use Local Deployment**: Faster than share links
3. **Clear Conversations**: Long histories may slow down the UI
4. **Optimize Target Setup**: Ensure vector stores are properly indexed

## Contributing

To contribute improvements to the Gradio UI:

1. Edit `src/gradio_app.py`
2. Test locally: `python launch_ui.py`
3. Consider adding features like:
   - Dark mode toggle
   - Export conversation history
   - Advanced search filters
   - Multi-target comparison
   - Bookmarked queries

## Support

For issues or questions:
1. Check this guide first
2. Review the main README.md
3. Check console output for errors
4. Open an issue on GitHub

---

**Happy chatting with your documentation!** 🤖📚
