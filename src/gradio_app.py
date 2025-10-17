#!/usr/bin/env python3
"""
Gradio UI for the AI Documentation Assistant.
Provides a conversational chat interface with multi-target support.
"""

import gradio as gr
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Generator, Dict, Any
import time
import json
from datetime import datetime
import threading
import queue

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import get_merged_config, load_target_config
from orchestration.crew_flow import run_documentation_assistant, format_assistant_response
from setup_pipeline import check_target_setup
from main import list_available_targets


class GradioDocAssistant:
    """Gradio-based conversational interface for the documentation assistant."""

    def __init__(self):
        self.current_target: Optional[str] = None
        self.conversation_history: List[Tuple[str, str]] = []
        self.debug_logs: List[Dict[str, Any]] = []
        self.latest_log_file: Optional[str] = None

    def get_available_targets(self) -> List[str]:
        """Get list of available and ready targets."""
        targets = list_available_targets()
        ready_targets = []

        for target in targets:
            setup_status = check_target_setup(target)
            if setup_status['is_ready']:
                ready_targets.append(target)

        return ready_targets

    def get_target_info(self, target_name: str) -> str:
        """Get formatted information about a target."""
        if not target_name:
            return "Please select a target from the dropdown."

        try:
            config = load_target_config(target_name)
            target_info = config.get('target', {})

            info_parts = []
            info_parts.append(f"**Target:** {target_info.get('name', target_name)}")
            info_parts.append(f"**Description:** {target_info.get('description', 'No description available')}")
            info_parts.append(f"**Domain:** {target_info.get('domain', 'Unknown')}")

            doc_config = config.get('documentation', {})
            if doc_config.get('base_url'):
                info_parts.append(f"**Documentation:** {doc_config['base_url']}")

            agents = config.get('agents', {})
            info_parts.append(f"**Agents configured:** {len(agents)}")

            setup_status = check_target_setup(target_name)
            status_emoji = "✅" if setup_status['is_ready'] else "❌"
            info_parts.append(f"**Status:** {status_emoji} {'Ready' if setup_status['is_ready'] else 'Needs setup'}")

            return "\n\n".join(info_parts)

        except Exception as e:
            return f"Error loading target info: {e}"

    def select_target(self, target_name: str) -> Tuple[str, List]:
        """Handle target selection."""
        if not target_name:
            return "Please select a target.", []

        self.current_target = target_name
        self.conversation_history = []

        info = self.get_target_info(target_name)
        welcome_msg = f"""# Welcome to {target_name} Assistant! 🤖

{info}

---

You can now ask questions about {target_name}. I'll search the documentation, generate code examples, and provide helpful guidance.

**Example queries:**
- "How do I get started with {target_name}?"
- "Show me an example of [specific feature]"
- "What are the best practices for [topic]?"
"""
        return welcome_msg, []

    def chat(
        self,
        message: str,
        history: List[List[str]],
        target_name: str
    ) -> Generator[List[List[str]], None, None]:
        """
        Process a chat message and yield response with streaming effect.

        Args:
            message: User's message
            history: Chat history in Gradio format [[user_msg, bot_msg], ...]
            target_name: Selected target

        Yields:
            Updated history with streaming response
        """
        if not target_name:
            history.append([message, "❌ Please select a target first."])
            yield history
            return

        if not message.strip():
            yield history
            return

        # Check if target is ready
        setup_status = check_target_setup(target_name)
        if not setup_status['is_ready']:
            error_msg = f"❌ Target '{target_name}' is not set up properly. Please run setup first."
            history.append([message, error_msg])
            yield history
            return

        # Add user message and empty bot response
        history.append([message, ""])
        yield history

        # Initial processing message
        history[-1][1] = "🔍 Processing your query..."
        yield history

        try:
            # Get the output manager to find log file location
            from utils.output_manager import get_output_manager

            # Build conversation context from history
            conversation_context = ""
            if history:
                for user_msg, bot_msg in history[:-1]:  # Exclude the current message we just added
                    if user_msg and bot_msg:
                        conversation_context += f"User: {user_msg}\nAssistant: {bot_msg}\n\n"

            # Prepend context to current message if history exists
            full_message = message
            if conversation_context:
                full_message = f"Previous conversation:\n{conversation_context}\nCurrent question: {message}"

            # Create a queue for status updates
            status_queue = queue.Queue()
            result_container = {}

            # Define callback to update status in real-time
            def status_update_callback(status: str):
                """Push status updates to the queue."""
                status_queue.put(status)

            # Run assistant in a separate thread
            def run_assistant():
                try:
                    # Use debug_mode=False so logs are captured to file (for download)
                    # Status updates will still be shown in the UI via the callback
                    result = run_documentation_assistant(
                        target_name,
                        full_message,
                        debug_mode=False,
                        status_callback=status_update_callback
                    )
                    result_container['result'] = result
                    status_queue.put(None)  # Signal completion
                except Exception as e:
                    result_container['error'] = e
                    status_queue.put(None)  # Signal completion

            # Start the assistant thread
            thread = threading.Thread(target=run_assistant)
            thread.start()

            # Poll for status updates and yield them
            while True:
                try:
                    status = status_queue.get(timeout=0.1)
                    if status is None:  # Completion signal
                        break
                    history[-1][1] = status
                    yield history
                except queue.Empty:
                    # No new status, just yield current state to keep UI responsive
                    yield history

            # Wait for thread to complete
            thread.join()

            # Check for errors
            if 'error' in result_container:
                raise result_container['error']

            result = result_container['result']

            # Store the log file path from output manager
            output_mgr = get_output_manager()
            if output_mgr and output_mgr.log_file_path:
                self.latest_log_file = str(output_mgr.log_file_path)

            # Store debug log entry
            debug_entry = {
                "timestamp": datetime.now().isoformat(),
                "target": target_name,
                "user_message": message,
                "raw_result": result,
            }
            self.debug_logs.append(debug_entry)

            # Format the response
            response = format_assistant_response(result)

            # Store formatted response in debug log
            debug_entry["assistant_response"] = response

            # Improved streaming with word-by-word delivery while preserving newlines
            history[-1][1] = ""

            # Split by whitespace but preserve structure
            import re
            # Split on spaces but keep newlines attached to words
            tokens = re.split(r'(\s+)', response)

            for token in tokens:
                if token:  # Skip empty strings
                    history[-1][1] += token
                    yield history
                    # Only add delay for actual words, not whitespace
                    if not token.isspace():
                        time.sleep(0.02)

        except Exception as e:
            error_msg = f"❌ **Error processing query:**\n\n{str(e)}\n\nPlease try rephrasing your question."
            history[-1][1] = error_msg

            # Log the error
            debug_entry = {
                "timestamp": datetime.now().isoformat(),
                "target": target_name,
                "user_message": message,
                "error": str(e),
            }
            self.debug_logs.append(debug_entry)

            yield history

    def clear_conversation(self) -> Tuple[List, str]:
        """Clear the conversation history."""
        self.conversation_history = []
        return [], "Conversation cleared. Ask me anything!"

    def download_debug_log(self) -> Optional[str]:
        """Return the path to the actual log file with full agentic flow history."""
        # Return the latest log file from the output manager
        if self.latest_log_file and Path(self.latest_log_file).exists():
            return self.latest_log_file

        # Fallback: look for the most recent log file
        log_dir = Path("/root/cudabot/logs")
        if log_dir.exists():
            log_files = sorted(log_dir.glob("cudabot_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
            if log_files:
                return str(log_files[0])

        return None

    def create_interface(self) -> gr.Blocks:
        """Create the Gradio interface."""

        # Create a custom theme
        custom_theme = gr.themes.Base.from_hub("JohnSmith9982/small_and_pretty").set(
            body_background_fill="*neutral_50",
            body_text_color="*neutral_800",
            button_primary_background_fill="*primary_500",
            button_primary_text_color="white",
            input_background_fill="*neutral_50",
            input_background_fill_focus="*neutral_50",
        )

        with gr.Blocks(
            title="ChatterBot for CUDA-Q",
            theme=custom_theme
        ) as demo:

            gr.Markdown(
                """
                # ChatterBot for CUDA-Q

                Chat with your CUDA-Q documentation using AI-powered agents.
                """
            )

            with gr.Row():
                with gr.Column(scale=1):
                    # Target selection
                    gr.Markdown("### 🎯 Select Documentation Target")

                    available_targets = self.get_available_targets()

                    if not available_targets:
                        gr.Markdown(
                            """
                            ⚠️ **No targets are ready!**

                            Please run the setup first:
                            ```bash
                            python src/main.py setup --target <target_name>
                            ```
                            """
                        )
                        target_dropdown = gr.Dropdown(
                            choices=[],
                            label="Target",
                            interactive=False
                        )
                    else:
                        target_dropdown = gr.Dropdown(
                            choices=available_targets,
                            label="Target",
                            value=available_targets[0] if available_targets else None,
                            interactive=True
                        )

                    # Target info display
                    target_info = gr.Markdown(
                        label="Target Information",
                        value=self.get_target_info(available_targets[0]) if available_targets else ""
                    )

                    # Clear button moved to sidebar
                    clear_btn = gr.Button("Clear Conversation 🗑️", variant="secondary")

                    # Download agentic flow history button
                    download_btn = gr.Button("Download Agentic Flow History 📥", variant="secondary")
                    download_file = gr.File(label="Agentic Flow History", visible=False)

                    # Example queries with clickable buttons
                    gr.Markdown("### 💡 Quick Start Questions")

                    # Define example questions as variables to ensure button text matches query
                    example_Q1 = "Show me a 5 qubit state with Hadamard gate operators"
                    example_Q2 = "What's the difference between CUDA-Q, DGX Cloud, and cuQuantum?"
                    example_Q3 = "How to use VQE to solve energy of the H2O molecule?"
                    example_Q4 = "Is quantum mechanics, like, even real?"

                    example_btn1 = gr.Button(example_Q1, size="sm")
                    example_btn2 = gr.Button(example_Q2, size="sm")
                    example_btn3 = gr.Button(example_Q3, size="sm")
                    example_btn4 = gr.Button(example_Q4, size="sm")

                with gr.Column(scale=2):
                    # Chat interface
                    gr.Markdown("### 💬 Chat")

                    chatbot = gr.Chatbot(
                        label="Conversation",
                        height=500,
                        show_copy_button=True,
                        render_markdown=True
                    )

                    msg = gr.Textbox(
                        label="Your message",
                        placeholder="Ask a question about the documentation... (Press Enter to send)",
                        lines=1,
                        max_lines=1,
                        show_label=False
                    )

                    # Info message
                    info_box = gr.Markdown(
                        "Select a target and start chatting!",
                        visible=True
                    )

            # Event handlers
            def on_target_change(target):
                info, cleared_history = self.select_target(target)
                return info, cleared_history, info

            target_dropdown.change(
                fn=on_target_change,
                inputs=[target_dropdown],
                outputs=[target_info, chatbot, info_box]
            )

            # Handle message submission (Enter key)
            msg.submit(
                fn=self.chat,
                inputs=[msg, chatbot, target_dropdown],
                outputs=[chatbot]
            ).then(
                fn=lambda: gr.update(value=""),
                outputs=[msg]
            )

            # Clear conversation
            clear_btn.click(
                fn=self.clear_conversation,
                outputs=[chatbot, info_box]
            )

            # Download agentic flow history log
            def prepare_download():
                file_path = self.download_debug_log()
                if file_path:
                    return gr.File(value=file_path, visible=True)
                else:
                    return gr.File(value=None, visible=False)

            download_btn.click(
                fn=prepare_download,
                outputs=[download_file]
            )

            # Example button handlers - they set the message and trigger submission
            example_btn1.click(
                fn=lambda: example_Q1,
                outputs=[msg]
            ).then(
                fn=self.chat,
                inputs=[msg, chatbot, target_dropdown],
                outputs=[chatbot]
            ).then(
                fn=lambda: gr.update(value=""),
                outputs=[msg]
            )

            example_btn2.click(
                fn=lambda: example_Q2,
                outputs=[msg]
            ).then(
                fn=self.chat,
                inputs=[msg, chatbot, target_dropdown],
                outputs=[chatbot]
            ).then(
                fn=lambda: gr.update(value=""),
                outputs=[msg]
            )

            example_btn3.click(
                fn=lambda: example_Q3,
                outputs=[msg]
            ).then(
                fn=self.chat,
                inputs=[msg, chatbot, target_dropdown],
                outputs=[chatbot]
            ).then(
                fn=lambda: gr.update(value=""),
                outputs=[msg]
            )

            example_btn4.click(
                fn=lambda: example_Q4,
                outputs=[msg]
            ).then(
                fn=self.chat,
                inputs=[msg, chatbot, target_dropdown],
                outputs=[chatbot]
            ).then(
                fn=lambda: gr.update(value=""),
                outputs=[msg]
            )

            # Footer
            gr.Markdown(
                """
                ---

                **Built with CrewAI, ChromaDB, and Gradio** |
                [Documentation](https://github.com/yourusername/cudabot) |
                Powered by multi-agent AI
                """
            )

        return demo

    def launch(
        self,
        share: bool = False,
        server_name: str = "0.0.0.0",
        server_port: int = 7860,
        **kwargs
    ):
        """Launch the Gradio interface."""
        demo = self.create_interface()

        print("\n" + "="*60)
        print("🚀 Launching AI Documentation Assistant UI")
        print("="*60)

        available_targets = self.get_available_targets()
        if available_targets:
            print(f"✅ Ready targets: {', '.join(available_targets)}")
        else:
            print("⚠️  No targets are ready. Run setup first.")

        print(f"🌐 Server will be available at http://{server_name}:{server_port}")
        print("="*60 + "\n")

        demo.launch(
            share=share,
            server_name=server_name,
            server_port=server_port,
            auth=("cuda", "cuda"),
            auth_message="Welcome to CudaBot! Username: cuda | Password: cuda",
            favicon_path="/root/cudabot/config/chattermax_favicon.png",
            **kwargs
        )


def main():
    """Main entry point for Gradio UI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Launch Gradio UI for AI Documentation Assistant"
    )
    parser.add_argument(
        '--share',
        action='store_true',
        help='Create a public share link'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=7860,
        help='Port to run the server on (default: 7860)'
    )
    parser.add_argument(
        '--host',
        type=str,
        default="0.0.0.0",
        help='Host to bind to (default: 0.0.0.0)'
    )

    args = parser.parse_args()

    # Create and launch the app
    app = GradioDocAssistant()
    app.launch(
        share=args.share,
        server_name=args.host,
        server_port=args.port
    )


if __name__ == "__main__":
    main()
