"""
Configuration management with YAML + environment variable overrides.
"""

import os
import re
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

from workflow_validator.data.schemas import (
    FolderMapping,
    IMAPConfig,
    SMTPConfig,
    WorkflowValidationConfig,
)


class ConfigManager:
    """Manages configuration loading with environment variable overrides."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config manager.

        Args:
            config_path: Optional path to config YAML file
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            # Default to settings.yaml in config directory
            self.config_path = Path(__file__).parent / "settings.yaml"

        # Load .env file from project root
        env_path = Path(__file__).parent.parent.parent / ".env"
        if env_path.exists():
            load_dotenv(env_path)

    def load_config(self) -> WorkflowValidationConfig:
        """
        Load configuration from YAML file and apply environment overrides.

        Priority: Code defaults → YAML → .env file → Environment variables

        Loads secrets from .env file in project root if it exists.

        Returns:
            WorkflowValidationConfig object

        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config is invalid
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        # Load YAML
        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        # Replace environment variable placeholders
        data = self._replace_env_vars(data)

        # Build Pydantic config
        try:
            # Extract nested configs
            imap_config = IMAPConfig(**data["imap"])
            smtp_config = SMTPConfig(**data["smtp"])

            folder_mappings = [
                FolderMapping(**fm) for fm in data.get("folder_mappings", [])
            ]

            # Build main config
            config = WorkflowValidationConfig(
                imap=imap_config,
                smtp=smtp_config,
                folder_mappings=folder_mappings or None,  # Use defaults if empty
                wait_time_seconds=data.get("validation", {}).get(
                    "wait_time_seconds", 120
                ),
                cleanup_after_test=data.get("validation", {}).get(
                    "cleanup_after_test", True
                ),
                uuid_storage_path=data.get("validation", {}).get(
                    "uuid_storage_path", "results/uuid_mapping.json"
                ),
                categories=data.get("categories", None),  # Use defaults if not provided
                output_format=data.get("output", {}).get("format", "both"),
                output_directory=data.get("output", {}).get("directory", "results"),
                timestamp_format=data.get("output", {}).get(
                    "timestamp_format", "%Y%m%d_%H%M%S"
                ),
            )

            return config

        except Exception as e:
            raise ValueError(f"Invalid configuration: {e}")

    def _replace_env_vars(self, data: dict) -> dict:
        """
        Recursively replace ${VAR_NAME} placeholders with environment variables.

        Args:
            data: Configuration dict

        Returns:
            Dict with environment variables replaced
        """
        if isinstance(data, dict):
            return {k: self._replace_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._replace_env_vars(item) for item in data]
        elif isinstance(data, str):
            # Replace ${VAR_NAME} with environment variable
            pattern = r"\$\{([A-Z_]+)\}"
            matches = re.findall(pattern, data)
            for var_name in matches:
                env_value = os.getenv(var_name, "")
                if not env_value:
                    env_path = Path(__file__).parent.parent.parent / ".env"
                    raise ValueError(
                        f"Environment variable {var_name} not set.\n"
                        f"Please add it to {env_path}\n"
                        f"Or set it with: export {var_name}='your-value'"
                    )
                data = data.replace(f"${{{var_name}}}", env_value)
            return data
        else:
            return data
