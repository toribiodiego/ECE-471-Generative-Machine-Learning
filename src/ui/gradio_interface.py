"""Gradio UI interface for Agnus multimodal agent.

This module provides the web interface for controlling the MediaLoop
session and viewing the live video feed.
"""

import gradio as gr

from src.core.session_manager import (
    start_media_session,
    stop_media_session,
    get_session_status,
)
from src.utils.config_loader import load_config


def create_ui() -> gr.Blocks:
    """Create and return the Gradio web interface.

    Builds a Gradio Blocks interface with controls for starting/stopping
    the media session and displaying the live video feed from the webcam.

    Returns:
        gr.Blocks: Configured Gradio interface ready to launch.

    Example:
        >>> demo = create_ui()
        >>> demo.launch(share=False)
    """
    config = load_config()

    with gr.Blocks(title=config["WEB_UI_TITLE"]) as demo:
        gr.Markdown(
            "## Gemini Audio/Video Demo\n"
            "Click **Start** to open the session; **Stop** to end."
        )

        with gr.Row():
            btn_start = gr.Button("Start")
            btn_stop = gr.Button("Stop")

        status = gr.Textbox(label="Status", interactive=False)

        live = gr.Video(
            label="Live Video Feed",
            sources=["webcam"],
            streaming=True,
            autoplay=True,
        )

        # Wire up button callbacks
        btn_start.click(start_media_session, inputs=[], outputs=status)
        btn_stop.click(stop_media_session, inputs=[], outputs=status)

    return demo
