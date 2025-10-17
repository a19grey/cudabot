#!/usr/bin/env python3
"""
Quick test script to demonstrate the researcher agent.

Usage:
  python test_researcher.py                # Production mode (clean output)
  python test_researcher.py --debug        # Debug mode (verbose output)
"""
import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from orchestration.crew_flow import create_simple_crew_workflow
from utils.output_manager import initialize_output_manager, debug_print, final_print, format_final_response


def test_researcher(debug_mode: bool = False):
    """
    Test the researcher agent with a sample query.

    Args:
        debug_mode: If True, show all debug output. If False, only show final response.
    """
    # Initialize output manager
    log_dir = Path(__file__).parent / "logs"
    output_mgr = initialize_output_manager(debug_mode=debug_mode, log_dir=log_dir)

    # Test query
    test_query = "How do I use the VQE solver in CUDA-Q?"

    # Show header in debug mode
    debug_print("=" * 80)
    debug_print("RESEARCHER AGENT TEST")
    debug_print("=" * 80)
    debug_print(f"\n🔍 Testing query: '{test_query}'")

    if debug_mode:
        debug_print("\nThe researcher agent will:")
        debug_print("  1. Analyze the query intent")
        debug_print("  2. Reformulate it for better search")
        debug_print("  3. Search the documentation")
        debug_print("  4. Evaluate result quality")
        debug_print("  5. Iterate if needed to find better results")
        debug_print("  6. Return the most relevant chunks\n")
        debug_print("-" * 80)

    try:
        # Run the workflow
        result = create_simple_crew_workflow("cuda_q", test_query, debug_mode=debug_mode)

        # Format and print final response
        final_response = format_final_response(result, include_header=True)
        final_print(final_response)

        # In debug mode, show summary
        if debug_mode:
            debug_print("\n" + "=" * 80)
            debug_print("✅ Test completed successfully!")
            debug_print("=" * 80)

    except Exception as e:
        final_print(f"\n❌ Error: {e}")
        if debug_mode:
            import traceback
            traceback.print_exc()
    finally:
        output_mgr.close()


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description="Test the CUDA-Q researcher agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Production mode - only show final response
  python test_researcher.py

  # Debug mode - show all intermediate steps
  python test_researcher.py --debug

  # Custom query
  python test_researcher.py --query "How do I create a quantum circuit?"
        """
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode (show all intermediate output)'
    )

    parser.add_argument(
        '--query',
        type=str,
        default="How do I use the VQE solver in CUDA-Q?",
        help='Query to test with'
    )

    args = parser.parse_args()

    # Run test
    test_researcher(debug_mode=args.debug)


if __name__ == "__main__":
    main()
