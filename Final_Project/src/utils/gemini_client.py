"""Gemini API client utilities.

This module provides functions for initializing and configuring the
Gemini Live API client for real-time audio/video streaming.
"""

from typing import Dict, Any, Optional

from google import genai
from google.genai import types


def get_gemini_client(api_key: str, http_options: Dict[str, Any]) -> genai.Client:
    """Initialize and return a Gemini API client.

    Creates a Gemini client configured with the provided API key and
    HTTP options for connecting to the Gemini Live API.

    Args:
        api_key: Gemini API key for authentication.
        http_options: Dictionary containing HTTP configuration options,
                     typically including 'api_version'.

    Returns:
        Configured genai.Client instance.

    Raises:
        ValueError: If api_key is None or empty.
        Exception: If client initialization fails (invalid credentials, etc.).

    Example:
        >>> client = get_gemini_client(
        ...     "your-api-key",
        ...     {"api_version": "v1alpha"}
        ... )
    """
    if not api_key:
        raise ValueError("API key cannot be None or empty")

    return genai.Client(api_key=api_key, http_options=http_options)


def create_speech_config(voice_name: str) -> types.SpeechConfig:
    """Create speech configuration for audio output.

    Configures the voice settings for Gemini's text-to-speech output,
    specifying which prebuilt voice to use for synthesized responses.

    Args:
        voice_name: Name of the prebuilt voice (e.g., "Leda", "Aoede").

    Returns:
        SpeechConfig object configured with the specified voice.

    Example:
        >>> speech_config = create_speech_config("Leda")
    """
    return types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
        )
    )


def get_live_config(
    system_instruction: str,
    response_modalities: list,
    speech_config: types.SpeechConfig,
    previous_handle: Optional[str] = None,
) -> types.LiveConnectConfig:
    """Create LiveConnectConfig for Gemini Live API session.

    Builds the configuration object needed to establish a live streaming
    connection with Gemini, including system instructions, response settings,
    context compression, and optional session resumption.

    Args:
        system_instruction: Text containing the system prompt that defines
                           the agent's personality and behavior.
        response_modalities: List of response types (e.g., ["AUDIO"]).
        speech_config: SpeechConfig object with voice settings.
        previous_handle: Optional session handle for resuming a previous
                        session. If None, starts a new session.

    Returns:
        LiveConnectConfig object ready for establishing a live connection.

    Example:
        >>> speech_cfg = create_speech_config("Leda")
        >>> live_cfg = get_live_config(
        ...     system_instruction="You are a helpful assistant.",
        ...     response_modalities=["AUDIO"],
        ...     speech_config=speech_cfg,
        ...     previous_handle=None
        ... )
    """
    return types.LiveConnectConfig(
        response_modalities=response_modalities,
        context_window_compression=types.ContextWindowCompressionConfig(
            sliding_window=types.SlidingWindow(),
        ),
        session_resumption=types.SessionResumptionConfig(
            handle=previous_handle
        ),
        system_instruction=types.Content(
            parts=[types.Part.from_text(text=system_instruction)],
            role="user",
        ),
        speech_config=speech_config,
    )
