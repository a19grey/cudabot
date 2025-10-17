#!/usr/bin/env python3
"""
Secure launcher for the Gradio UI with authentication.
Usage: python launch_ui_secure.py --username USER --password PASS
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from gradio_app import GradioDocAssistant


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Launch Gradio UI with authentication for AI Documentation Assistant"
    )
    parser.add_argument(
        '--username',
        type=str,
        default=os.environ.get('GRADIO_USERNAME', 'admin'),
        help='Username for authentication (default: admin, or $GRADIO_USERNAME)'
    )
    parser.add_argument(
        '--password',
        type=str,
        default=os.environ.get('GRADIO_PASSWORD'),
        help='Password for authentication (required, or set $GRADIO_PASSWORD)'
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
        help='Host to bind to (default: 0.0.0.0 for all interfaces)'
    )
    parser.add_argument(
        '--no-auth',
        action='store_true',
        help='Disable authentication (NOT RECOMMENDED for public access)'
    )

    args = parser.parse_args()

    # Validate password if auth is enabled
    if not args.no_auth and not args.password:
        print("❌ Error: Password is required for secure access!")
        print("\nOptions:")
        print("  1. Set password via argument: --password YOUR_PASSWORD")
        print("  2. Set environment variable: export GRADIO_PASSWORD=YOUR_PASSWORD")
        print("  3. Disable auth (NOT RECOMMENDED): --no-auth")
        sys.exit(1)

    # Create and launch the app
    app = GradioDocAssistant()
    demo = app.create_interface()

    print("\n" + "="*60)
    print("🚀 Launching AI Documentation Assistant UI (SECURE MODE)")
    print("="*60)

    if not args.no_auth:
        print(f"🔒 Authentication: ENABLED")
        print(f"   Username: {args.username}")
        print(f"   Password: {'*' * len(args.password)}")
    else:
        print("⚠️  Authentication: DISABLED (Not recommended for public access)")

    available_targets = app.get_available_targets()
    if available_targets:
        print(f"✅ Ready targets: {', '.join(available_targets)}")
    else:
        print("⚠️  No targets are ready. Run setup first.")

    print(f"🌐 Server will be available at:")
    print(f"   Local: http://localhost:{args.port}")
    if args.host == "0.0.0.0":
        print(f"   Network: http://YOUR_VPS_IP:{args.port}")
    print("="*60 + "\n")

    # Launch with or without authentication
    launch_kwargs = {
        'share': args.share,
        'server_name': args.host,
        'server_port': args.port,
        'show_error': True,
    }

    if not args.no_auth:
        launch_kwargs['auth'] = (args.username, args.password)

    demo.launch(**launch_kwargs)


if __name__ == "__main__":
    main()
