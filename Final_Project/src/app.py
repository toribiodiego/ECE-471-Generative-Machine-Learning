"""Main entry point for Agnus multimodal agent application.

This module provides the command-line interface for launching the
Gradio web application with configurable options.
"""

import argparse

from src.ui.gradio_interface import create_ui


def parse_args():
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Launch Agnus multimodal agent web interface"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port to run the Gradio server on (default: 7860)"
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a public shareable link"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with verbose logging"
    )
    return parser.parse_args()


def main():
    """Launch the Gradio web application.

    Parses command-line arguments and starts the Gradio interface
    with the specified configuration.
    """
    args = parse_args()

    # Create and launch the UI
    demo = create_ui()
    demo.launch(
        server_port=args.port,
        share=args.share,
        debug=args.debug,
    )


if __name__ == "__main__":
    main()
