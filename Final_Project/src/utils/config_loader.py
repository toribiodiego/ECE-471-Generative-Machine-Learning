"""Configuration loading utilities.

This module handles loading and merging YAML configuration files and
system instruction files for the Agnus application.
"""

import os
from typing import Any, Dict, Optional
import yaml


def load_config(config_path: str = "config.yaml", media_path: str = "media.yaml") -> Dict[str, Any]:
    """Load and merge YAML configuration files.

    Loads both config.yaml (development settings) and media.yaml (runtime
    A/V parameters), merging them into a single configuration dictionary.
    Values from config.yaml take precedence over media.yaml in case of
    duplicate keys.

    Args:
        config_path: Path to the main config YAML file. Defaults to "config.yaml".
        media_path: Path to the media config YAML file. Defaults to "media.yaml".

    Returns:
        Merged configuration dictionary containing all settings.

    Raises:
        FileNotFoundError: If either configuration file does not exist.
        yaml.YAMLError: If configuration files contain invalid YAML.
    """
    if not os.path.isfile(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    if not os.path.isfile(media_path):
        raise FileNotFoundError(f"Media configuration file not found: {media_path}")

    with open(media_path, 'r') as f:
        media_cfg = yaml.safe_load(f)

    with open(config_path, 'r') as f:
        dev_cfg = yaml.safe_load(f)

    # Merge configs with dev_cfg taking precedence
    return {**media_cfg, **dev_cfg}


def load_system_instruction(config: Dict[str, Any]) -> str:
    """Load system instruction text from file.

    Reads the system instruction file path from config and loads the
    instruction text that defines the agent's personality and behavior.

    Args:
        config: Configuration dictionary containing INSTRUCTIONS_FILE key.

    Returns:
        System instruction text content.

    Raises:
        FileNotFoundError: If instruction file is missing or empty.
        KeyError: If INSTRUCTIONS_FILE key is not in config.
    """
    instruction_file = config.get("INSTRUCTIONS_FILE")
    if not instruction_file:
        raise KeyError("INSTRUCTIONS_FILE not found in configuration")

    if not os.path.isfile(instruction_file):
        raise FileNotFoundError(f"Instruction file not found: {instruction_file}")

    with open(instruction_file, encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        raise FileNotFoundError(f"Instruction file is empty: {instruction_file}")

    return text


def get_config_value(config: Dict[str, Any], key: str, default: Optional[Any] = None) -> Any:
    """Safely retrieve a configuration value with optional default.

    Args:
        config: Configuration dictionary.
        key: Configuration key to retrieve.
        default: Default value to return if key is not found. Defaults to None.

    Returns:
        Configuration value for the key, or default if key not found.
    """
    return config.get(key, default)
