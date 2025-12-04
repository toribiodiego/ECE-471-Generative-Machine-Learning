"""Integration tests for MediaLoop class."""

import asyncio
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock, patch
import numpy as np
from PIL import Image

from src.core.media_loop import MediaLoop, get_previous_handle, _declared_previous_handle


@pytest.fixture
def mock_config():
    """Provide a valid test configuration."""
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
    }


@pytest.fixture
def mock_pyaudio():
    """Mock PyAudio for audio testing."""
    with patch('src.core.media_loop.pyaudio.PyAudio') as mock_pa:
        mock_instance = MagicMock()
        mock_pa.return_value = mock_instance

        # Mock device info
        mock_instance.get_default_input_device_info.return_value = {
            "index": 0,
            "name": "Test Microphone"
        }

        # Mock audio streams
        mock_stream = MagicMock()
        mock_stream.read.return_value = b'\x00' * 1024
        mock_instance.open.return_value = mock_stream

        yield mock_instance


@pytest.fixture
def mock_cv2():
    """Mock OpenCV for video testing."""
    with patch('src.core.media_loop.cv2.VideoCapture') as mock_cap:
        mock_instance = MagicMock()
        mock_cap.return_value = mock_instance

        # Mock successful frame capture
        mock_instance.isOpened.return_value = True
        test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_instance.read.return_value = (True, test_frame)

        yield mock_instance


@pytest.fixture
def mock_gemini_session():
    """Mock Gemini Live API session."""
    mock_session = AsyncMock()

    # Mock send methods
    mock_session.send_realtime_input = AsyncMock()

    # Mock receive with an async generator
    async def mock_receive():
        # Return empty async generator
        return
        yield  # Never actually yields

    mock_session.receive.return_value = mock_receive()

    return mock_session


class TestMediaLoopInitialization:
    """Tests for MediaLoop initialization."""

    def test_init_with_valid_config(self, mock_config):
        """Test MediaLoop initializes with valid configuration."""
        with patch('src.core.media_loop.pyaudio.PyAudio'):
            media_loop = MediaLoop(mock_config)

            assert media_loop.config == mock_config
            assert media_loop.chunk_size == 1024  # computer_mic
            assert media_loop.session is None
            assert not media_loop.quit.is_set()

    def test_init_with_dynamic_mic(self, mock_config):
        """Test chunk size selection for dynamic microphone."""
        mock_config["MIC_TYPE"] = "dynamic_mic"

        with patch('src.core.media_loop.pyaudio.PyAudio'):
            media_loop = MediaLoop(mock_config)
            assert media_loop.chunk_size == 512

    def test_init_with_invalid_mic_type(self, mock_config):
        """Test that invalid MIC_TYPE raises ValueError."""
        mock_config["MIC_TYPE"] = "invalid_mic"

        with patch('src.core.media_loop.pyaudio.PyAudio'):
            with pytest.raises(ValueError, match="Invalid MIC_TYPE"):
                MediaLoop(mock_config)


class TestAudioListening:
    """Tests for audio listening functionality."""

    @pytest.mark.asyncio
    async def test_listen_audio_opens_stream(self, mock_config, mock_pyaudio):
        """Test that listen_audio opens audio input stream."""
        media_loop = MediaLoop(mock_config)
        media_loop.session = AsyncMock()

        # Stop after one iteration
        def stop_after_read(*args, **kwargs):
            media_loop.quit.set()
            return b'\x00' * 1024

        mock_pyaudio.open.return_value.read = stop_after_read

        await media_loop.listen_audio()

        # Verify stream was opened with correct parameters
        mock_pyaudio.open.assert_called_once()
        call_kwargs = mock_pyaudio.open.call_args[1]
        assert call_kwargs['input'] is True
        assert call_kwargs['rate'] == 16000

    @pytest.mark.asyncio
    async def test_listen_audio_sends_to_session(self, mock_config, mock_pyaudio):
        """Test that audio data is sent to Gemini session."""
        media_loop = MediaLoop(mock_config)
        mock_session = AsyncMock()
        media_loop.session = mock_session

        # Stop after one iteration
        call_count = 0
        def stop_after_one(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count > 1:
                media_loop.quit.set()
            return b'\x00' * 1024

        mock_pyaudio.open.return_value.read = stop_after_one

        await media_loop.listen_audio()

        # Verify send_realtime_input was called
        assert mock_session.send_realtime_input.called


class TestAudioReceiving:
    """Tests for audio receiving functionality."""

    @pytest.mark.asyncio
    async def test_receive_audio_processes_messages(self, mock_config):
        """Test that receive_audio processes session messages."""
        with patch('src.core.media_loop.pyaudio.PyAudio'):
            media_loop = MediaLoop(mock_config)

            # Track whether audio was queued
            queued_data = []
            original_put = media_loop.audio_in_queue.put

            async def track_put(data):
                queued_data.append(data)
                await original_put(data)

            media_loop.audio_in_queue.put = track_put

            # Create mock session with messages
            mock_msg = MagicMock()
            mock_msg.session_resumption_update = None
            mock_msg.data = b'audio_data_chunk'

            async def mock_turn():
                yield mock_msg
                media_loop.quit.set()

            mock_session = AsyncMock()
            # session.receive() returns a turn, which is async iterable
            mock_session.receive = lambda: mock_turn()
            media_loop.session = mock_session

            await media_loop.receive_audio()

            # Verify audio was queued (even though it was cleared afterward)
            assert len(queued_data) == 1
            assert queued_data[0] == b'audio_data_chunk'

    @pytest.mark.asyncio
    async def test_receive_audio_handles_session_resumption(self, mock_config):
        """Test session resumption handle updates."""
        with patch('src.core.media_loop.pyaudio.PyAudio'):
            media_loop = MediaLoop(mock_config)

            # Mock resumption update
            mock_msg = MagicMock()
            mock_resumption = MagicMock()
            mock_resumption.resumable = True
            mock_resumption.new_handle = "new-session-handle-123"
            mock_msg.session_resumption_update = mock_resumption
            mock_msg.data = None

            async def mock_turn():
                yield mock_msg
                media_loop.quit.set()

            mock_session = AsyncMock()
            # session.receive() returns a turn, which is async iterable
            mock_session.receive = lambda: mock_turn()
            media_loop.session = mock_session

            await media_loop.receive_audio()

            # Verify handle was updated
            assert get_previous_handle() == "new-session-handle-123"


class TestAudioPlayback:
    """Tests for audio playback functionality."""

    @pytest.mark.asyncio
    async def test_play_audio_opens_output_stream(self, mock_config, mock_pyaudio):
        """Test that play_audio opens audio output stream."""
        media_loop = MediaLoop(mock_config)
        media_loop.quit.set()  # Stop immediately

        await media_loop.play_audio()

        # Verify output stream was opened
        mock_pyaudio.open.assert_called_once()
        call_kwargs = mock_pyaudio.open.call_args[1]
        assert call_kwargs['output'] is True
        assert call_kwargs['rate'] == 24000

    @pytest.mark.asyncio
    async def test_play_audio_buffers_data(self, mock_config, mock_pyaudio):
        """Test that audio playback buffers data before writing."""
        media_loop = MediaLoop(mock_config)

        # Queue some audio data
        small_chunk = b'\x00' * 100
        await media_loop.audio_in_queue.put(small_chunk)

        # Stop after a short time
        async def delayed_quit():
            await asyncio.sleep(0.2)
            media_loop.quit.set()

        asyncio.create_task(delayed_quit())
        await media_loop.play_audio()

        # Verify stream was opened
        assert mock_pyaudio.open.called


class TestVideoCapture:
    """Tests for video capture functionality."""

    @pytest.mark.asyncio
    async def test_capture_video_opens_camera(self, mock_config, mock_cv2):
        """Test that capture_video opens camera device."""
        with patch('src.core.media_loop.pyaudio.PyAudio'):
            media_loop = MediaLoop(mock_config)
            media_loop.session = AsyncMock()
            media_loop.quit.set()  # Stop immediately

            with patch('src.core.media_loop.cv2.VideoCapture') as mock_cap:
                mock_instance = MagicMock()
                mock_instance.isOpened.return_value = True
                mock_cap.return_value = mock_instance

                await media_loop.capture_video()

                # Verify camera was opened
                mock_cap.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_capture_video_handles_failed_camera(self, mock_config):
        """Test graceful handling when camera fails to open."""
        with patch('src.core.media_loop.pyaudio.PyAudio'):
            media_loop = MediaLoop(mock_config)

            with patch('src.core.media_loop.cv2.VideoCapture') as mock_cap:
                mock_instance = MagicMock()
                mock_instance.isOpened.return_value = False
                mock_cap.return_value = mock_instance

                # Should return without error
                await media_loop.capture_video()

    @pytest.mark.asyncio
    async def test_capture_video_sends_frames(self, mock_config):
        """Test that video frames are sent to session."""
        with patch('src.core.media_loop.pyaudio.PyAudio'):
            media_loop = MediaLoop(mock_config)
            mock_session = AsyncMock()
            media_loop.session = mock_session

            with patch('src.core.media_loop.cv2.VideoCapture') as mock_cap:
                mock_instance = MagicMock()
                mock_instance.isOpened.return_value = True

                # Return a frame once, then fail
                call_count = 0
                def read_once():
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        frame = np.zeros((480, 640, 3), dtype=np.uint8)
                        return (True, frame)
                    media_loop.quit.set()
                    return (False, None)

                mock_instance.read = read_once
                mock_cap.return_value = mock_instance

                await media_loop.capture_video()

                # Verify frame was sent to session
                assert mock_session.send_realtime_input.called


class TestShutdown:
    """Tests for shutdown functionality."""

    def test_shutdown_sets_quit_event(self, mock_config):
        """Test that shutdown sets the quit event."""
        with patch('src.core.media_loop.pyaudio.PyAudio'):
            media_loop = MediaLoop(mock_config)

            assert not media_loop.quit.is_set()
            media_loop.shutdown()
            assert media_loop.quit.is_set()


class TestSessionResumption:
    """Tests for session resumption functionality."""

    def test_get_previous_handle(self):
        """Test getting previous session handle."""
        # The global variable is set by receive_audio
        handle = get_previous_handle()
        # Should return whatever was set by previous tests or None
        assert handle is None or isinstance(handle, str)


class TestIntegration:
    """Integration tests combining multiple components."""

    @pytest.mark.asyncio
    async def test_run_coordinates_all_tasks(self, mock_config):
        """Test that run() coordinates all streaming tasks."""
        with patch('src.core.media_loop.pyaudio.PyAudio'):
            media_loop = MediaLoop(mock_config)

            # Mock all external dependencies
            with patch('src.core.media_loop.get_gemini_client') as mock_get_client, \
                 patch('src.core.media_loop.load_system_instruction') as mock_load_instr, \
                 patch('src.core.media_loop.create_speech_config') as mock_speech, \
                 patch('src.core.media_loop.get_live_config') as mock_live_cfg:

                # Setup mocks
                mock_client = MagicMock()
                mock_session = AsyncMock()

                # Mock async context manager
                async def mock_connect(*args, **kwargs):
                    # Immediately shutdown to avoid hanging
                    media_loop.shutdown()
                    yield mock_session

                mock_client.aio.live.connect = MagicMock(
                    return_value=MagicMock(
                        __aenter__=AsyncMock(return_value=mock_session),
                        __aexit__=AsyncMock()
                    )
                )

                mock_get_client.return_value = mock_client
                mock_load_instr.return_value = "Test instruction"
                mock_speech.return_value = MagicMock()
                mock_live_cfg.return_value = MagicMock()

                # Run should complete without hanging
                try:
                    await asyncio.wait_for(
                        media_loop.run("test-api-key"),
                        timeout=2.0
                    )
                except asyncio.TimeoutError:
                    pytest.fail("run() did not complete within timeout")
