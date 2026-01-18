"""
Configuration manager for loading and validating settings.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from contract_validator.data.schemas import Config


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
        flat_config = self._flatten_config(config_dict)

        # 3. Apply environment variable overrides
        flat_config = self._apply_env_overrides(flat_config)

        # 4. Validate and create Config object
        try:
            return Config(**flat_config)
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
        Flatten nested YAML structure to match Config model fields.

        Args:
            config_dict: Nested configuration dictionary

        Returns:
            Flattened configuration dictionary
        """
        flat = {}

        # Ollama settings
        if "ollama" in config_dict:
            ollama = config_dict["ollama"]
            if "endpoint" in ollama:
                flat["ollama_endpoint"] = ollama["endpoint"]
            if "model" in ollama:
                flat["ollama_model"] = ollama["model"]
            if "timeout" in ollama:
                flat["ollama_timeout"] = ollama["timeout"]
            if "max_retries" in ollama:
                flat["ollama_max_retries"] = ollama["max_retries"]

        # Validation settings
        if "validation" in config_dict:
            validation = config_dict["validation"]
            if "min_working_days" in validation:
                flat["min_working_days"] = validation["min_working_days"]

        # Output settings
        if "output" in config_dict:
            output = config_dict["output"]
            if "format" in output:
                flat["output_format"] = output["format"]
            if "directory" in output:
                flat["output_directory"] = output["directory"]
            if "timestamp_format" in output:
                flat["timestamp_format"] = output["timestamp_format"]

        return flat

    def _apply_env_overrides(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.

        Environment variables are mapped as follows:
        - OLLAMA_ENDPOINT -> ollama_endpoint
        - OLLAMA_MODEL -> ollama_model
        - OLLAMA_TIMEOUT -> ollama_timeout
        - OLLAMA_MAX_RETRIES -> ollama_max_retries
        - OUTPUT_FORMAT -> output_format
        - OUTPUT_DIRECTORY -> output_directory
        - MIN_WORKING_DAYS -> min_working_days

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
            "MIN_WORKING_DAYS": ("min_working_days", int),
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

        # Convert Config to nested dict structure
        config_dict = {
            "ollama": {
                "endpoint": config.ollama_endpoint,
                "model": config.ollama_model,
                "timeout": config.ollama_timeout,
                "max_retries": config.ollama_max_retries,
            },
            "validation": {
                "min_working_days": config.min_working_days,
            },
            "output": {
                "format": config.output_format,
                "directory": config.output_directory,
                "timestamp_format": config.timestamp_format,
            },
        }

        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        # Write to file
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
