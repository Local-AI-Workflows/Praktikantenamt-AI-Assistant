"""Configuration management with YAML and environment variable support.

Supports bilingual operation (English/German) via the language setting.
"""

import logging
import os
from pathlib import Path
from typing import Any, Optional

import yaml

from company_lookup.data.schemas import Config

logger = logging.getLogger(__name__)

# Default config file path
DEFAULT_CONFIG_PATH = Path(__file__).parent / "settings.yaml"


class ConfigManager:
    """Manages configuration loading from YAML files and environment variables."""

    # Environment variable prefix
    ENV_PREFIX = "COMPANY_LOOKUP_"

    # Mapping of environment variables to config fields
    ENV_MAPPINGS = {
        "COMPANY_LOOKUP_EXCEL_FILE": "excel_file_path",
        "COMPANY_LOOKUP_THRESHOLD": "default_fuzzy_threshold",
        "COMPANY_LOOKUP_CASE_SENSITIVE": "case_sensitive",
        "COMPANY_LOOKUP_WHITELIST_SHEET": "whitelist_sheet",
        "COMPANY_LOOKUP_BLACKLIST_SHEET": "blacklist_sheet",
        "COMPANY_LOOKUP_API_HOST": "api_host",
        "COMPANY_LOOKUP_API_PORT": "api_port",
        "COMPANY_LOOKUP_OUTPUT_FORMAT": "output_format",
        "COMPANY_LOOKUP_OUTPUT_DIR": "output_directory",
        "COMPANY_LOOKUP_LANGUAGE": "language",
    }

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the config manager.

        Args:
            config_path: Path to YAML config file. Uses default if not provided.
        """
        self.config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self._config: Optional[Config] = None

    def load(self) -> Config:
        """Load configuration from file and environment variables.

        Returns:
            Config object with merged configuration.
        """
        # Start with defaults
        config_dict: dict[str, Any] = {}

        # Load from YAML file if it exists
        if self.config_path.exists():
            config_dict = self._load_yaml()
            logger.debug(f"Loaded config from: {self.config_path}")
        else:
            logger.debug(f"Config file not found: {self.config_path}, using defaults")

        # Apply environment variable overrides
        config_dict = self._apply_env_overrides(config_dict)

        # Create Config object
        self._config = Config(**config_dict)
        return self._config

    def _load_yaml(self) -> dict[str, Any]:
        """Load configuration from YAML file.

        Returns:
            Dictionary of configuration values.
        """
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Error loading config file: {e}")
            return {}

        # Flatten nested structure
        config_dict: dict[str, Any] = {}

        # Language setting
        if "language" in raw_config:
            config_dict["language"] = raw_config["language"]

        # Excel settings
        if "excel" in raw_config:
            excel = raw_config["excel"]
            if "file_path" in excel:
                config_dict["excel_file_path"] = excel["file_path"]
            if "whitelist_sheet" in excel:
                config_dict["whitelist_sheet"] = excel["whitelist_sheet"]
            if "blacklist_sheet" in excel:
                config_dict["blacklist_sheet"] = excel["blacklist_sheet"]
            if "company_name_column" in excel:
                config_dict["company_name_column"] = excel["company_name_column"]
            if "notes_column" in excel:
                config_dict["notes_column"] = excel["notes_column"]
            if "category_column" in excel:
                config_dict["category_column"] = excel["category_column"]

        # Matching settings
        if "matching" in raw_config:
            matching = raw_config["matching"]
            if "default_threshold" in matching:
                config_dict["default_fuzzy_threshold"] = matching["default_threshold"]
            if "case_sensitive" in matching:
                config_dict["case_sensitive"] = matching["case_sensitive"]

        # Output settings
        if "output" in raw_config:
            output = raw_config["output"]
            if "format" in output:
                config_dict["output_format"] = output["format"]
            if "directory" in output:
                config_dict["output_directory"] = output["directory"]

        # API settings
        if "api" in raw_config:
            api = raw_config["api"]
            if "host" in api:
                config_dict["api_host"] = api["host"]
            if "port" in api:
                config_dict["api_port"] = api["port"]

        return config_dict

    def _apply_env_overrides(self, config_dict: dict[str, Any]) -> dict[str, Any]:
        """Apply environment variable overrides to config.

        Args:
            config_dict: Current configuration dictionary.

        Returns:
            Updated configuration dictionary.
        """
        for env_var, config_key in self.ENV_MAPPINGS.items():
            value = os.environ.get(env_var)
            if value is not None:
                # Parse value based on expected type
                if config_key in ("case_sensitive",):
                    config_dict[config_key] = value.lower() in ("true", "1", "yes")
                elif config_key in ("default_fuzzy_threshold",):
                    config_dict[config_key] = float(value)
                elif config_key in ("api_port",):
                    config_dict[config_key] = int(value)
                else:
                    config_dict[config_key] = value
                logger.debug(f"Override from env: {env_var} -> {config_key}")

        return config_dict

    @property
    def config(self) -> Config:
        """Get the current configuration, loading if needed.

        Returns:
            Config object.
        """
        if self._config is None:
            self.load()
        return self._config  # type: ignore

    def reload(self) -> Config:
        """Reload configuration from file and environment.

        Returns:
            Freshly loaded Config object.
        """
        self._config = None
        return self.load()

    def save(self, config: Config, path: Optional[str] = None) -> None:
        """Save configuration to a YAML file.

        Args:
            config: Configuration to save.
            path: Path to save to (uses self.config_path if not provided).
        """
        save_path = Path(path) if path else self.config_path

        # Convert to nested YAML structure
        yaml_config = {
            "language": config.language,
            "excel": {
                "file_path": config.excel_file_path,
                "whitelist_sheet": config.whitelist_sheet,
                "blacklist_sheet": config.blacklist_sheet,
                "company_name_column": config.company_name_column,
                "notes_column": config.notes_column,
                "category_column": config.category_column,
            },
            "matching": {
                "default_threshold": config.default_fuzzy_threshold,
                "case_sensitive": config.case_sensitive,
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

        with open(save_path, "w", encoding="utf-8") as f:
            yaml.dump(yaml_config, f, default_flow_style=False, allow_unicode=True)

        logger.info(f"Saved configuration to: {save_path}")
