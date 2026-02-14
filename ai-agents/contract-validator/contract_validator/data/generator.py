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

    # Supervisors at companies — appear as noise alongside the student
    SUPERVISORS = [
        ("Dr. Andreas Berger", "Abteilungsleiter", "+49 89 123456-10"),
        ("Sabine Kremer", "HR-Beauftragte", "+49 30 987654-22"),
        ("Thomas Reinhardt", "Betreuender Ingenieur", "+49 40 112233-44"),
        ("Prof. Dr. Claudia Wirth", "Projektleiterin", "+49 69 445566-99"),
        ("Michael Hoffbauer", "Personalreferent", "+49 711 778899-01"),
    ]

    # Degree programmes — noise field in form_style
    DEGREE_PROGRAMMES = [
        "Informatik (B.Sc.)",
        "Wirtschaftsinformatik (B.Sc.)",
        "Maschinenbau (B.Eng.)",
        "Elektrotechnik (B.Eng.)",
        "Medieninformatik (B.Sc.)",
        "Betriebswirtschaftslehre (B.A.)",
    ]

    # Departments — noise field in tabular
    DEPARTMENTS = [
        "Entwicklung / R&D",
        "IT-Infrastruktur",
        "Produktmanagement",
        "Qualitaetssicherung",
        "Finanzwesen / Controlling",
        "Vertrieb & Marketing",
    ]

    # German month names for prose dates
    GERMAN_MONTHS = [
        "Januar", "Februar", "Maerz", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember"
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
        metadata: Dict[str, Any] = {
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

    # ------------------------------------------------------------------ #
    #  Distractor / helper generators                                      #
    # ------------------------------------------------------------------ #

    def _generate_contract_ref(self) -> str:
        """Generate a contract reference number (looks numeric but is NOT the Matrikelnummer)."""
        year = random.randint(2024, 2026)
        num = random.randint(10000, 99999)
        return f"PV-{year}-{num}"

    def _generate_phone(self) -> str:
        """Generate a plausible German phone number."""
        area = random.choice(["089", "030", "040", "069", "0711", "0221"])
        main = random.randint(100000, 999999)
        ext = random.randint(10, 99)
        return f"+49 {area.lstrip('0')} {main}-{ext}"

    def _generate_iban(self) -> str:
        """Generate a fake but plausible-looking German IBAN."""
        bank = random.choice(["3704 0044", "2004 1010", "7001 0080", "5001 0517"])
        account = random.randint(1000000000, 9999999999)
        check = random.randint(10, 99)
        return f"DE{check} {bank} {str(account)[:4]} {str(account)[4:8]} {str(account)[8:10]}"

    def _format_date_prose(self, d: date) -> str:
        """Format a date as German prose: '1. Maerz 2026' (no leading zero)."""
        return f"{d.day}. {self.GERMAN_MONTHS[d.month - 1]} {d.year}"

    def _pick_supervisor(self) -> tuple:
        """Return a (name, title, phone) supervisor tuple."""
        return random.choice(self.SUPERVISORS)

    def _generate_letterhead(self, company_name: str, company_address: str, phone: str) -> str:
        """Generate a company letterhead block."""
        city = company_address.split(",")[-1].strip() if "," in company_address else "Hamburg"
        # Use today as document date for realism
        doc_date = date(2026, 2, 14)
        return (
            f"{company_name}\n"
            f"{company_address}\n"
            f"Tel.: {phone}  |  www.{company_name.lower().replace(' ', '').replace('.', '')}.de\n"
            f"\n"
            f"{city}, den {self._format_date_prose(doc_date)}\n"
        )

    def _generate_boilerplate_clauses(
        self,
        company_name: str,
        supervisor_name: str,
        start_prose: str,
        end_prose: str,
        monthly_pay: int,
        iban: str,
    ) -> str:
        """Generate 5 legal §-clauses as a multi-paragraph block."""
        return (
            f"\n§1 Gegenstand des Vertrages\n"
            f"Die {company_name} (nachfolgend 'Unternehmen') bietet dem Praktikanten/der "
            f"Praktikantin die Moeglichkeit, ein Pflichtpraktikum gemaess der Studienordnung "
            f"der Hochschule fuer Angewandte Wissenschaften Hamburg (HAW Hamburg) zu absolvieren. "
            f"Der Einsatz erfolgt in Absprache mit {supervisor_name}.\n"
            f"\n§2 Pflichten des Praktikanten/der Praktikantin\n"
            f"Die/Der Praktikant/in verpflichtet sich, die uebertragenen Aufgaben sorgfaeltig "
            f"und gewissenhaft auszufuehren, die betrieblichen Ordnungen einzuhalten sowie "
            f"am Ende des Praktikums einen Praktikumsbericht einzureichen.\n"
            f"\n§3 Arbeitszeit und Dauer\n"
            f"Die regelmaessige woechentliche Arbeitszeit betraegt 40 Stunden. "
            f"Das Praktikum laeuft vom {start_prose} bis zum {end_prose}. "
            f"Urlaubs- und Feiertagsregelungen folgen den betrieblichen Bestimmungen.\n"
            f"\n§4 Verguetung\n"
            f"Der Praktikant/die Praktikantin erhaelt eine monatliche Verguetung von "
            f"{monthly_pay},00 EUR brutto. Die Auszahlung erfolgt per Bankueberweisung auf "
            f"das vom Praktikanten angegebene Konto (IBAN: {iban}).\n"
            f"\n§5 Vertraulichkeit\n"
            f"Der Praktikant/die Praktikantin verpflichtet sich, alle im Rahmen des "
            f"Praktikums erlangten vertraulichen Informationen der {company_name} "
            f"gegenueber Dritten nicht preiszugeben. Diese Verpflichtung gilt auch nach "
            f"Beendigung des Praktikumsverhaeltnisses.\n"
        )

    def _generate_signature_block(self, student_name: str, supervisor_name: str) -> str:
        """Generate a signature block for the contract."""
        return (
            f"\nDieser Vertrag wurde in zwei gleichlautenden Ausfertigungen erstellt "
            f"und von beiden Parteien unterzeichnet.\n"
            f"\n"
            f"________________________    ________________________\n"
            f"(Unternehmen)               (Praktikant/in)\n"
            f"{supervisor_name:<28}{student_name}\n"
        )

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
                start_date, end_date, start_str, end_str, fields_to_omit
            )
        elif contract_format == ContractFormat.TABULAR:
            return self._generate_tabular_text(
                student_name, matrikelnummer, company_name, company_address,
                start_date, end_date, start_str, end_str, fields_to_omit
            )
        elif contract_format == ContractFormat.FORM_STYLE:
            return self._generate_form_text(
                student_name, matrikelnummer, company_name, company_address,
                start_date, end_date, start_str, end_str, fields_to_omit
            )
        else:  # FLOWING_TEXT
            return self._generate_flowing_text(
                student_name, matrikelnummer, company_name, company_address,
                start_date, end_date, start_str, end_str, fields_to_omit
            )

    def _generate_structured_text(
        self,
        student_name: str,
        matrikelnummer: str,
        company_name: str,
        company_address: str,
        start_date: date,
        end_date: date,
        start_str: str,
        end_str: str,
        fields_to_omit: List[str],
    ) -> str:
        """Generate structured format contract text with letterhead, boilerplate, and signature."""
        supervisor_name, supervisor_title, supervisor_phone = self._pick_supervisor()
        contract_ref = self._generate_contract_ref()
        iban = self._generate_iban()
        monthly_pay = random.randint(4, 8) * 100
        start_prose = self._format_date_prose(start_date)
        end_prose = self._format_date_prose(end_date)

        lines = [
            self._generate_letterhead(company_name, company_address, supervisor_phone),
            "=" * 60,
            "PRAKTIKUMSVERTRAG",
            f"Vertragsnummer: {contract_ref}",
            "=" * 60,
            "",
            "VERTRAGSPARTEIEN",
            "-" * 40,
            f"Student:          {student_name}",
        ]

        if "matrikelnummer" not in fields_to_omit:
            lines.append(f"Matrikelnummer:   {matrikelnummer}")

        lines.append(f"Firma:            {company_name}")

        if "company_address" not in fields_to_omit:
            lines.append(f"Adresse:          {company_address}")

        if "start_date" not in fields_to_omit:
            lines.append(f"Beginn:           {start_str}")

        if "end_date" not in fields_to_omit:
            lines.append(f"Ende:             {end_str}")

        lines.append(f"Betreuer:         {supervisor_name} ({supervisor_title})")
        lines.append(f"Kontakt:          {supervisor_phone}")
        lines.append("")

        lines.append(
            self._generate_boilerplate_clauses(
                company_name, supervisor_name, start_prose, end_prose, monthly_pay, iban
            )
        )

        lines.append(self._generate_signature_block(student_name, supervisor_name))

        return "\n".join(lines)

    def _generate_tabular_text(
        self,
        student_name: str,
        matrikelnummer: str,
        company_name: str,
        company_address: str,
        start_date: date,
        end_date: date,
        start_str: str,
        end_str: str,
        fields_to_omit: List[str],
    ) -> str:
        """Generate tabular format contract text with letterhead, prose dates, and boilerplate."""
        supervisor_name, supervisor_title, supervisor_phone = self._pick_supervisor()
        contract_ref = self._generate_contract_ref()
        iban = self._generate_iban()
        monthly_pay = random.randint(4, 8) * 100
        department = random.choice(self.DEPARTMENTS)
        start_prose = self._format_date_prose(start_date)
        end_prose = self._format_date_prose(end_date)

        lines = [
            self._generate_letterhead(company_name, company_address, supervisor_phone),
            "# PRAKTIKUMSVERTRAG",
            "",
            f"**Vertragsnummer:** {contract_ref}",
            "",
            "## Vertragsparteien",
            "",
            "| Feld                | Wert                                          |",
            "|---------------------|-----------------------------------------------|",
            f"| Name                | {student_name:<45} |",
        ]

        if "matrikelnummer" not in fields_to_omit:
            lines.append(f"| Matrikel-Nr.        | {matrikelnummer:<45} |")

        lines.append(f"| Unternehmen         | {company_name:<45} |")

        if "company_address" not in fields_to_omit:
            addr = company_address[:45] if len(company_address) > 45 else company_address
            lines.append(f"| Adresse             | {addr:<45} |")

        if "start_date" not in fields_to_omit:
            lines.append(f"| Praktikumsbeginn    | {start_str:<45} |")

        if "end_date" not in fields_to_omit:
            lines.append(f"| Praktikumsende      | {end_str:<45} |")

        lines.append(f"| Betreuer/in         | {supervisor_name} ({supervisor_title})".ljust(66) + "|")
        lines.append(f"| Abteilung           | {department:<45} |")
        lines.append(f"| Kontakt Betreuer    | {supervisor_phone:<45} |")
        lines.append("")
        lines.append("## Vertragsdauer")
        lines.append("")

        if "start_date" not in fields_to_omit and "end_date" not in fields_to_omit:
            lines.append(
                f"Das Praktikum beginnt am {start_prose} und endet am {end_prose}. "
                f"Die Gesamtdauer ergibt sich aus den oben genannten Vertragsdaten."
            )
        elif "start_date" not in fields_to_omit:
            lines.append(f"Das Praktikum beginnt am {start_prose}. Das Enddatum ist noch festzulegen.")
        elif "end_date" not in fields_to_omit:
            lines.append(f"Das Praktikum endet spaetestens am {end_prose}.")

        lines.append("")
        lines.append(
            self._generate_boilerplate_clauses(
                company_name, supervisor_name, start_prose, end_prose, monthly_pay, iban
            )
        )
        lines.append(self._generate_signature_block(student_name, supervisor_name))

        return "\n".join(lines)

    def _generate_form_text(
        self,
        student_name: str,
        matrikelnummer: str,
        company_name: str,
        company_address: str,
        start_date: date,
        end_date: date,
        start_str: str,
        end_str: str,
        fields_to_omit: List[str],
    ) -> str:
        """Generate form-style contract with letterhead, distractors, and boilerplate."""
        supervisor_name, supervisor_title, supervisor_phone = self._pick_supervisor()
        contract_ref = self._generate_contract_ref()
        iban = self._generate_iban()
        monthly_pay = random.randint(4, 8) * 100
        degree = random.choice(self.DEGREE_PROGRAMMES)
        start_prose = self._format_date_prose(start_date)
        end_prose = self._format_date_prose(end_date)

        lines = [
            self._generate_letterhead(company_name, company_address, supervisor_phone),
            "PRAKTIKUMSVERTRAG - ANTRAGSFORMULAR",
            f"Vertragsnummer: ____{contract_ref}____",
            "",
            "ANGABEN ZUM PRAKTIKANTEN / ZUR PRAKTIKANTIN",
            "-" * 50,
            f"Name des Praktikanten:        __{student_name}{'_' * max(0, 30 - len(student_name))}",
        ]

        if "matrikelnummer" not in fields_to_omit:
            lines.append(f"Matrikelnummer:               ____{matrikelnummer}____________________")

        lines.append(f"Studiengang:                  __{degree}{'_' * max(0, 28 - len(degree))}")
        lines.append("")
        lines.append("ANGABEN ZUM UNTERNEHMEN")
        lines.append("-" * 50)
        lines.append(f"Praktikumsbetrieb:            __{company_name}{'_' * max(0, 28 - len(company_name))}")

        if "company_address" not in fields_to_omit:
            lines.append(f"Adresse:                      __{company_address}__")

        lines.append(f"Telefon Unternehmen:          __{supervisor_phone}__")
        lines.append(f"Betreuer/in im Unternehmen:   __{supervisor_name} ({supervisor_title})__")
        lines.append("")
        lines.append("PRAKTIKUMSZEITRAUM")
        lines.append("-" * 50)

        if "start_date" not in fields_to_omit and "end_date" not in fields_to_omit:
            lines.append(f"von: __{start_str}__  bis: __{end_str}__")
            lines.append(f"(entspricht dem Zeitraum vom {start_prose} bis {end_prose})")
        elif "start_date" not in fields_to_omit:
            lines.append(f"von: __{start_str}__  bis: ______________")
            lines.append(f"(Beginn: {start_prose})")
        elif "end_date" not in fields_to_omit:
            lines.append(f"von: ______________  bis: __{end_str}__")
            lines.append(f"(Ende: {end_prose})")
        else:
            lines.append("von: ______________  bis: ______________")

        lines.append("")
        lines.append(
            self._generate_boilerplate_clauses(
                company_name, supervisor_name, start_prose, end_prose, monthly_pay, iban
            )
        )
        lines.append(self._generate_signature_block(student_name, supervisor_name))

        return "\n".join(lines)

    def _generate_flowing_text(
        self,
        student_name: str,
        matrikelnummer: str,
        company_name: str,
        company_address: str,
        start_date: date,
        end_date: date,
        start_str: str,
        end_str: str,
        fields_to_omit: List[str],
    ) -> str:
        """Generate multi-paragraph flowing prose contract with all distractor elements."""
        supervisor_name, supervisor_title, supervisor_phone = self._pick_supervisor()
        contract_ref = self._generate_contract_ref()
        iban = self._generate_iban()
        monthly_pay = random.randint(4, 8) * 100
        start_prose = self._format_date_prose(start_date)
        end_prose = self._format_date_prose(end_date)

        # Determine gender based on typical German first name endings
        first_name = student_name.split()[0]
        if first_name.endswith(("a", "e", "i")) and first_name not in [
            "Max", "Niklas", "Lukas", "Tim", "Moritz"
        ]:
            title = "Frau"
            pronoun = "ihre"
        else:
            title = "Herr"
            pronoun = "seine"

        city = company_address.split(",")[-1].strip() if "," in company_address else "Hamburg"

        paragraphs = [self._generate_letterhead(company_name, company_address, supervisor_phone)]
        paragraphs.append("PRAKTIKUMSVERTRAG\n")

        # Preamble — both parties named, supervisor as company rep (noise)
        preamble = (
            f"Zwischen der {company_name} (nachfolgend 'Unternehmen'), vertreten durch "
            f"{supervisor_name}, {supervisor_title}, Telefon: {supervisor_phone},"
        )
        if "company_address" not in fields_to_omit:
            preamble += f" mit Sitz in {city},"
        preamble += (
            f" und {title} {student_name}"
        )
        if "matrikelnummer" not in fields_to_omit:
            preamble += f", Matrikelnummer {matrikelnummer},"
        preamble += (
            " Studierender der Hochschule fuer Angewandte Wissenschaften Hamburg (HAW Hamburg),"
            " wird folgender Praktikumsvertrag geschlossen:"
        )
        paragraphs.append(preamble)

        # Duration paragraph — prose dates + numeric dates as noise
        duration_parts = []
        if "start_date" not in fields_to_omit and "end_date" not in fields_to_omit:
            duration_parts.append(
                f"Das Pflichtpraktikum beginnt am {start_prose} ({start_str}) "
                f"und endet am {end_prose} ({end_str}). "
                f"Die Vertragsnummer lautet: {contract_ref}."
            )
        elif "start_date" not in fields_to_omit:
            duration_parts.append(
                f"Das Pflichtpraktikum beginnt am {start_prose} ({start_str}). "
                f"Das Enddatum wird gesondert schriftlich vereinbart. "
                f"Vertragsnummer: {contract_ref}."
            )
        elif "end_date" not in fields_to_omit:
            duration_parts.append(
                f"Das Pflichtpraktikum endet am {end_prose} ({end_str}). "
                f"Vertragsnummer: {contract_ref}."
            )
        else:
            duration_parts.append(
                f"Die Dauer des Pflichtpraktikums wird separat festgelegt. "
                f"Vertragsnummer: {contract_ref}."
            )

        if duration_parts:
            paragraphs.append(" ".join(duration_parts))

        paragraphs.append(
            self._generate_boilerplate_clauses(
                company_name, supervisor_name, start_prose, end_prose, monthly_pay, iban
            )
        )
        paragraphs.append(
            f"Dieser Vertrag wurde in zwei gleichlautenden Ausfertigungen erstellt "
            f"und von beiden Parteien unterzeichnet.\n"
            f"{city}, den {self._format_date_prose(date(2026, 2, 14))}\n"
            f"\n"
            f"____________________    ____________________\n"
            f"(Unternehmen)           (Praktikant/in)\n"
            f"{supervisor_name:<24}{student_name}\n"
        )

        return "\n\n".join(paragraphs)

    def _generate_metadata(
        self,
        contract_format: ContractFormat,
        status: ValidationStatus,
        working_days: int,
    ) -> Dict[str, Any]:
        """Generate contract metadata."""
        # Determine difficulty — all formats now have boilerplate + distractors
        if status == ValidationStatus.MISSING_DATA:
            difficulty = "hard"
        elif contract_format == ContractFormat.FLOWING_TEXT:
            # Dates buried in prose, multiple number distractors, supervisor noise
            difficulty = "hard"
        elif status == ValidationStatus.VALID and working_days >= 95 and working_days <= 97:
            difficulty = "edge_case"
        elif contract_format in (ContractFormat.STRUCTURED, ContractFormat.TABULAR):
            # Key fields still labeled but surrounded by legal noise and distractors
            difficulty = "medium"
        else:
            # form_style: labeled but with phone numbers, IBAN, extra fields
            difficulty = "medium"

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
        def _contract_to_dict(c: Contract) -> Dict[str, Any]:
            d: Dict[str, Any] = {
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
            return d

        data = {
            "metadata": dataset.metadata,
            "contracts": [_contract_to_dict(c) for c in dataset.contracts],
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
