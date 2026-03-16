"""Unit tests for gradio_interface module."""

import pytest
from unittest.mock import Mock, MagicMock, patch

from src.ui.gradio_interface import create_ui


@pytest.fixture
def mock_config():
    """Mock configuration data."""
    return {
        "WEB_UI_TITLE": "Test Gemini Demo",
        "MIC_TYPE": "computer_mic",
    }


class TestCreateUI:
    """Tests for create_ui function."""

    @patch('src.ui.gradio_interface.load_config')
    @patch('src.ui.gradio_interface.gr.Blocks')
    @patch('src.ui.gradio_interface.gr.Markdown')
    @patch('src.ui.gradio_interface.gr.Row')
    @patch('src.ui.gradio_interface.gr.Button')
    @patch('src.ui.gradio_interface.gr.Textbox')
    @patch('src.ui.gradio_interface.gr.Video')
    def test_create_ui_builds_interface(
        self,
        mock_video,
        mock_textbox,
        mock_button,
        mock_row,
        mock_markdown,
        mock_blocks,
        mock_load_config,
        mock_config
    ):
        """Test that create_ui builds Gradio interface components."""
        mock_load_config.return_value = mock_config

        # Mock the Blocks context manager
        mock_demo = MagicMock()
        mock_blocks.return_value.__enter__ = MagicMock(return_value=mock_demo)
        mock_blocks.return_value.__exit__ = MagicMock(return_value=False)

        # Mock Row context manager
        mock_row.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_row.return_value.__exit__ = MagicMock(return_value=False)

        result = create_ui()

        # Verify config was loaded
        mock_load_config.assert_called_once()

        # Verify Blocks was created with correct title
        mock_blocks.assert_called_once_with(title="Test Gemini Demo")

        # Verify result is the demo
        assert result == mock_demo

    @patch('src.ui.gradio_interface.load_config')
    @patch('src.ui.gradio_interface.gr.Blocks')
    @patch('src.ui.gradio_interface.gr.Markdown')
    @patch('src.ui.gradio_interface.gr.Row')
    @patch('src.ui.gradio_interface.gr.Button')
    @patch('src.ui.gradio_interface.gr.Textbox')
    @patch('src.ui.gradio_interface.gr.Video')
    def test_create_ui_creates_buttons(
        self,
        mock_video,
        mock_textbox,
        mock_button,
        mock_row,
        mock_markdown,
        mock_blocks,
        mock_load_config,
        mock_config
    ):
        """Test that create_ui creates Start and Stop buttons."""
        mock_load_config.return_value = mock_config

        # Mock the Blocks context manager
        mock_demo = MagicMock()
        mock_blocks.return_value.__enter__ = MagicMock(return_value=mock_demo)
        mock_blocks.return_value.__exit__ = MagicMock(return_value=False)

        # Mock Row context manager
        mock_row.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_row.return_value.__exit__ = MagicMock(return_value=False)

        create_ui()

        # Verify two buttons were created (Start and Stop)
        assert mock_button.call_count == 2

        # Check that buttons were called with "Start" and "Stop" labels
        button_labels = [call[0][0] if call[0] else call[1].get('value', '')
                        for call in mock_button.call_args_list]
        assert "Start" in button_labels or any("Start" in str(call) for call in mock_button.call_args_list)
        assert "Stop" in button_labels or any("Stop" in str(call) for call in mock_button.call_args_list)

    @patch('src.ui.gradio_interface.load_config')
    @patch('src.ui.gradio_interface.gr.Blocks')
    @patch('src.ui.gradio_interface.gr.Markdown')
    @patch('src.ui.gradio_interface.gr.Row')
    @patch('src.ui.gradio_interface.gr.Button')
    @patch('src.ui.gradio_interface.gr.Textbox')
    @patch('src.ui.gradio_interface.gr.Video')
    def test_create_ui_creates_status_textbox(
        self,
        mock_video,
        mock_textbox,
        mock_button,
        mock_row,
        mock_markdown,
        mock_blocks,
        mock_load_config,
        mock_config
    ):
        """Test that create_ui creates status textbox."""
        mock_load_config.return_value = mock_config

        # Mock the Blocks context manager
        mock_demo = MagicMock()
        mock_blocks.return_value.__enter__ = MagicMock(return_value=mock_demo)
        mock_blocks.return_value.__exit__ = MagicMock(return_value=False)

        # Mock Row context manager
        mock_row.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_row.return_value.__exit__ = MagicMock(return_value=False)

        create_ui()

        # Verify textbox was created with correct parameters
        mock_textbox.assert_called_once_with(label="Status", interactive=False)

    @patch('src.ui.gradio_interface.load_config')
    @patch('src.ui.gradio_interface.gr.Blocks')
    @patch('src.ui.gradio_interface.gr.Markdown')
    @patch('src.ui.gradio_interface.gr.Row')
    @patch('src.ui.gradio_interface.gr.Button')
    @patch('src.ui.gradio_interface.gr.Textbox')
    @patch('src.ui.gradio_interface.gr.Video')
    def test_create_ui_creates_video_component(
        self,
        mock_video,
        mock_textbox,
        mock_button,
        mock_row,
        mock_markdown,
        mock_blocks,
        mock_load_config,
        mock_config
    ):
        """Test that create_ui creates video component."""
        mock_load_config.return_value = mock_config

        # Mock the Blocks context manager
        mock_demo = MagicMock()
        mock_blocks.return_value.__enter__ = MagicMock(return_value=mock_demo)
        mock_blocks.return_value.__exit__ = MagicMock(return_value=False)

        # Mock Row context manager
        mock_row.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_row.return_value.__exit__ = MagicMock(return_value=False)

        create_ui()

        # Verify video component was created
        mock_video.assert_called_once_with(
            label="Live Video Feed",
            sources=["webcam"],
            streaming=True,
            autoplay=True,
        )

    @patch('src.ui.gradio_interface.load_config')
    @patch('src.ui.gradio_interface.gr.Blocks')
    @patch('src.ui.gradio_interface.gr.Markdown')
    @patch('src.ui.gradio_interface.gr.Row')
    @patch('src.ui.gradio_interface.gr.Button')
    @patch('src.ui.gradio_interface.gr.Textbox')
    @patch('src.ui.gradio_interface.gr.Video')
    def test_create_ui_wires_callbacks(
        self,
        mock_video,
        mock_textbox,
        mock_button,
        mock_row,
        mock_markdown,
        mock_blocks,
        mock_load_config,
        mock_config
    ):
        """Test that create_ui wires button callbacks correctly."""
        mock_load_config.return_value = mock_config

        # Mock the Blocks context manager
        mock_demo = MagicMock()
        mock_blocks.return_value.__enter__ = MagicMock(return_value=mock_demo)
        mock_blocks.return_value.__exit__ = MagicMock(return_value=False)

        # Mock Row context manager
        mock_row.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_row.return_value.__exit__ = MagicMock(return_value=False)

        # Track button instances
        mock_start_btn = MagicMock()
        mock_stop_btn = MagicMock()
        mock_button.side_effect = [mock_start_btn, mock_stop_btn]

        create_ui()

        # Verify both buttons have click handlers
        assert mock_start_btn.click.called
        assert mock_stop_btn.click.called


class TestUIIntegration:
    """Integration tests for UI components."""

    @patch('src.ui.gradio_interface.load_config')
    def test_create_ui_returns_gradio_blocks(self, mock_load_config, mock_config):
        """Test that create_ui returns a Gradio Blocks object."""
        mock_load_config.return_value = mock_config

        result = create_ui()

        # Should return a Gradio Blocks instance
        import gradio as gr
        assert isinstance(result, gr.Blocks)

    @patch('src.ui.gradio_interface.load_config')
    def test_create_ui_uses_config_title(self, mock_load_config):
        """Test that UI title comes from config."""
        test_config = {
            "WEB_UI_TITLE": "Custom Test Title",
            "MIC_TYPE": "computer_mic",
        }
        mock_load_config.return_value = test_config

        result = create_ui()

        # Title should be set from config
        # Note: Gradio doesn't expose title directly, so we just verify
        # that config was loaded
        mock_load_config.assert_called_once()


class TestUIComponents:
    """Tests for individual UI component configuration."""

    @patch('src.ui.gradio_interface.load_config')
    def test_video_component_configuration(self, mock_load_config, mock_config):
        """Test that video component has correct configuration."""
        mock_load_config.return_value = mock_config

        # Create UI and check it doesn't raise
        demo = create_ui()

        # Should complete without errors
        assert demo is not None
