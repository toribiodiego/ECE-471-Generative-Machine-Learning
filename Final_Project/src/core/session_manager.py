"""Session management for MediaLoop instances.

This module handles the lifecycle of MediaLoop sessions, including
starting, stopping, and checking the status of active sessions.
Thread-safe session control with proper state management.
"""

import asyncio
import os
import threading
from typing import Optional

from dotenv import load_dotenv

from src.core.media_loop import MediaLoop
from src.utils.config_loader import load_config


# Global state for session management
_media_loop: Optional[MediaLoop] = None
_media_loop_thread: Optional[threading.Thread] = None
_session_lock = threading.Lock()


def _run_media_loop(loop: MediaLoop, api_key: str):
    """Run MediaLoop in async context.

    Helper function to execute the async MediaLoop.run() method
    in a separate thread.

    Args:
        loop: MediaLoop instance to run.
        api_key: Gemini API key for authentication.
    """
    asyncio.run(loop.run(api_key))


def start_media_session() -> str:
    """Initialize and start a new MediaLoop session.

    Creates a new MediaLoop instance with loaded configuration and
    starts it in a background thread. If a session is already active,
    this is a no-op.

    Returns:
        Status message: "Started" if new session created, or current status.

    Raises:
        EnvironmentError: If GEMINI_API_KEY is not set in environment.

    Example:
        >>> load_dotenv()
        >>> status = start_media_session()
        >>> print(status)
        Started
    """
    global _media_loop, _media_loop_thread

    with _session_lock:
        # Check if session already active
        if _media_loop is not None and not _media_loop.quit.is_set():
            return "Already running"

        # Load environment and configuration
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GEMINI_API_KEY not found in environment. "
                "Please create a .env file with your API key."
            )

        config = load_config()

        # Create and start MediaLoop
        _media_loop = MediaLoop(config)
        _media_loop_thread = threading.Thread(
            target=_run_media_loop,
            args=(_media_loop, api_key),
            daemon=True
        )
        _media_loop_thread.start()

        return "Started"


def stop_media_session() -> str:
    """Shutdown the active MediaLoop session.

    Signals the MediaLoop to stop all streaming tasks and cleans up
    resources. If no session is active, this is a no-op.

    Returns:
        Status message: "Stopped" if session was stopped, "Not running" otherwise.

    Example:
        >>> status = stop_media_session()
        >>> print(status)
        Stopped
    """
    global _media_loop, _media_loop_thread

    with _session_lock:
        if _media_loop is None:
            return "Not running"

        # Shutdown MediaLoop
        _media_loop.shutdown()

        # Clear global state
        _media_loop = None
        _media_loop_thread = None

        return "Stopped"


def get_session_status() -> str:
    """Check if a MediaLoop session is currently active.

    Returns:
        Status string: "Running" if session active, "Stopped" otherwise.

    Example:
        >>> status = get_session_status()
        >>> print(status)
        Running
    """
    with _session_lock:
        if _media_loop is not None and not _media_loop.quit.is_set():
            return "Running"
        return "Stopped"


def get_latest_video_frame():
    """Get the most recent video frame from the active session.

    Returns:
        PIL.Image or None if no session active or no frame captured yet.

    Example:
        >>> frame = get_latest_video_frame()
        >>> if frame:
        ...     frame.save("latest_frame.jpg")
    """
    with _session_lock:
        if _media_loop is not None:
            return _media_loop.latest_video_frame
        return None
