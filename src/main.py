#!/usr/bin/env python3
"""
Main entry point for the AI Documentation Assistant.
Supports multiple targets with CUDA-Q as the initial implementation.
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config_loader import get_merged_config, get_data_paths, load_target_config
from orchestration.crew_flow import run_documentation_assistant, format_assistant_response, get_conversation_history
from setup_pipeline import setup_target_pipeline_sync as setup_target_pipeline, check_target_setup
from utils.target_manager import TargetManager


def list_available_targets() -> List[str]:
    """List all available target configurations."""
    targets_dir = Path(__file__).parent.parent / "config" / "targets"
    if not targets_dir.exists():
        return []

    targets = []
    for config_file in targets_dir.glob("*.yaml"):
        target_name = config_file.stem
        targets.append(target_name)

    return sorted(targets)


def display_target_info(target_name: str) -> None:
    """Display information about a target."""
    try:
        config = load_target_config(target_name)
        target_info = config.get('target', {})

        print(f"\n📋 Target: {target_info.get('name', target_name)}")
        print(f"Description: {target_info.get('description', 'No description available')}")
        print(f"Domain: {target_info.get('domain', 'Unknown')}")

        doc_config = config.get('documentation', {})
        if doc_config.get('base_url'):
            print(f"Documentation: {doc_config['base_url']}")

        agents = config.get('agents', {})
        print(f"Agents configured: {len(agents)}")

        # Check setup status
        setup_status = check_target_setup(target_name)
        print(f"Setup status: {'✅ Ready' if setup_status['is_ready'] else '❌ Needs setup'}")

        if not setup_status['is_ready']:
            print("Missing components:")
            for component, status in setup_status['components'].items():
                if not status:
                    print(f"  - {component}")

    except Exception as e:
        print(f"Error loading target info: {e}")


def interactive_target_selection() -> str:
    """Interactive target selection menu."""
    targets = list_available_targets()

    if not targets:
        print("❌ No targets configured. Please add target configurations to config/targets/")
        sys.exit(1)

    print("\n🎯 Available Targets:")
    for i, target in enumerate(targets, 1):
        print(f"  {i}. {target}")

    while True:
        try:
            choice = input(f"\nSelect target (1-{len(targets)}) or 'q' to quit: ").strip()

            if choice.lower() == 'q':
                sys.exit(0)

            idx = int(choice) - 1
            if 0 <= idx < len(targets):
                return targets[idx]
            else:
                print(f"Please enter a number between 1 and {len(targets)}")

        except ValueError:
            print("Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            sys.exit(0)


def interactive_chat_session(target_name: str, debug_mode: bool = False) -> None:
    """Interactive chat session with the assistant."""
    print(f"\n🤖 Starting chat session with {target_name} assistant")
    if debug_mode:
        print("🐛 Debug mode enabled - showing verbose output")
    print("Type 'quit', 'exit', or press Ctrl+C to end the session")
    print("Type 'history' to see conversation history")
    print("Type 'help' for available commands\n")

    while True:
        try:
            query = input(f"{target_name}> ").strip()

            if not query:
                continue

            if query.lower() in ['quit', 'exit']:
                print("Goodbye!")
                break

            elif query.lower() == 'history':
                history = get_conversation_history(target_name)
                if history:
                    print(f"\n📜 Conversation History ({len(history)} entries):")
                    for entry in history[-5:]:  # Show last 5
                        print(f"  {entry.get('timestamp', 'Unknown time')}: {entry.get('query', 'No query')[:60]}...")
                else:
                    print("No conversation history found.")
                print()
                continue

            elif query.lower() == 'help':
                print("""
Available commands:
  - history: Show conversation history
  - quit/exit: End the session
  - help: Show this help message

Just type your question to get assistance!
""")
                continue

            # Process the query
            if not debug_mode:
                print("🔍 Processing query...")

            try:
                result = run_documentation_assistant(target_name, query, debug_mode=debug_mode)
                formatted_response = format_assistant_response(result)
                print(f"\n{formatted_response}\n")

            except Exception as e:
                print(f"❌ Error processing query: {e}")
                print("Please try rephrasing your question or check your setup.\n")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


def setup_command(args: argparse.Namespace) -> None:
    """Handle setup command."""
    target_name = args.target

    if not target_name:
        target_name = interactive_target_selection()

    print(f"🔧 Setting up {target_name}...")

    try:
        result = setup_target_pipeline(
            target_name,
            crawl_docs=not args.skip_crawl,
            force_recrawl=args.force_crawl,
            max_concurrent=args.max_concurrent
        )

        print(f"✅ Setup completed successfully!")
        print(f"   Documents crawled: {result.get('documents_crawled', 0)}")
        print(f"   Chunks created: {result.get('chunks_created', 0)}")
        print(f"   Embeddings generated: {result.get('embeddings_created', 0)}")

    except Exception as e:
        print(f"❌ Setup failed: {e}")
        sys.exit(1)


def chat_command(args: argparse.Namespace) -> None:
    """Handle chat command."""
    target_name = args.target
    debug_mode = getattr(args, 'debug', False)

    if not target_name:
        target_name = interactive_target_selection()

    # Check if target is set up
    setup_status = check_target_setup(target_name)
    if not setup_status['is_ready']:
        print(f"❌ Target '{target_name}' is not set up properly.")
        print("Run setup first: python src/main.py setup --target", target_name)
        sys.exit(1)

    if args.query:
        # Single query mode
        if not debug_mode:
            print(f"🔍 Processing query with {target_name}...")

        try:
            result = run_documentation_assistant(target_name, args.query, debug_mode=debug_mode)
            formatted_response = format_assistant_response(result)
            print(formatted_response)

        except Exception as e:
            print(f"❌ Error: {e}")
            sys.exit(1)
    else:
        # Interactive mode
        interactive_chat_session(target_name, debug_mode=debug_mode)


def info_command(args: argparse.Namespace) -> None:
    """Handle info command."""
    if args.target:
        display_target_info(args.target)
    else:
        targets = list_available_targets()
        print(f"\n📋 Available Targets ({len(targets)}):")
        for target in targets:
            display_target_info(target)
            print("-" * 50)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="ChatterBot for CUDA-Q - Chat with your CUDA-Q documentation using AI agents",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Setup CUDA-Q target
  python src/main.py setup --target cuda_q

  # Interactive chat with CUDA-Q
  python src/main.py chat --target cuda_q

  # Single query
  python src/main.py chat --target cuda_q --query "How do I create a quantum circuit?"

  # List targets
  python src/main.py info
        """
    )

    parser.add_argument(
        '--version',
        action='version',
        version='AI Documentation Assistant 1.0.0'
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Set up a target (crawl docs, create embeddings)')
    setup_parser.add_argument('--target', '-t', help='Target to set up')
    setup_parser.add_argument('--skip-crawl', action='store_true', help='Skip documentation crawling')
    setup_parser.add_argument('--force-crawl', action='store_true', help='Force re-crawl even if docs exist')
    setup_parser.add_argument('--max-concurrent', type=int, default=10, help='Max concurrent crawl requests')

    # Chat command
    chat_parser = subparsers.add_parser('chat', help='Start chat session or process single query')
    chat_parser.add_argument('--target', '-t', help='Target to chat with')
    chat_parser.add_argument('--query', '-q', help='Single query to process')
    chat_parser.add_argument('--debug', action='store_true', help='Enable debug mode (show verbose output)')

    # Info command
    info_parser = subparsers.add_parser('info', help='Show information about targets')
    info_parser.add_argument('--target', '-t', help='Specific target to show info for')

    # Parse arguments
    args = parser.parse_args()

    if not args.command:
        # Default behavior - show available targets and start interactive mode
        targets = list_available_targets()
        if not targets:
            print("❌ No targets configured. Please add target configurations to config/targets/")
            sys.exit(1)

        print("🤖 AI Documentation Assistant")
        print("Choose a command: setup, chat, or info")
        print("Use --help for more information")

        target_name = interactive_target_selection()
        setup_status = check_target_setup(target_name)

        if not setup_status['is_ready']:
            print(f"\n❌ Target '{target_name}' needs setup first.")
            confirm = input("Run setup now? (y/N): ").strip().lower()
            if confirm == 'y':
                # Simulate setup args
                args.command = 'setup'
                args.target = target_name
                args.skip_crawl = False
                args.force_crawl = False
                args.max_concurrent = 10
                setup_command(args)
                print("\n" + "="*50 + "\n")

        # Start chat
        args.command = 'chat'
        args.target = target_name
        args.query = None

    # Execute command
    if args.command == 'setup':
        setup_command(args)
    elif args.command == 'chat':
        chat_command(args)
    elif args.command == 'info':
        info_command(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()