"""
Validation logic for contract extraction and business rules.
"""

from datetime import datetime
from typing import Dict, List, Optional, Set

from contract_validator.core.working_days import calculate_working_days
from contract_validator.data.schemas import (
    Contract,
    ExtractedData,
    ExtractionMetrics,
    ExtractionResult,
    GroundTruth,
    ValidationReport,
    ValidationResult,
    ValidationStatus,
)


class ExtractionValidator:
    """Validates extraction results and calculates accuracy metrics."""

    def calculate_metrics(self, results: List[ExtractionResult]) -> ExtractionMetrics:
        """
        Calculate extraction metrics from results.

        Args:
            results: List of extraction results

        Returns:
            ExtractionMetrics with accuracy scores
        """
        if not results:
            return ExtractionMetrics(
                total_contracts=0,
                student_name_accuracy=0.0,
                matrikelnummer_accuracy=0.0,
                company_name_accuracy=0.0,
                start_date_accuracy=0.0,
                end_date_accuracy=0.0,
                overall_accuracy=0.0,
                per_format_accuracy={},
            )

        total = len(results)

        # Calculate per-field accuracy
        student_name_correct = sum(1 for r in results if r.student_name_correct)
        matrikelnummer_correct = sum(1 for r in results if r.matrikelnummer_correct)
        company_name_correct = sum(1 for r in results if r.company_name_correct)
        start_date_correct = sum(1 for r in results if r.start_date_correct)
        end_date_correct = sum(1 for r in results if r.end_date_correct)
        all_correct = sum(1 for r in results if r.all_correct)

        # Calculate per-format accuracy
        per_format_accuracy = self._calculate_per_format_accuracy(results)

        return ExtractionMetrics(
            total_contracts=total,
            student_name_accuracy=student_name_correct / total,
            matrikelnummer_accuracy=matrikelnummer_correct / total,
            company_name_accuracy=company_name_correct / total,
            start_date_accuracy=start_date_correct / total,
            end_date_accuracy=end_date_correct / total,
            overall_accuracy=all_correct / total,
            per_format_accuracy=per_format_accuracy,
        )

    def _calculate_per_format_accuracy(
        self, results: List[ExtractionResult]
    ) -> Dict[str, float]:
        """Calculate accuracy grouped by contract format, including ocr_scanned."""
        format_results: Dict[str, List[ExtractionResult]] = {}

        for result in results:
            key = result.contract_format.value
            format_results.setdefault(key, []).append(result)

        return {
            fmt: sum(1 for r in res if r.all_correct) / len(res)
            for fmt, res in format_results.items()
            if res
        }

    def validate_results(
        self,
        results: List[ExtractionResult],
        contracts: List[Contract],
        prompt_name: str = "",
    ) -> ValidationReport:
        """
        Calculate metrics and build a ValidationReport from extraction results.

        This is the single entry point called by the CLI's test command.
        """
        metrics = self.calculate_metrics(results)

        # Build a ValidationReport (business-rule validation lives in ValidationValidator)
        return create_validation_report(
            extraction_results=results,
            validation_results=[],   # business-rule validation not wired in test command
            extraction_metrics=metrics,
            prompt_name=prompt_name,
        )


class ValidationValidator:
    """Validates contracts against business rules."""

    def __init__(
        self,
        min_working_days: int = 95,
        blacklist: Optional[Set[str]] = None,
    ):
        """
        Initialize validation validator.

        Args:
            min_working_days: Minimum required working days
            blacklist: Set of blacklisted company names
        """
        self.min_working_days = min_working_days
        self.blacklist = blacklist or set()

    def validate_contract(
        self,
        extracted: ExtractedData,
        expected: GroundTruth,
    ) -> ValidationResult:
        """
        Validate a single contract against business rules.

        Args:
            extracted: Extracted data from LLM
            expected: Ground truth data for comparison

        Returns:
            ValidationResult with validation status and issues
        """
        issues: List[str] = []
        calculated_working_days: Optional[int] = None

        # Check for missing data
        missing_fields = []
        if not extracted.student_name:
            missing_fields.append("student_name")
        if not extracted.matrikelnummer:
            missing_fields.append("matrikelnummer")
        if not extracted.company_name:
            missing_fields.append("company_name")
        if not extracted.start_date:
            missing_fields.append("start_date")
        if not extracted.end_date:
            missing_fields.append("end_date")

        if missing_fields:
            issues.append(f"Missing required fields: {', '.join(missing_fields)}")
            status = ValidationStatus.MISSING_DATA
        elif self._is_blacklisted(extracted.company_name):
            issues.append(f"Company '{extracted.company_name}' is blacklisted")
            status = ValidationStatus.BLACKLISTED_COMPANY
        else:
            # Calculate working days
            calculated_working_days = calculate_working_days(
                extracted.start_date, extracted.end_date
            )

            if calculated_working_days < self.min_working_days:
                issues.append(
                    f"Duration too short: {calculated_working_days} working days "
                    f"(minimum: {self.min_working_days})"
                )
                status = ValidationStatus.INVALID_DURATION
            else:
                status = ValidationStatus.VALID

        # Check if validation matches expected
        is_correct = status == expected.expected_status

        return ValidationResult(
            contract_id="",  # Will be set by caller
            extracted=extracted,
            calculated_working_days=calculated_working_days,
            status=status,
            expected_status=expected.expected_status,
            is_correct=is_correct,
            issues=issues,
        )

    def _is_blacklisted(self, company_name: Optional[str]) -> bool:
        """Check if a company is on the blacklist."""
        if not company_name:
            return False

        # Normalize for comparison
        normalized = company_name.lower().strip()

        for blacklisted in self.blacklist:
            if blacklisted.lower().strip() == normalized:
                return True

        return False

    def validate_batch(
        self,
        results: List[ExtractionResult],
    ) -> List[ValidationResult]:
        """
        Validate a batch of extraction results.

        Args:
            results: List of extraction results

        Returns:
            List of ValidationResult objects
        """
        validation_results = []

        for result in results:
            validation = self.validate_contract(result.extracted, result.expected)
            validation.contract_id = result.contract_id
            validation_results.append(validation)

        return validation_results

    def calculate_validation_accuracy(
        self, validation_results: List[ValidationResult]
    ) -> float:
        """
        Calculate validation status accuracy.

        Args:
            validation_results: List of validation results

        Returns:
            Accuracy score (0.0 to 1.0)
        """
        if not validation_results:
            return 0.0

        correct = sum(1 for r in validation_results if r.is_correct)
        return correct / len(validation_results)

    def calculate_per_status_accuracy(
        self, validation_results: List[ValidationResult]
    ) -> Dict[str, float]:
        """
        Calculate accuracy per validation status.

        Args:
            validation_results: List of validation results

        Returns:
            Dictionary mapping status to accuracy
        """
        status_results: Dict[ValidationStatus, List[ValidationResult]] = {}

        for result in validation_results:
            if result.expected_status not in status_results:
                status_results[result.expected_status] = []
            status_results[result.expected_status].append(result)

        per_status = {}
        for status, results in status_results.items():
            if results:
                correct = sum(1 for r in results if r.is_correct)
                per_status[status.value] = correct / len(results)

        return per_status


def create_validation_report(
    extraction_results: List[ExtractionResult],
    validation_results: List[ValidationResult],
    extraction_metrics: ExtractionMetrics,
    prompt_name: str,
) -> ValidationReport:
    """
    Create a complete validation report.

    Args:
        extraction_results: List of extraction results
        validation_results: List of validation results
        extraction_metrics: Calculated extraction metrics
        prompt_name: Name of the prompt used

    Returns:
        ValidationReport with all metrics and results
    """
    # Calculate validation accuracy
    validation_correct = sum(1 for r in validation_results if r.is_correct)
    validation_accuracy = (
        validation_correct / len(validation_results) if validation_results else 0.0
    )

    # Calculate per-status accuracy
    status_results: Dict[str, List[ValidationResult]] = {}
    for result in validation_results:
        status_key = result.expected_status.value
        if status_key not in status_results:
            status_results[status_key] = []
        status_results[status_key].append(result)

    per_status_accuracy = {}
    for status, results in status_results.items():
        if results:
            correct = sum(1 for r in results if r.is_correct)
            per_status_accuracy[status] = correct / len(results)

    return ValidationReport(
        total_contracts=len(extraction_results),
        extraction_metrics=extraction_metrics,
        validation_accuracy=validation_accuracy,
        per_status_accuracy=per_status_accuracy,
        results=extraction_results,
        validation_results=validation_results,
        prompt_name=prompt_name,
        test_timestamp=datetime.now(),
    )
