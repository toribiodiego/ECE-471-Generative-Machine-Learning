"""Unit tests for session_manager module."""

import os
import pytest
import threading
import time
from unittest.mock import Mock, MagicMock, patch, AsyncMock

from src.core.session_manager import (
    start_media_session,
    stop_media_session,
    get_session_status,
    get_latest_video_frame,
)


@pytest.fixture
def mock_env():
    """Mock environment with API key."""
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test-api-key-123"}):
        yield


@pytest.fixture
def mock_config():
    """Mock configuration data."""
    return {
        "MIC_TYPE": "computer_mic",
        "AUDIO_FORMAT": 8,
        "AUDIO_CHANNELS": 1,
        "INPUT_SAMPLE_RATE": 16000,
        "OUTPUT_SAMPLE_RATE": 24000,
        "VIDEO_CAPTURE_INTERVAL": 1.0,
        "THUMBNAIL_MAX_SIZE": [1024, 1024],
        "GEMINI_MODEL": "gemini-2.0-flash-exp",
        "GEMINI_RESPONSE_MODALITIES": ["AUDIO"],
        "GEMINI_HTTP_OPTIONS": {"api_version": "v1alpha"},
        "VOICE_NAME": "Leda",
    }


@pytest.fixture(autouse=True)
def reset_session_state():
    """Reset global session state before each test."""
    import src.core.session_manager as sm
    sm._media_loop = None
    sm._media_loop_thread = None
    yield
    # Cleanup after test
    if sm._media_loop:
        sm._media_loop.shutdown()
    sm._media_loop = None
    sm._media_loop_thread = None


class TestStartMediaSession:
    """Tests for start_media_session function."""

    @patch('src.core.session_manager.load_config')
    @patch('src.core.session_manager.MediaLoop')
    @patch('src.core.session_manager.threading.Thread')
    def test_start_session_success(self, mock_thread_class, mock_media_loop_class, mock_load_config, mock_env, mock_config):
        """Test successfully starting a new session."""
        mock_load_config.return_value = mock_config
        mock_loop = MagicMock()
        mock_loop.quit.is_set.return_value = False
        mock_media_loop_class.return_value = mock_loop
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        result = start_media_session()

        assert result == "Started"
        mock_media_loop_class.assert_called_once_with(mock_config)
        mock_thread.start.assert_called_once()

    @patch('src.core.session_manager.load_dotenv')
    def test_start_session_missing_api_key(self, mock_load_dotenv):
        """Test that missing API key raises EnvironmentError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(EnvironmentError, match="GEMINI_API_KEY not found"):
                start_media_session()

    @patch('src.core.session_manager.load_config')
    @patch('src.core.session_manager.MediaLoop')
    @patch('src.core.session_manager.threading.Thread')
    def test_start_session_already_running(self, mock_thread_class, mock_media_loop_class, mock_load_config, mock_env, mock_config):
        """Test starting session when one is already active."""
        mock_load_config.return_value = mock_config
        mock_loop = MagicMock()
        mock_loop.quit.is_set.return_value = False
        mock_media_loop_class.return_value = mock_loop

        # Start first session
        result1 = start_media_session()
        assert result1 == "Started"

        # Try to start second session
        result2 = start_media_session()
        assert result2 == "Already running"

        # Should only create one MediaLoop
        assert mock_media_loop_class.call_count == 1

    @patch('src.core.session_manager.load_config')
    @patch('src.core.session_manager.MediaLoop')
    @patch('src.core.session_manager.threading.Thread')
    def test_start_after_stop(self, mock_thread_class, mock_media_loop_class, mock_load_config, mock_env, mock_config):
        """Test starting a new session after stopping previous one."""
        mock_load_config.return_value = mock_config
        mock_loop = MagicMock()
        mock_loop.quit.is_set.return_value = True
        mock_media_loop_class.return_value = mock_loop

        # First session
        result1 = start_media_session()
        assert result1 == "Started"

        # Second session (previous quit is set)
        mock_loop.quit.is_set.return_value = True
        result2 = start_media_session()
        assert result2 == "Started"

        # Should create two MediaLoop instances
        assert mock_media_loop_class.call_count == 2


class TestStopMediaSession:
    """Tests for stop_media_session function."""

    @patch('src.core.session_manager.load_config')
    @patch('src.core.session_manager.MediaLoop')
    @patch('src.core.session_manager.threading.Thread')
    def test_stop_active_session(self, mock_thread_class, mock_media_loop_class, mock_load_config, mock_env, mock_config):
        """Test stopping an active session."""
        mock_load_config.return_value = mock_config
        mock_loop = MagicMock()
        mock_media_loop_class.return_value = mock_loop

        # Start session
        start_media_session()

        # Stop session
        result = stop_media_session()

        assert result == "Stopped"
        mock_loop.shutdown.assert_called_once()

    def test_stop_no_session(self):
        """Test stopping when no session is active."""
        result = stop_media_session()
        assert result == "Not running"

    @patch('src.core.session_manager.load_config')
    @patch('src.core.session_manager.MediaLoop')
    @patch('src.core.session_manager.threading.Thread')
    def test_stop_clears_state(self, mock_thread_class, mock_media_loop_class, mock_load_config, mock_env, mock_config):
        """Test that stop clears global state."""
        import src.core.session_manager as sm

        mock_load_config.return_value = mock_config
        mock_loop = MagicMock()
        mock_media_loop_class.return_value = mock_loop

        # Start session
        start_media_session()
        assert sm._media_loop is not None
        assert sm._media_loop_thread is not None

        # Stop session
        stop_media_session()
        assert sm._media_loop is None
        assert sm._media_loop_thread is None


class TestGetSessionStatus:
    """Tests for get_session_status function."""

    def test_status_when_stopped(self):
        """Test status when no session is running."""
        status = get_session_status()
        assert status == "Stopped"

    @patch('src.core.session_manager.load_config')
    @patch('src.core.session_manager.MediaLoop')
    @patch('src.core.session_manager.threading.Thread')
    def test_status_when_running(self, mock_thread_class, mock_media_loop_class, mock_load_config, mock_env, mock_config):
        """Test status when session is active."""
        mock_load_config.return_value = mock_config
        mock_loop = MagicMock()
        mock_loop.quit.is_set.return_value = False
        mock_media_loop_class.return_value = mock_loop

        start_media_session()
        status = get_session_status()
        assert status == "Running"

    @patch('src.core.session_manager.load_config')
    @patch('src.core.session_manager.MediaLoop')
    @patch('src.core.session_manager.threading.Thread')
    def test_status_after_stop(self, mock_thread_class, mock_media_loop_class, mock_load_config, mock_env, mock_config):
        """Test status transitions from running to stopped."""
        mock_load_config.return_value = mock_config
        mock_loop = MagicMock()
        mock_loop.quit.is_set.return_value = False
        mock_media_loop_class.return_value = mock_loop

        # Start
        start_media_session()
        assert get_session_status() == "Running"

        # Stop
        stop_media_session()
        assert get_session_status() == "Stopped"


class TestGetLatestVideoFrame:
    """Tests for get_latest_video_frame function."""

    def test_get_frame_no_session(self):
        """Test getting frame when no session exists."""
        frame = get_latest_video_frame()
        assert frame is None

    @patch('src.core.session_manager.load_config')
    @patch('src.core.session_manager.MediaLoop')
    @patch('src.core.session_manager.threading.Thread')
    def test_get_frame_from_active_session(self, mock_thread_class, mock_media_loop_class, mock_load_config, mock_env, mock_config):
        """Test getting frame from active session."""
        from PIL import Image

        mock_load_config.return_value = mock_config
        mock_loop = MagicMock()
        mock_frame = Image.new('RGB', (640, 480))
        mock_loop.latest_video_frame = mock_frame
        mock_media_loop_class.return_value = mock_loop

        start_media_session()
        frame = get_latest_video_frame()

        assert frame == mock_frame

    @patch('src.core.session_manager.load_config')
    @patch('src.core.session_manager.MediaLoop')
    @patch('src.core.session_manager.threading.Thread')
    def test_get_frame_none_when_no_capture(self, mock_thread_class, mock_media_loop_class, mock_load_config, mock_env, mock_config):
        """Test getting frame when session exists but no frame captured."""
        mock_load_config.return_value = mock_config
        mock_loop = MagicMock()
        mock_loop.latest_video_frame = None
        mock_media_loop_class.return_value = mock_loop

        start_media_session()
        frame = get_latest_video_frame()

        assert frame is None


class TestThreadSafety:
    """Tests for thread-safe session management."""

    @patch('src.core.session_manager.load_config')
    @patch('src.core.session_manager.MediaLoop')
    @patch('src.core.session_manager.load_dotenv')
    def test_concurrent_start_attempts(self, mock_load_dotenv, mock_media_loop_class, mock_load_config, mock_config):
        """Test that concurrent start attempts are handled safely."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}):
            mock_load_config.return_value = mock_config
            mock_loop = MagicMock()
            mock_loop.quit.is_set.return_value = False
            mock_media_loop_class.return_value = mock_loop

            results = []

            def start_in_thread():
                results.append(start_media_session())

            # Use real threads to test thread safety
            threads = [threading.Thread(target=start_in_thread) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # Should only create one MediaLoop despite concurrent attempts
            # Due to thread safety with lock
            assert mock_media_loop_class.call_count == 1
            assert "Started" in results
            # At least some threads should see "Already running"
            assert results.count("Already running") >= 1


class TestIntegration:
    """Integration tests for session lifecycle."""

    @patch('src.core.session_manager.load_config')
    @patch('src.core.session_manager.MediaLoop')
    @patch('src.core.session_manager.threading.Thread')
    def test_full_session_lifecycle(self, mock_thread_class, mock_media_loop_class, mock_load_config, mock_env, mock_config):
        """Test complete start -> status -> stop cycle."""
        mock_load_config.return_value = mock_config
        mock_loop = MagicMock()
        mock_loop.quit.is_set.return_value = False
        mock_media_loop_class.return_value = mock_loop

        # Initial state
        assert get_session_status() == "Stopped"

        # Start
        result = start_media_session()
        assert result == "Started"
        assert get_session_status() == "Running"

        # Try start again
        result = start_media_session()
        assert result == "Already running"

        # Stop
        result = stop_media_session()
        assert result == "Stopped"
        assert get_session_status() == "Stopped"

        # Stop again
        result = stop_media_session()
        assert result == "Not running"
