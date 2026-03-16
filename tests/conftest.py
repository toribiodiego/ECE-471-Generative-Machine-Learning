"""Pytest configuration and shared fixtures for Agnus test suite.

This module provides reusable fixtures for mocking configurations,
audio streams, video captures, and Gemini API clients across all tests.
"""

import os
import pytest
import numpy as np
from unittest.mock import Mock, MagicMock, AsyncMock, patch


@pytest.fixture
def mock_config():
    """Provide standard test configuration with all required parameters.

    Returns:
        dict: Configuration dictionary with audio, video, and Gemini settings.
    """
    return {
        "MIC_TYPE": "computer_mic",
        "AUDIO_FORMAT": 8,  # pyaudio.paInt16
        "AUDIO_CHANNELS": 1,
        "INPUT_SAMPLE_RATE": 16000,
        "OUTPUT_SAMPLE_RATE": 24000,
        "VIDEO_CAPTURE_INTERVAL": 1.0,
        "THUMBNAIL_MAX_SIZE": [1024, 1024],
        "GEMINI_MODEL": "gemini-2.0-flash-exp",
        "GEMINI_RESPONSE_MODALITIES": ["AUDIO"],
        "GEMINI_HTTP_OPTIONS": {"api_version": "v1alpha"},
        "VOICE_NAME": "Leda",
        "WEB_UI_TITLE": "Test Gemini Demo",
    }


@pytest.fixture
def mock_env():
    """Mock environment variables with test API key.

    Yields:
        None: Patches os.environ for the duration of the test.
    """
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key-123"}):
        yield


@pytest.fixture
def mock_pyaudio():
    """Mock PyAudio instance for audio stream testing.

    Yields:
        MagicMock: Mocked PyAudio instance with device info and stream support.
    """
    with patch('pyaudio.PyAudio') as mock_pa_class:
        mock_instance = MagicMock()
        mock_pa_class.return_value = mock_instance

        # Mock device info
        mock_instance.get_default_input_device_info.return_value = {
            "index": 0,
            "name": "Test Microphone"
        }

        # Mock audio stream
        mock_stream = MagicMock()
        mock_stream.read.return_value = b'\x00' * 1024
        mock_stream.is_active.return_value = True
        mock_instance.open.return_value = mock_stream

        yield mock_instance


@pytest.fixture
def mock_audio_stream():
    """Mock PyAudio stream for input/output testing.

    Returns:
        MagicMock: Mocked audio stream with read/write/control methods.
    """
    mock_stream = MagicMock()
    mock_stream.read.return_value = b'\x00' * 1024
    mock_stream.write.return_value = None
    mock_stream.is_active.return_value = True
    mock_stream.stop_stream.return_value = None
    mock_stream.close.return_value = None
    return mock_stream


@pytest.fixture
def mock_cv2():
    """Mock OpenCV VideoCapture for video testing.

    Yields:
        MagicMock: Mocked VideoCapture instance with frame capture support.
    """
    with patch('cv2.VideoCapture') as mock_cap_class:
        mock_instance = MagicMock()
        mock_cap_class.return_value = mock_instance

        # Mock successful frame capture
        mock_instance.isOpened.return_value = True
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_instance.read.return_value = (True, test_frame)
        mock_instance.release.return_value = None

        yield mock_instance


@pytest.fixture
def mock_video_frame():
    """Provide a test video frame as numpy array.

    Returns:
        np.ndarray: 640x480 RGB test frame filled with zeros.
    """
    return np.zeros((480, 640, 3), dtype=np.uint8)


@pytest.fixture
def mock_gemini_client():
    """Mock Google Gemini API client.

    Returns:
        MagicMock: Mocked Gemini client with live session support.
    """
    mock_client = MagicMock()
    mock_client.aio = MagicMock()

    # Mock live session
    mock_session = AsyncMock()
    mock_client.aio.live.connect.return_value.__aenter__ = AsyncMock(
        return_value=mock_session
    )
    mock_client.aio.live.connect.return_value.__aexit__ = AsyncMock(
        return_value=None
    )

    return mock_client


@pytest.fixture
def mock_gemini_session():
    """Mock Gemini Live API session for async testing.

    Returns:
        AsyncMock: Mocked live session with send/receive support.
    """
    mock_session = AsyncMock()

    # Mock send methods
    mock_session.send_realtime_input = AsyncMock()

    # Mock receive with empty async generator
    async def mock_receive():
        # Return empty async generator (no messages)
        return
        yield  # Never actually yields

    mock_session.receive.return_value = mock_receive()

    return mock_session


@pytest.fixture(autouse=True)
def reset_session_state():
    """Reset global session state before and after each test.

    This fixture automatically runs for all tests to ensure clean state.

    Yields:
        None: Performs cleanup before and after test execution.
    """
    # Import here to avoid circular dependencies
    try:
        import src.core.session_manager as sm
        sm._media_loop = None
        sm._media_loop_thread = None
        yield
        # Cleanup after test
        if sm._media_loop:
            try:
                sm._media_loop.shutdown()
            except:
                pass
        sm._media_loop = None
        sm._media_loop_thread = None
    except ImportError:
        # Module doesn't exist yet or isn't needed
        yield
