"""
Output manager for controlling debug vs production output.

In debug mode:
- All output goes to stdout
- Verbose crew output is enabled

In production mode:
- Debug output goes to a log file
- Only final response goes to stdout
- Verbose crew output is captured
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, TextIO
from contextlib import contextmanager
import io


class OutputManager:
    """Manages output routing between debug and production modes."""

    def __init__(self, debug_mode: bool = False, log_dir: Optional[Path] = None):
        """
        Initialize the output manager.

        Args:
            debug_mode: If True, show all output. If False, capture debug output.
            log_dir: Directory for log files in production mode
        """
        self.debug_mode = debug_mode
        self.log_dir = log_dir or Path("logs")
        self.log_file: Optional[TextIO] = None
        self.captured_output: list = []
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

        # Create log directory if in production mode
        if not debug_mode:
            self.log_dir.mkdir(parents=True, exist_ok=True)

            # Create log file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_path = self.log_dir / f"cudabot_{timestamp}.log"
            self.log_file = open(log_path, 'w', encoding='utf-8')

            # Write header to log file
            self.log_file.write(f"CUDA-Q Bot Debug Log\n")
            self.log_file.write(f"Started: {datetime.now().isoformat()}\n")
            self.log_file.write("=" * 80 + "\n\n")
            self.log_file.flush()

    def debug_print(self, message: str, end: str = "\n"):
        """
        Print a debug message.

        In debug mode: prints to stdout
        In production mode: writes to log file
        """
        if self.debug_mode:
            print(message, end=end)
        else:
            if self.log_file:
                self.log_file.write(message + end)
                self.log_file.flush()

    def final_print(self, message: str, end: str = "\n"):
        """
        Print final output - always goes to stdout.
        """
        # Always print to original stdout (even if we've redirected)
        self.original_stdout.write(message + end)
        self.original_stdout.flush()

        # Also log it if in production mode
        if not self.debug_mode and self.log_file:
            self.log_file.write("\n" + "=" * 80 + "\n")
            self.log_file.write("FINAL RESPONSE:\n")
            self.log_file.write("=" * 80 + "\n")
            self.log_file.write(message + end)
            self.log_file.flush()

    @contextmanager
    def capture_output(self):
        """
        Context manager to capture stdout/stderr.

        In debug mode: doesn't capture anything
        In production mode: captures to log file
        """
        if self.debug_mode:
            # In debug mode, don't capture - let everything through
            yield
        else:
            # In production mode, redirect to log file
            class TeeOutput:
                """Writes to both log file and captures output."""
                def __init__(self, log_file):
                    self.log_file = log_file
                    self.buffer = []

                def write(self, text):
                    if text:
                        self.log_file.write(text)
                        self.log_file.flush()
                        self.buffer.append(text)

                def flush(self):
                    self.log_file.flush()

            tee_stdout = TeeOutput(self.log_file)
            tee_stderr = TeeOutput(self.log_file)

            old_stdout = sys.stdout
            old_stderr = sys.stderr

            try:
                sys.stdout = tee_stdout
                sys.stderr = tee_stderr
                yield
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

    def print_section(self, title: str, char: str = "="):
        """Print a section separator."""
        separator = char * 80
        self.debug_print(f"\n{separator}")
        self.debug_print(title)
        self.debug_print(separator)

    def close(self):
        """Close the log file if open."""
        if self.log_file:
            self.log_file.write("\n" + "=" * 80 + "\n")
            self.log_file.write(f"Completed: {datetime.now().isoformat()}\n")
            self.log_file.close()
            self.log_file = None


# Global output manager instance
_output_manager: Optional[OutputManager] = None


def initialize_output_manager(debug_mode: bool = False, log_dir: Optional[Path] = None) -> OutputManager:
    """Initialize the global output manager."""
    global _output_manager
    _output_manager = OutputManager(debug_mode=debug_mode, log_dir=log_dir)
    return _output_manager


def get_output_manager() -> OutputManager:
    """Get the global output manager instance."""
    global _output_manager
    if _output_manager is None:
        _output_manager = initialize_output_manager(debug_mode=True)
    return _output_manager


def debug_print(message: str, end: str = "\n"):
    """Convenience function for debug printing."""
    get_output_manager().debug_print(message, end)


def final_print(message: str, end: str = "\n"):
    """Convenience function for final output printing."""
    get_output_manager().final_print(message, end)


def format_final_response(result: dict, include_header: bool = True) -> str:
    """
    Format the final response for output.

    Args:
        result: Result dictionary from crew workflow
        include_header: Whether to include a header

    Returns:
        Formatted response string
    """
    parts = []

    if include_header:
        parts.append("=" * 80)
        parts.append("FINAL RESPONSE")
        parts.append("=" * 80)
        parts.append("")

    # Add documentation context
    doc_context = result.get('documentation_context', '')
    if doc_context:
        parts.append("## Documentation")
        parts.append("")
        parts.append(doc_context)
        parts.append("")

    # Add generated code
    code = result.get('generated_code', '')
    if code:
        parts.append("## Generated Code")
        parts.append("")
        parts.append(code)
        parts.append("")

    # Add validation
    validation = result.get('validation_result', '')
    if validation:
        parts.append("## Code Review")
        parts.append("")
        parts.append(validation)
        parts.append("")

    # Add final response if it exists and is different
    final_response = result.get('final_response', '')
    if final_response and final_response.strip():
        # Check if final_response is just a concatenation of the above
        # If so, don't duplicate it
        if final_response != doc_context and final_response != code:
            parts.append("## Summary")
            parts.append("")
            parts.append(final_response)

    if include_header:
        parts.append("")
        parts.append("=" * 80)

    return "\n".join(parts)
