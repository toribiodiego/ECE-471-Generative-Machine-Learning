"""Unit tests for gemini_client module."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.utils.gemini_client import (
    get_gemini_client,
    create_speech_config,
    get_live_config,
)


class TestGetGeminiClient:
    """Tests for get_gemini_client function."""

    @patch('src.utils.gemini_client.genai.Client')
    def test_get_gemini_client_success(self, mock_client_class):
        """Test successful client creation with valid API key."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        api_key = "test-api-key-12345"
        http_options = {"api_version": "v1alpha"}

        result = get_gemini_client(api_key, http_options)

        mock_client_class.assert_called_once_with(
            api_key=api_key,
            http_options=http_options
        )
        assert result == mock_client

    def test_get_gemini_client_empty_key(self):
        """Test that empty API key raises ValueError."""
        with pytest.raises(ValueError, match="API key cannot be None or empty"):
            get_gemini_client("", {"api_version": "v1alpha"})

    def test_get_gemini_client_none_key(self):
        """Test that None API key raises ValueError."""
        with pytest.raises(ValueError, match="API key cannot be None or empty"):
            get_gemini_client(None, {"api_version": "v1alpha"})

    @patch('src.utils.gemini_client.genai.Client')
    def test_get_gemini_client_with_different_options(self, mock_client_class):
        """Test client creation with different HTTP options."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        api_key = "test-key"
        http_options = {"api_version": "v2beta", "timeout": 30}

        result = get_gemini_client(api_key, http_options)

        mock_client_class.assert_called_once_with(
            api_key=api_key,
            http_options=http_options
        )


class TestCreateSpeechConfig:
    """Tests for create_speech_config function."""

    @patch('src.utils.gemini_client.types')
    def test_create_speech_config_with_voice(self, mock_types):
        """Test speech config creation with specified voice."""
        mock_speech_config = Mock()
        mock_types.SpeechConfig.return_value = mock_speech_config
        mock_voice_config = Mock()
        mock_types.VoiceConfig.return_value = mock_voice_config
        mock_prebuilt = Mock()
        mock_types.PrebuiltVoiceConfig.return_value = mock_prebuilt

        result = create_speech_config("Leda")

        mock_types.PrebuiltVoiceConfig.assert_called_once_with(voice_name="Leda")
        mock_types.VoiceConfig.assert_called_once_with(
            prebuilt_voice_config=mock_prebuilt
        )
        mock_types.SpeechConfig.assert_called_once_with(
            voice_config=mock_voice_config
        )
        assert result == mock_speech_config

    @patch('src.utils.gemini_client.types')
    def test_create_speech_config_different_voices(self, mock_types):
        """Test speech config creation with different voice names."""
        for voice_name in ["Leda", "Aoede", "Charon"]:
            mock_types.reset_mock()
            create_speech_config(voice_name)
            mock_types.PrebuiltVoiceConfig.assert_called_once_with(
                voice_name=voice_name
            )


class TestGetLiveConfig:
    """Tests for get_live_config function."""

    @patch('src.utils.gemini_client.types')
    def test_get_live_config_without_previous_handle(self, mock_types):
        """Test live config creation without session resumption."""
        mock_live_config = Mock()
        mock_types.LiveConnectConfig.return_value = mock_live_config

        system_instruction = "You are a helpful assistant."
        response_modalities = ["AUDIO"]
        speech_config = Mock()

        result = get_live_config(
            system_instruction=system_instruction,
            response_modalities=response_modalities,
            speech_config=speech_config,
            previous_handle=None
        )

        # Verify LiveConnectConfig was called with correct parameters
        call_kwargs = mock_types.LiveConnectConfig.call_args[1]
        assert call_kwargs['response_modalities'] == response_modalities
        assert call_kwargs['speech_config'] == speech_config
        assert result == mock_live_config

    @patch('src.utils.gemini_client.types')
    def test_get_live_config_with_previous_handle(self, mock_types):
        """Test live config creation with session resumption handle."""
        mock_live_config = Mock()
        mock_types.LiveConnectConfig.return_value = mock_live_config
        mock_session_resumption = Mock()
        mock_types.SessionResumptionConfig.return_value = mock_session_resumption

        previous_handle = "previous-session-handle-123"
        result = get_live_config(
            system_instruction="Test instruction",
            response_modalities=["AUDIO"],
            speech_config=Mock(),
            previous_handle=previous_handle
        )

        # Verify SessionResumptionConfig was called with handle
        mock_types.SessionResumptionConfig.assert_called_once_with(
            handle=previous_handle
        )

    @patch('src.utils.gemini_client.types')
    def test_get_live_config_creates_system_instruction(self, mock_types):
        """Test that system instruction is properly formatted."""
        mock_content = Mock()
        mock_types.Content.return_value = mock_content
        mock_part = Mock()
        mock_types.Part.from_text.return_value = mock_part

        instruction_text = "You are a sarcastic AI assistant."
        get_live_config(
            system_instruction=instruction_text,
            response_modalities=["AUDIO"],
            speech_config=Mock(),
            previous_handle=None
        )

        # Verify Part.from_text was called with instruction text
        mock_types.Part.from_text.assert_called_once_with(text=instruction_text)

        # Verify Content was called with correct structure
        mock_types.Content.assert_called_once_with(
            parts=[mock_part],
            role="user"
        )

    @patch('src.utils.gemini_client.types')
    def test_get_live_config_creates_context_compression(self, mock_types):
        """Test that context window compression is configured."""
        mock_sliding_window = Mock()
        mock_types.SlidingWindow.return_value = mock_sliding_window
        mock_compression_config = Mock()
        mock_types.ContextWindowCompressionConfig.return_value = mock_compression_config

        get_live_config(
            system_instruction="Test",
            response_modalities=["AUDIO"],
            speech_config=Mock(),
            previous_handle=None
        )

        # Verify SlidingWindow was created
        mock_types.SlidingWindow.assert_called_once()

        # Verify ContextWindowCompressionConfig was created with sliding window
        mock_types.ContextWindowCompressionConfig.assert_called_once_with(
            sliding_window=mock_sliding_window
        )

    @patch('src.utils.gemini_client.types')
    def test_get_live_config_with_multiple_modalities(self, mock_types):
        """Test live config with multiple response modalities."""
        modalities = ["AUDIO", "TEXT"]
        get_live_config(
            system_instruction="Test",
            response_modalities=modalities,
            speech_config=Mock(),
            previous_handle=None
        )

        call_kwargs = mock_types.LiveConnectConfig.call_args[1]
        assert call_kwargs['response_modalities'] == modalities


class TestIntegration:
    """Integration tests combining multiple functions."""

    @patch('src.utils.gemini_client.types')
    def test_create_speech_config_and_use_in_live_config(self, mock_types):
        """Test creating speech config and using it in live config."""
        mock_speech_config = Mock()
        mock_types.SpeechConfig.return_value = mock_speech_config

        # Create speech config
        speech_config = create_speech_config("Leda")

        # Use it in live config
        get_live_config(
            system_instruction="Test",
            response_modalities=["AUDIO"],
            speech_config=speech_config,
            previous_handle=None
        )

        # Verify speech_config was passed to LiveConnectConfig
        call_kwargs = mock_types.LiveConnectConfig.call_args[1]
        assert call_kwargs['speech_config'] == mock_speech_config
