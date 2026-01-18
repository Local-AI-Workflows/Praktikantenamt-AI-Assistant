"""
Data loading utilities for contracts, prompts, and company lists.
"""

import json
from datetime import date
from pathlib import Path
from typing import List, Set

import yaml

from contract_validator.data.schemas import (
    Contract,
    ContractDataset,
    ContractFormat,
    GroundTruth,
    PromptConfig,
    ValidationStatus,
)


class DataLoader:
    """Loads test data from JSON files, prompts from text files, and company lists from YAML."""

    @staticmethod
    def load_contracts(file_path: str) -> List[Contract]:
        """
        Load contracts from JSON file.

        Args:
            file_path: Path to JSON file containing contracts

        Returns:
            List of Contract objects

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is invalid or doesn't match schema
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Contract dataset file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Parse contracts manually to handle date conversion
            contracts = []
            for c in data.get("contracts", []):
                ground_truth_data = c.get("ground_truth", {})

                # Parse dates
                start_date = date.fromisoformat(ground_truth_data.get("start_date"))
                end_date = date.fromisoformat(ground_truth_data.get("end_date"))

                ground_truth = GroundTruth(
                    student_name=ground_truth_data.get("student_name"),
                    matrikelnummer=ground_truth_data.get("matrikelnummer"),
                    company_name=ground_truth_data.get("company_name"),
                    company_address=ground_truth_data.get("company_address"),
                    start_date=start_date,
                    end_date=end_date,
                    working_days=ground_truth_data.get("working_days"),
                    expected_status=ValidationStatus(ground_truth_data.get("expected_status")),
                )

                contract = Contract(
                    id=c.get("id"),
                    text=c.get("text"),
                    format=ContractFormat(c.get("format")),
                    ground_truth=ground_truth,
                    metadata=c.get("metadata"),
                )
                contracts.append(contract)

            return contracts

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading contracts from {file_path}: {e}")

    @staticmethod
    def load_dataset(file_path: str) -> ContractDataset:
        """
        Load complete contract dataset including metadata.

        Args:
            file_path: Path to JSON file containing dataset

        Returns:
            ContractDataset object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If JSON is invalid or doesn't match schema
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Contract dataset file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            contracts = DataLoader.load_contracts(file_path)

            return ContractDataset(
                metadata=data.get("metadata", {}),
                contracts=contracts,
            )

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading dataset from {file_path}: {e}")

    @staticmethod
    def load_prompt(file_path: str) -> str:
        """
        Load prompt from text file.

        Args:
            file_path: Path to prompt text file

        Returns:
            Prompt text content

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise ValueError(f"Error loading prompt from {file_path}: {e}")

    @staticmethod
    def create_prompt_config(
        name: str,
        version: str,
        system_prompt_path: str,
        user_prompt_path: str,
    ) -> PromptConfig:
        """
        Create a PromptConfig from prompt files.

        Args:
            name: Prompt name/identifier
            version: Prompt version
            system_prompt_path: Path to system prompt file
            user_prompt_path: Path to user prompt template file

        Returns:
            PromptConfig object

        Raises:
            FileNotFoundError: If any prompt file doesn't exist
        """
        system_prompt = DataLoader.load_prompt(system_prompt_path)
        user_prompt_template = DataLoader.load_prompt(user_prompt_path)

        return PromptConfig(
            name=name,
            version=version,
            system_prompt=system_prompt,
            user_prompt_template=user_prompt_template,
        )

    @staticmethod
    def load_company_lists(file_path: str) -> tuple:
        """
        Load company whitelist and blacklist from YAML file.

        Args:
            file_path: Path to YAML file containing company lists

        Returns:
            Tuple of (whitelist: Set[str], blacklist: Set[str])

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"Company lists file not found: {file_path}")

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            whitelist = set(data.get("whitelist", []))
            blacklist = set(data.get("blacklist", []))

            return whitelist, blacklist

        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {file_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading company lists from {file_path}: {e}")

    @staticmethod
    def validate_contracts(
        contracts: List[Contract],
        valid_formats: List[ContractFormat] = None,
        valid_statuses: List[ValidationStatus] = None,
    ) -> bool:
        """
        Validate that all contracts have valid formats and statuses.

        Args:
            contracts: List of contracts to validate
            valid_formats: List of valid format names (optional, uses all if None)
            valid_statuses: List of valid status names (optional, uses all if None)

        Returns:
            True if all contracts are valid

        Raises:
            ValueError: If any contract has invalid format or status
        """
        if valid_formats is None:
            valid_formats = list(ContractFormat)

        if valid_statuses is None:
            valid_statuses = list(ValidationStatus)

        invalid_contracts = []

        for contract in contracts:
            errors = []

            if contract.format not in valid_formats:
                errors.append(f"invalid format '{contract.format}'")

            if contract.ground_truth.expected_status not in valid_statuses:
                errors.append(
                    f"invalid expected_status '{contract.ground_truth.expected_status}'"
                )

            if errors:
                invalid_contracts.append(
                    f"Contract {contract.id}: {', '.join(errors)}"
                )

        if invalid_contracts:
            raise ValueError(
                f"Dataset validation failed:\n" + "\n".join(invalid_contracts)
            )

        return True
