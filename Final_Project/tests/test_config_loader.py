"""Unit tests for config_loader module."""

import os
import pytest
import tempfile
from pathlib import Path

from src.utils.config_loader import (
    load_config,
    load_system_instruction,
    get_config_value,
)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_config_merges_yaml_files(self, tmp_path):
        """Test that config.yaml and media.yaml are merged correctly."""
        # Create test config files
        config_file = tmp_path / "config.yaml"
        media_file = tmp_path / "media.yaml"

        config_file.write_text("MIC_TYPE: dynamic_mic\nVOICE_NAME: Leda\n")
        media_file.write_text("INPUT_SAMPLE_RATE: 16000\nOUTPUT_SAMPLE_RATE: 24000\n")

        result = load_config(str(config_file), str(media_file))

        assert result["MIC_TYPE"] == "dynamic_mic"
        assert result["VOICE_NAME"] == "Leda"
        assert result["INPUT_SAMPLE_RATE"] == 16000
        assert result["OUTPUT_SAMPLE_RATE"] == 24000

    def test_load_config_dev_takes_precedence(self, tmp_path):
        """Test that config.yaml values override media.yaml on duplicate keys."""
        config_file = tmp_path / "config.yaml"
        media_file = tmp_path / "media.yaml"

        config_file.write_text("MIC_TYPE: dynamic_mic\nSHARED_KEY: from_config\n")
        media_file.write_text("INPUT_SAMPLE_RATE: 16000\nSHARED_KEY: from_media\n")

        result = load_config(str(config_file), str(media_file))

        assert result["SHARED_KEY"] == "from_config"

    def test_load_config_missing_config_file(self, tmp_path):
        """Test that FileNotFoundError is raised when config.yaml is missing."""
        media_file = tmp_path / "media.yaml"
        media_file.write_text("INPUT_SAMPLE_RATE: 16000\n")

        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_config(str(tmp_path / "nonexistent.yaml"), str(media_file))

    def test_load_config_missing_media_file(self, tmp_path):
        """Test that FileNotFoundError is raised when media.yaml is missing."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("MIC_TYPE: dynamic_mic\n")

        with pytest.raises(FileNotFoundError, match="Media configuration file not found"):
            load_config(str(config_file), str(tmp_path / "nonexistent.yaml"))

    def test_load_config_invalid_yaml(self, tmp_path):
        """Test that YAMLError is raised for invalid YAML syntax."""
        config_file = tmp_path / "config.yaml"
        media_file = tmp_path / "media.yaml"

        config_file.write_text("invalid: yaml: syntax: here:\n")
        media_file.write_text("INPUT_SAMPLE_RATE: 16000\n")

        with pytest.raises(Exception):  # yaml.YAMLError
            load_config(str(config_file), str(media_file))


class TestLoadSystemInstruction:
    """Tests for load_system_instruction function."""

    def test_load_system_instruction_success(self, tmp_path):
        """Test successful loading of system instruction file."""
        instruction_file = tmp_path / "instructions.txt"
        instruction_text = "You are a helpful assistant.\nBe polite and friendly."
        instruction_file.write_text(instruction_text)

        config = {"INSTRUCTIONS_FILE": str(instruction_file)}
        result = load_system_instruction(config)

        assert result == instruction_text.strip()

    def test_load_system_instruction_missing_key(self):
        """Test that KeyError is raised when INSTRUCTIONS_FILE is not in config."""
        config = {}

        with pytest.raises(KeyError, match="INSTRUCTIONS_FILE not found"):
            load_system_instruction(config)

    def test_load_system_instruction_file_not_found(self, tmp_path):
        """Test that FileNotFoundError is raised when instruction file doesn't exist."""
        config = {"INSTRUCTIONS_FILE": str(tmp_path / "nonexistent.txt")}

        with pytest.raises(FileNotFoundError, match="Instruction file not found"):
            load_system_instruction(config)

    def test_load_system_instruction_empty_file(self, tmp_path):
        """Test that FileNotFoundError is raised when instruction file is empty."""
        instruction_file = tmp_path / "instructions.txt"
        instruction_file.write_text("")

        config = {"INSTRUCTIONS_FILE": str(instruction_file)}

        with pytest.raises(FileNotFoundError, match="Instruction file is empty"):
            load_system_instruction(config)

    def test_load_system_instruction_strips_whitespace(self, tmp_path):
        """Test that leading/trailing whitespace is stripped."""
        instruction_file = tmp_path / "instructions.txt"
        instruction_file.write_text("\n\n  You are helpful.  \n\n")

        config = {"INSTRUCTIONS_FILE": str(instruction_file)}
        result = load_system_instruction(config)

        assert result == "You are helpful."


class TestGetConfigValue:
    """Tests for get_config_value function."""

    def test_get_config_value_exists(self):
        """Test retrieving an existing config value."""
        config = {"MIC_TYPE": "dynamic_mic", "VOICE_NAME": "Leda"}

        result = get_config_value(config, "MIC_TYPE")

        assert result == "dynamic_mic"

    def test_get_config_value_missing_with_default(self):
        """Test retrieving missing key returns default value."""
        config = {"MIC_TYPE": "dynamic_mic"}

        result = get_config_value(config, "NONEXISTENT_KEY", default="fallback")

        assert result == "fallback"

    def test_get_config_value_missing_without_default(self):
        """Test retrieving missing key without default returns None."""
        config = {"MIC_TYPE": "dynamic_mic"}

        result = get_config_value(config, "NONEXISTENT_KEY")

        assert result is None

    def test_get_config_value_none_value(self):
        """Test that explicit None values in config are returned."""
        config = {"KEY_WITH_NONE": None}

        result = get_config_value(config, "KEY_WITH_NONE", default="fallback")

        # Should return None from config, not the default
        assert result is None
