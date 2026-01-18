"""
Configuration manager for loading and validating settings.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

from workday_calculator.data.schemas import Bundesland, Config


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
        package_dir = Path(__file__).parent.parent
        return str(package_dir / "config" / "settings.yaml")

    def load_config(self) -> Config:
        """
        Load configuration from YAML file with environment variable overrides.

        Returns:
            Config: Validated configuration object.

        Raises:
            ValueError: If config is invalid.
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
                return self._flatten_config(config) if config else {}
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML config file: {e}")

    def _flatten_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flatten nested YAML config to match Config model fields.

        Args:
            config: Nested configuration dictionary.

        Returns:
            Flattened configuration dictionary.
        """
        result = {}

        # Handle location section
        if "location" in config:
            loc = config["location"]
            if "default_bundesland" in loc:
                result["default_bundesland"] = loc["default_bundesland"]
            if "geocoding_enabled" in loc:
                result["geocoding_enabled"] = loc["geocoding_enabled"]
            if "geocoding_timeout" in loc:
                result["geocoding_timeout"] = loc["geocoding_timeout"]

        # Handle holidays section
        if "holidays" in config:
            hol = config["holidays"]
            if "language" in hol:
                result["holiday_language"] = hol["language"]

        # Handle output section
        if "output" in config:
            out = config["output"]
            if "format" in out:
                result["output_format"] = out["format"]
            if "directory" in out:
                result["output_directory"] = out["directory"]

        # Handle API section
        if "api" in config:
            api = config["api"]
            if "host" in api:
                result["api_host"] = api["host"]
            if "port" in api:
                result["api_port"] = api["port"]

        return result

    def _apply_env_overrides(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.

        Environment variables:
        - WORKDAY_DEFAULT_BUNDESLAND -> default_bundesland
        - WORKDAY_GEOCODING_ENABLED -> geocoding_enabled
        - WORKDAY_GEOCODING_TIMEOUT -> geocoding_timeout
        - WORKDAY_HOLIDAY_LANGUAGE -> holiday_language
        - WORKDAY_OUTPUT_FORMAT -> output_format
        - WORKDAY_OUTPUT_DIRECTORY -> output_directory
        - WORKDAY_API_HOST -> api_host
        - WORKDAY_API_PORT -> api_port

        Args:
            config_dict: Configuration dictionary from YAML.

        Returns:
            Updated configuration dictionary.
        """
        env_mappings = {
            "WORKDAY_DEFAULT_BUNDESLAND": "default_bundesland",
            "WORKDAY_GEOCODING_ENABLED": ("geocoding_enabled", self._parse_bool),
            "WORKDAY_GEOCODING_TIMEOUT": ("geocoding_timeout", int),
            "WORKDAY_HOLIDAY_LANGUAGE": "holiday_language",
            "WORKDAY_OUTPUT_FORMAT": "output_format",
            "WORKDAY_OUTPUT_DIRECTORY": "output_directory",
            "WORKDAY_API_HOST": "api_host",
            "WORKDAY_API_PORT": ("api_port", int),
        }

        for env_var, mapping in env_mappings.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                if isinstance(mapping, tuple):
                    config_key, type_converter = mapping
                    try:
                        config_dict[config_key] = type_converter(env_value)
                    except ValueError:
                        pass  # Skip invalid value
                else:
                    config_dict[mapping] = env_value

        return config_dict

    def _parse_bool(self, value: str) -> bool:
        """Parse a boolean from string."""
        return value.lower() in ("true", "1", "yes", "on")

    def save_config(self, config: Config, output_path: Optional[str] = None) -> None:
        """
        Save configuration to YAML file.

        Args:
            config: Configuration object to save.
            output_path: Optional output path. If not provided, uses default.
        """
        output_path = output_path or self.config_path

        config_dict = {
            "location": {
                "default_bundesland": config.default_bundesland.value if config.default_bundesland else None,
                "geocoding_enabled": config.geocoding_enabled,
                "geocoding_timeout": config.geocoding_timeout,
            },
            "holidays": {
                "language": config.holiday_language,
            },
            "output": {
                "format": config.output_format,
                "directory": config.output_directory,
            },
            "api": {
                "host": config.api_host,
                "port": config.api_port,
            },
        }

        # Ensure directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
