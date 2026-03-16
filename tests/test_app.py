"""Unit tests for main application entry point."""

import pytest
from unittest.mock import Mock, MagicMock, patch
import argparse

from src.app import parse_args, main


class TestParseArgs:
    """Tests for command-line argument parsing."""

    def test_parse_args_defaults(self):
        """Test default argument values."""
        with patch('sys.argv', ['app.py']):
            args = parse_args()

            assert args.port == 7860
            assert args.share is False
            assert args.debug is False

    def test_parse_args_custom_port(self):
        """Test custom port argument."""
        with patch('sys.argv', ['app.py', '--port', '8080']):
            args = parse_args()

            assert args.port == 8080
            assert args.share is False
            assert args.debug is False

    def test_parse_args_share_enabled(self):
        """Test share flag."""
        with patch('sys.argv', ['app.py', '--share']):
            args = parse_args()

            assert args.port == 7860
            assert args.share is True
            assert args.debug is False

    def test_parse_args_debug_enabled(self):
        """Test debug flag."""
        with patch('sys.argv', ['app.py', '--debug']):
            args = parse_args()

            assert args.port == 7860
            assert args.share is False
            assert args.debug is True

    def test_parse_args_all_options(self):
        """Test all options together."""
        with patch('sys.argv', ['app.py', '--port', '9000', '--share', '--debug']):
            args = parse_args()

            assert args.port == 9000
            assert args.share is True
            assert args.debug is True


class TestMain:
    """Tests for main application function."""

    @patch('src.app.create_ui')
    @patch('src.app.parse_args')
    def test_main_launches_with_defaults(self, mock_parse_args, mock_create_ui):
        """Test that main launches UI with default arguments."""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.port = 7860
        mock_args.share = False
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        # Mock UI
        mock_demo = MagicMock()
        mock_create_ui.return_value = mock_demo

        # Run main
        main()

        # Verify UI was created and launched
        mock_create_ui.assert_called_once()
        mock_demo.launch.assert_called_once_with(
            server_port=7860,
            share=False,
            debug=False,
        )

    @patch('src.app.create_ui')
    @patch('src.app.parse_args')
    def test_main_launches_with_custom_port(self, mock_parse_args, mock_create_ui):
        """Test that main launches UI with custom port."""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.port = 8080
        mock_args.share = False
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        # Mock UI
        mock_demo = MagicMock()
        mock_create_ui.return_value = mock_demo

        # Run main
        main()

        # Verify launch was called with custom port
        mock_demo.launch.assert_called_once_with(
            server_port=8080,
            share=False,
            debug=False,
        )

    @patch('src.app.create_ui')
    @patch('src.app.parse_args')
    def test_main_launches_with_share(self, mock_parse_args, mock_create_ui):
        """Test that main launches UI with share enabled."""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.port = 7860
        mock_args.share = True
        mock_args.debug = False
        mock_parse_args.return_value = mock_args

        # Mock UI
        mock_demo = MagicMock()
        mock_create_ui.return_value = mock_demo

        # Run main
        main()

        # Verify launch was called with share=True
        mock_demo.launch.assert_called_once_with(
            server_port=7860,
            share=True,
            debug=False,
        )

    @patch('src.app.create_ui')
    @patch('src.app.parse_args')
    def test_main_launches_with_debug(self, mock_parse_args, mock_create_ui):
        """Test that main launches UI with debug enabled."""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.port = 7860
        mock_args.share = False
        mock_args.debug = True
        mock_parse_args.return_value = mock_args

        # Mock UI
        mock_demo = MagicMock()
        mock_create_ui.return_value = mock_demo

        # Run main
        main()

        # Verify launch was called with debug=True
        mock_demo.launch.assert_called_once_with(
            server_port=7860,
            share=False,
            debug=True,
        )

    @patch('src.app.create_ui')
    @patch('src.app.parse_args')
    def test_main_launches_with_all_options(self, mock_parse_args, mock_create_ui):
        """Test that main launches UI with all options enabled."""
        # Mock arguments
        mock_args = MagicMock()
        mock_args.port = 9000
        mock_args.share = True
        mock_args.debug = True
        mock_parse_args.return_value = mock_args

        # Mock UI
        mock_demo = MagicMock()
        mock_create_ui.return_value = mock_demo

        # Run main
        main()

        # Verify launch was called with all options
        mock_demo.launch.assert_called_once_with(
            server_port=9000,
            share=True,
            debug=True,
        )


class TestIntegration:
    """Integration tests for application entry point."""

    @patch('src.app.create_ui')
    def test_import_and_structure(self, mock_create_ui):
        """Test that module imports and has correct structure."""
        from src import app

        # Verify functions exist
        assert hasattr(app, 'parse_args')
        assert hasattr(app, 'main')
        assert callable(app.parse_args)
        assert callable(app.main)

    def test_help_message(self):
        """Test that help message is available."""
        with patch('sys.argv', ['app.py', '--help']):
            with pytest.raises(SystemExit) as exc_info:
                parse_args()

            # Help should exit with code 0
            assert exc_info.value.code == 0
