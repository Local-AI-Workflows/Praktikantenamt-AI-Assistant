"""
Configuration manager for loading and validating settings.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from response_generator.data.schemas import Config


class ConfigManager:
    """Manages configuration loading from YAML files and environment variables."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the config manager.

        Args:
            config_path: Optional path to config file. If not provided, uses default.
        """
        self.config_path = config_path or self._get_default_config_path()

    def _get_default_config_path(self) -> str:
        """Get the default configuration file path."""
        # Get the package directory
        package_dir = Path(__file__).parent.parent
        return str(package_dir / "config" / "settings.yaml")

    def load_config(self) -> Config:
        """
        Load configuration from YAML file with environment variable overrides.

        Returns:
            Config: Validated configuration object

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        # 1. Load from YAML file
        config_dict = self._load_yaml()

        # 2. Flatten nested structure
        config_dict = self._flatten_config(config_dict)

        # 3. Apply environment variable overrides
        config_dict = self._apply_env_overrides(config_dict)

        # 4. Validate and create Config object
        try:
            return Config(**config_dict)
        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}")

    def _load_yaml(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        config_path = Path(self.config_path)

        if not config_path.exists():
            # If config file doesn't exist, return empty dict (will use defaults)
            return {}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
                return config or {}
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML config file: {e}")

    def _flatten_config(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten nested configuration structure to flat key-value pairs.

        Args:
            config_dict: Nested configuration dictionary

        Returns:
            Flattened configuration dictionary
        """
        flat_config: Dict[str, Any] = {}

        # Handle ollama section
        if "ollama" in config_dict:
            ollama = config_dict["ollama"]
            if "endpoint" in ollama:
                flat_config["ollama_endpoint"] = ollama["endpoint"]
            if "model" in ollama:
                flat_config["ollama_model"] = ollama["model"]
            if "timeout" in ollama:
                flat_config["ollama_timeout"] = ollama["timeout"]
            if "max_retries" in ollama:
                flat_config["ollama_max_retries"] = ollama["max_retries"]

        # Handle categories
        if "categories" in config_dict:
            flat_config["categories"] = config_dict["categories"]

        # Handle response section
        if "response" in config_dict:
            response = config_dict["response"]
            if "default_tone" in response:
                flat_config["default_tone"] = response["default_tone"]
            if "generate_both_tones" in response:
                flat_config["generate_both_tones"] = response["generate_both_tones"]
            if "personalization_enabled" in response:
                flat_config["personalization_enabled"] = response["personalization_enabled"]
            if "confidence_threshold" in response:
                flat_config["confidence_threshold"] = response["confidence_threshold"]
            if "quality_threshold" in response:
                flat_config["quality_threshold"] = response["quality_threshold"]

        # Handle output section
        if "output" in config_dict:
            output = config_dict["output"]
            if "format" in output:
                flat_config["output_format"] = output["format"]
            if "directory" in output:
                flat_config["output_directory"] = output["directory"]
            if "timestamp_format" in output:
                flat_config["timestamp_format"] = output["timestamp_format"]

        # Handle paths section
        if "paths" in config_dict:
            paths = config_dict["paths"]
            if "templates_directory" in paths:
                flat_config["templates_directory"] = paths["templates_directory"]
            if "prompts_directory" in paths:
                flat_config["prompts_directory"] = paths["prompts_directory"]

        return flat_config

    def _apply_env_overrides(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.

        Environment variables are mapped as follows:
        - OLLAMA_ENDPOINT -> ollama_endpoint
        - OLLAMA_MODEL -> ollama_model
        - OLLAMA_TIMEOUT -> ollama_timeout
        - OUTPUT_FORMAT -> output_format
        - OUTPUT_DIRECTORY -> output_directory
        - PERSONALIZATION_ENABLED -> personalization_enabled
        - GENERATE_BOTH_TONES -> generate_both_tones

        Args:
            config_dict: Configuration dictionary from YAML

        Returns:
            Updated configuration dictionary
        """
        # Map environment variables to config keys
        env_mappings = {
            "OLLAMA_ENDPOINT": "ollama_endpoint",
            "OLLAMA_MODEL": "ollama_model",
            "OLLAMA_TIMEOUT": ("ollama_timeout", int),
            "OLLAMA_MAX_RETRIES": ("ollama_max_retries", int),
            "OUTPUT_FORMAT": "output_format",
            "OUTPUT_DIRECTORY": "output_directory",
            "DEFAULT_TONE": "default_tone",
            "GENERATE_BOTH_TONES": ("generate_both_tones", self._str_to_bool),
            "PERSONALIZATION_ENABLED": ("personalization_enabled", self._str_to_bool),
            "CONFIDENCE_THRESHOLD": ("confidence_threshold", float),
            "QUALITY_THRESHOLD": ("quality_threshold", float),
            "TEMPLATES_DIRECTORY": "templates_directory",
            "PROMPTS_DIRECTORY": "prompts_directory",
        }

        for env_var, mapping in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                if isinstance(mapping, tuple):
                    # Need type conversion
                    config_key, type_converter = mapping
                    try:
                        config_dict[config_key] = type_converter(env_value)
                    except ValueError:
                        # Skip invalid value
                        pass
                else:
                    # Direct string assignment
                    config_dict[mapping] = env_value

        return config_dict

    @staticmethod
    def _str_to_bool(value: str) -> bool:
        """Convert string to boolean."""
        return value.lower() in ("true", "1", "yes", "on")

    def save_config(self, config: Config, output_path: Optional[str] = None) -> None:
        """
        Save configuration to YAML file.

        Args:
            config: Configuration object to save
            output_path: Optional output path. If not provided, uses default.
        """
        output_path = output_path or self.config_path

        # Convert Config to dict
        config_dict = {
            "ollama": {
                "endpoint": config.ollama_endpoint,
                "model": config.ollama_model,
                "timeout": config.ollama_timeout,
                "max_retries": config.ollama_max_retries,
            },
            "categories": config.categories,
            "response": {
                "default_tone": config.default_tone,
                "generate_both_tones": config.generate_both_tones,
                "personalization_enabled": config.personalization_enabled,
                "confidence_threshold": config.confidence_threshold,
                "quality_threshold": config.quality_threshold,
            },
            "output": {
                "format": config.output_format,
                "directory": config.output_directory,
                "timestamp_format": config.timestamp_format,
            },
            "paths": {
                "templates_directory": config.templates_directory,
                "prompts_directory": config.prompts_directory,
            },
        }

        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
