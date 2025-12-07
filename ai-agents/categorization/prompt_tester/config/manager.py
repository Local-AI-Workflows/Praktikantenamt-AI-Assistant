"""
Configuration manager for loading and validating settings.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from prompt_tester.data.schemas import Config


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

        # 2. Apply environment variable overrides
        config_dict = self._apply_env_overrides(config_dict)

        # 3. Validate and create Config object
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

    def _apply_env_overrides(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.

        Environment variables are mapped as follows:
        - OLLAMA_ENDPOINT -> ollama_endpoint
        - OLLAMA_MODEL -> ollama_model
        - OLLAMA_TIMEOUT -> ollama_timeout
        - OUTPUT_FORMAT -> output_format
        - OUTPUT_DIRECTORY -> output_directory

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
            "output": {
                "format": config.output_format,
                "directory": config.output_directory,
                "timestamp_format": config.timestamp_format,
            },
            "validation": {
                "include_confusion_matrix": config.include_confusion_matrix,
                "per_category_metrics": config.per_category_metrics,
            },
        }

        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
