"""
Contract generator for creating test datasets with realistic German contracts.
"""

import json
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from contract_validator.data.schemas import (
    Contract,
    ContractDataset,
    ContractFormat,
    GroundTruth,
    ValidationStatus,
)


class ContractGenerator:
    """Generates realistic German internship contracts for testing."""

    # German first names
    FIRST_NAMES = [
        "Max", "Anna", "Jonas", "Lisa", "Lukas", "Laura", "Felix", "Sophie",
        "Tim", "Julia", "Leon", "Marie", "Paul", "Sarah", "David", "Emma",
        "Niklas", "Hannah", "Erik", "Lena", "Moritz", "Mia", "Jan", "Clara",
        "Tobias", "Lea", "Simon", "Nina", "Philipp", "Katharina"
    ]

    # German last names
    LAST_NAMES = [
        "Mueller", "Schmidt", "Schneider", "Fischer", "Weber", "Meyer", "Wagner",
        "Becker", "Schulz", "Hoffmann", "Koch", "Bauer", "Richter", "Klein",
        "Wolf", "Schroeder", "Neumann", "Schwarz", "Zimmermann", "Braun",
        "Krueger", "Hofmann", "Lange", "Schmitt", "Werner", "Hartmann",
        "Krause", "Lehmann", "Schmitz", "Maier"
    ]

    # Whitelisted companies with addresses
    WHITELIST_COMPANIES = [
        ("Siemens AG", "Werner-von-Siemens-Str. 1, 80333 Muenchen"),
        ("BMW Group", "Petuelring 130, 80809 Muenchen"),
        ("Airbus SE", "Airbus-Allee 1, 28199 Bremen"),
        ("Deutsche Bank AG", "Taunusanlage 12, 60325 Frankfurt am Main"),
        ("SAP SE", "Dietmar-Hopp-Allee 16, 69190 Walldorf"),
        ("Bosch GmbH", "Robert-Bosch-Platz 1, 70839 Gerlingen"),
        ("Volkswagen AG", "Berliner Ring 2, 38440 Wolfsburg"),
        ("Mercedes-Benz AG", "Mercedesstr. 120, 70372 Stuttgart"),
        ("BASF SE", "Carl-Bosch-Str. 38, 67056 Ludwigshafen"),
        ("Allianz SE", "Koeniginstr. 28, 80802 Muenchen"),
    ]

    # Blacklisted companies
    BLACKLIST_COMPANIES = [
        ("Fake Company GmbH", "Fake Str. 1, 12345 Nowhere"),
        ("Scam Industries Ltd", "Scam Road 99, 54321 Scamtown"),
        ("Nicht Existiert AG", "Fantasieweg 0, 00000 Nirgendwo"),
    ]

    def __init__(self, seed: Optional[int] = None):
        """
        Initialize the contract generator.

        Args:
            seed: Optional random seed for reproducibility
        """
        if seed is not None:
            random.seed(seed)
        self.seed = seed

    def generate_dataset(
        self,
        num_contracts: int = 50,
        format_distribution: Optional[Dict[ContractFormat, int]] = None,
        status_distribution: Optional[Dict[ValidationStatus, int]] = None,
    ) -> ContractDataset:
        """
        Generate a complete contract dataset.

        Args:
            num_contracts: Total number of contracts to generate
            format_distribution: Optional distribution of formats.
                                 Defaults to: 15 structured, 12 tabular, 13 form_style, 10 flowing_text
            status_distribution: Optional distribution of statuses.
                                 Defaults to: 30 valid, 10 invalid_duration, 5 blacklisted, 5 missing_data

        Returns:
            ContractDataset with generated contracts
        """
        # Default distributions
        if format_distribution is None:
            format_distribution = {
                ContractFormat.STRUCTURED: 15,
                ContractFormat.TABULAR: 12,
                ContractFormat.FORM_STYLE: 13,
                ContractFormat.FLOWING_TEXT: 10,
            }

        if status_distribution is None:
            status_distribution = {
                ValidationStatus.VALID: 30,
                ValidationStatus.INVALID_DURATION: 10,
                ValidationStatus.BLACKLISTED_COMPANY: 5,
                ValidationStatus.MISSING_DATA: 5,
            }

        # Create format and status lists
        formats = []
        for fmt, count in format_distribution.items():
            formats.extend([fmt] * count)

        statuses = []
        for status, count in status_distribution.items():
            statuses.extend([status] * count)

        # Shuffle to randomize
        random.shuffle(formats)
        random.shuffle(statuses)

        # Generate contracts
        contracts = []
        for i in range(num_contracts):
            contract_format = formats[i] if i < len(formats) else random.choice(list(ContractFormat))
            status = statuses[i] if i < len(statuses) else random.choice(list(ValidationStatus))

            contract = self._generate_contract(
                contract_id=f"contract_{i+1:03d}",
                contract_format=contract_format,
                status=status,
            )
            contracts.append(contract)

        # Create dataset metadata
        metadata = {
            "version": "1.0",
            "total_contracts": num_contracts,
            "seed": self.seed,
            "format_distribution": {k.value: v for k, v in format_distribution.items()},
            "status_distribution": {k.value: v for k, v in status_distribution.items()},
        }

        return ContractDataset(metadata=metadata, contracts=contracts)

    def _generate_contract(
        self,
        contract_id: str,
        contract_format: ContractFormat,
        status: ValidationStatus,
    ) -> Contract:
        """
        Generate a single contract.

        Args:
            contract_id: Unique identifier for the contract
            contract_format: Format of the contract text
            status: Expected validation status

        Returns:
            Contract object
        """
        # Generate basic data
        student_name = self._generate_name()
        matrikelnummer = self._generate_matrikelnummer()
        company_name, company_address = self._select_company(status)
        start_date, end_date, working_days = self._generate_dates(status)

        # Create ground truth
        ground_truth = GroundTruth(
            student_name=student_name,
            matrikelnummer=matrikelnummer,
            company_name=company_name,
            company_address=company_address,
            start_date=start_date,
            end_date=end_date,
            working_days=working_days,
            expected_status=status,
        )

        # Generate contract text
        text = self._generate_contract_text(
            contract_format=contract_format,
            student_name=student_name,
            matrikelnummer=matrikelnummer,
            company_name=company_name,
            company_address=company_address,
            start_date=start_date,
            end_date=end_date,
            status=status,
        )

        # Create metadata
        metadata = self._generate_metadata(contract_format, status, working_days)

        return Contract(
            id=contract_id,
            text=text,
            format=contract_format,
            ground_truth=ground_truth,
            metadata=metadata,
        )

    def _generate_name(self) -> str:
        """Generate a random German name."""
        first_name = random.choice(self.FIRST_NAMES)
        last_name = random.choice(self.LAST_NAMES)
        return f"{first_name} {last_name}"

    def _generate_matrikelnummer(self) -> str:
        """Generate a 7-digit Matrikelnummer."""
        return str(random.randint(2000000, 2999999))

    def _select_company(self, status: ValidationStatus) -> Tuple[str, str]:
        """Select a company based on validation status."""
        if status == ValidationStatus.BLACKLISTED_COMPANY:
            return random.choice(self.BLACKLIST_COMPANIES)
        else:
            return random.choice(self.WHITELIST_COMPANIES)

    def _generate_dates(self, status: ValidationStatus) -> Tuple[date, date, int]:
        """
        Generate start and end dates based on validation status.

        Returns:
            Tuple of (start_date, end_date, working_days)
        """
        # Base year range: 2024-2026
        year = random.choice([2024, 2025, 2026])
        month = random.randint(1, 12)
        day = random.randint(1, 28)  # Safe day range

        start_date = date(year, month, day)

        if status == ValidationStatus.INVALID_DURATION:
            # Generate short duration (30-60 days, resulting in ~20-40 working days)
            duration_days = random.randint(30, 60)
        elif status == ValidationStatus.VALID:
            # Generate valid duration (at least 95 working days, ~135+ calendar days)
            # Some edge cases with exactly 95 working days
            if random.random() < 0.15:  # 15% chance of edge case
                duration_days = 133  # Approximately 95 working days
            else:
                duration_days = random.randint(140, 200)
        else:
            # For blacklisted or missing_data, duration doesn't matter much
            duration_days = random.randint(140, 180)

        end_date = start_date + timedelta(days=duration_days)

        # Calculate actual working days
        working_days = self._calculate_working_days(start_date, end_date)

        return start_date, end_date, working_days

    def _calculate_working_days(self, start: date, end: date) -> int:
        """Calculate working days (Mon-Fri) between two dates."""
        days = 0
        current = start
        while current <= end:
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                days += 1
            current += timedelta(days=1)
        return days

    def _generate_contract_text(
        self,
        contract_format: ContractFormat,
        student_name: str,
        matrikelnummer: str,
        company_name: str,
        company_address: str,
        start_date: date,
        end_date: date,
        status: ValidationStatus,
    ) -> str:
        """Generate contract text in the specified format."""
        # Format dates for display
        start_str = start_date.strftime("%d.%m.%Y")
        end_str = end_date.strftime("%d.%m.%Y")

        # For missing_data status, randomly omit some fields
        if status == ValidationStatus.MISSING_DATA:
            fields_to_omit = random.sample(
                ["matrikelnummer", "company_address", "start_date", "end_date"],
                k=random.randint(1, 2)
            )
        else:
            fields_to_omit = []

        # Generate text based on format
        if contract_format == ContractFormat.STRUCTURED:
            return self._generate_structured_text(
                student_name, matrikelnummer, company_name, company_address,
                start_str, end_str, fields_to_omit
            )
        elif contract_format == ContractFormat.TABULAR:
            return self._generate_tabular_text(
                student_name, matrikelnummer, company_name, company_address,
                start_str, end_str, fields_to_omit
            )
        elif contract_format == ContractFormat.FORM_STYLE:
            return self._generate_form_text(
                student_name, matrikelnummer, company_name, company_address,
                start_str, end_str, fields_to_omit
            )
        else:  # FLOWING_TEXT
            return self._generate_flowing_text(
                student_name, matrikelnummer, company_name, company_address,
                start_str, end_str, fields_to_omit
            )

    def _generate_structured_text(
        self,
        student_name: str,
        matrikelnummer: str,
        company_name: str,
        company_address: str,
        start_str: str,
        end_str: str,
        fields_to_omit: List[str],
    ) -> str:
        """Generate structured format contract text."""
        lines = ["PRAKTIKUMSVERTRAG", ""]
        lines.append(f"Student: {student_name}")

        if "matrikelnummer" not in fields_to_omit:
            lines.append(f"Matrikelnummer: {matrikelnummer}")

        lines.append(f"Firma: {company_name}")

        if "company_address" not in fields_to_omit:
            lines.append(f"Adresse: {company_address}")

        if "start_date" not in fields_to_omit:
            lines.append(f"Beginn: {start_str}")

        if "end_date" not in fields_to_omit:
            lines.append(f"Ende: {end_str}")

        return "\n".join(lines)

    def _generate_tabular_text(
        self,
        student_name: str,
        matrikelnummer: str,
        company_name: str,
        company_address: str,
        start_str: str,
        end_str: str,
        fields_to_omit: List[str],
    ) -> str:
        """Generate tabular format contract text."""
        lines = [
            "| Feld             | Wert                    |",
            "|------------------|-------------------------|",
            f"| Name             | {student_name:<23} |",
        ]

        if "matrikelnummer" not in fields_to_omit:
            lines.append(f"| Matrikel-Nr.     | {matrikelnummer:<23} |")

        lines.append(f"| Unternehmen      | {company_name:<23} |")

        if "company_address" not in fields_to_omit:
            # Truncate address if too long
            addr = company_address[:23] if len(company_address) > 23 else company_address
            lines.append(f"| Adresse          | {addr:<23} |")

        if "start_date" not in fields_to_omit:
            lines.append(f"| Praktikumsbeginn | {start_str:<23} |")

        if "end_date" not in fields_to_omit:
            lines.append(f"| Praktikumsende   | {end_str:<23} |")

        return "\n".join(lines)

    def _generate_form_text(
        self,
        student_name: str,
        matrikelnummer: str,
        company_name: str,
        company_address: str,
        start_str: str,
        end_str: str,
        fields_to_omit: List[str],
    ) -> str:
        """Generate form-style format contract text."""
        lines = [
            f"Name des Praktikanten: _{student_name}_{'_' * (30 - len(student_name))}",
        ]

        if "matrikelnummer" not in fields_to_omit:
            lines.append(f"Matrikelnummer: ____{matrikelnummer}____________________")

        lines.append(f"Praktikumsbetrieb: __{company_name}_{'_' * max(0, 25 - len(company_name))}")

        if "company_address" not in fields_to_omit:
            lines.append(f"Adresse: __{company_address}_")

        if "start_date" not in fields_to_omit and "end_date" not in fields_to_omit:
            lines.append(f"von: __{start_str}__ bis: __{end_str}__")
        elif "start_date" not in fields_to_omit:
            lines.append(f"von: __{start_str}__ bis: ______________")
        elif "end_date" not in fields_to_omit:
            lines.append(f"von: ______________ bis: __{end_str}__")

        return "\n".join(lines)

    def _generate_flowing_text(
        self,
        student_name: str,
        matrikelnummer: str,
        company_name: str,
        company_address: str,
        start_str: str,
        end_str: str,
        fields_to_omit: List[str],
    ) -> str:
        """Generate flowing text format contract text."""
        # Determine gender based on typical German first name endings
        first_name = student_name.split()[0]
        if first_name.endswith(("a", "e", "i")) and first_name not in ["Max", "Niklas", "Lukas", "Tim", "Moritz"]:
            title = "Frau"
        else:
            title = "Herr"

        # Build the text
        parts = [f"Hiermit wird bestaetigt, dass {title} {student_name}"]

        if "matrikelnummer" not in fields_to_omit:
            parts.append(f"(Matrikelnummer {matrikelnummer})")

        parts.append(f"sein Pflichtpraktikum bei der {company_name}")

        if "company_address" not in fields_to_omit:
            # Extract city from address
            city = company_address.split(",")[-1].strip() if "," in company_address else company_address
            parts.append(f"in {city}")

        if "start_date" not in fields_to_omit and "end_date" not in fields_to_omit:
            parts.append(f"vom {start_str} bis zum {end_str}")
        elif "start_date" not in fields_to_omit:
            parts.append(f"ab dem {start_str}")
        elif "end_date" not in fields_to_omit:
            parts.append(f"bis zum {end_str}")

        parts.append("absolvieren wird.")

        return " ".join(parts)

    def _generate_metadata(
        self,
        contract_format: ContractFormat,
        status: ValidationStatus,
        working_days: int,
    ) -> Dict[str, Any]:
        """Generate contract metadata."""
        # Determine difficulty
        if status == ValidationStatus.MISSING_DATA:
            difficulty = "hard"
        elif contract_format == ContractFormat.FLOWING_TEXT:
            difficulty = "medium"
        elif status == ValidationStatus.VALID and working_days >= 95 and working_days <= 97:
            difficulty = "edge_case"
        else:
            difficulty = "easy"

        return {
            "difficulty": difficulty,
            "format": contract_format.value,
            "status": status.value,
            "working_days": working_days,
        }

    def save_dataset(self, dataset: ContractDataset, output_path: str) -> str:
        """
        Save dataset to JSON file.

        Args:
            dataset: ContractDataset to save
            output_path: Path to output file

        Returns:
            Path to saved file
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict for JSON serialization
        data = {
            "metadata": dataset.metadata,
            "contracts": [
                {
                    "id": c.id,
                    "text": c.text,
                    "format": c.format.value,
                    "ground_truth": {
                        "student_name": c.ground_truth.student_name,
                        "matrikelnummer": c.ground_truth.matrikelnummer,
                        "company_name": c.ground_truth.company_name,
                        "company_address": c.ground_truth.company_address,
                        "start_date": c.ground_truth.start_date.isoformat(),
                        "end_date": c.ground_truth.end_date.isoformat(),
                        "working_days": c.ground_truth.working_days,
                        "expected_status": c.ground_truth.expected_status.value,
                    },
                    "metadata": c.metadata,
                }
                for c in dataset.contracts
            ],
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(path)

    def generate_batch(self, num_contracts: int = 50) -> List[Contract]:
        """
        Generate a batch of contracts.

        Args:
            num_contracts: Number of contracts to generate

        Returns:
            List of Contract objects
        """
        dataset = self.generate_dataset(num_contracts)
        return dataset.contracts

    def save_to_file(self, contracts: List[Contract], output_path: str) -> str:
        """
        Save contracts to JSON file.

        Args:
            contracts: List of Contract objects
            output_path: Path to output file

        Returns:
            Path to saved file
        """
        # Create dataset from contracts
        format_counts: Dict[str, int] = {}
        status_counts: Dict[str, int] = {}
        for c in contracts:
            fmt = c.format.value
            status = c.ground_truth.expected_status.value
            format_counts[fmt] = format_counts.get(fmt, 0) + 1
            status_counts[status] = status_counts.get(status, 0) + 1

        metadata = {
            "version": "1.0",
            "total_contracts": len(contracts),
            "seed": self.seed,
            "format_distribution": format_counts,
            "status_distribution": status_counts,
        }

        dataset = ContractDataset(metadata=metadata, contracts=contracts)
        return self.save_dataset(dataset, output_path)
