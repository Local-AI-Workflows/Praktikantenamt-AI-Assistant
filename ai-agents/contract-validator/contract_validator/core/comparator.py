"""
Side-by-side comparison of multiple prompts for contract extraction.
"""

from datetime import datetime
from typing import Dict, List, Optional, Set

from contract_validator.core.executor import ContractExecutor
from contract_validator.core.validator import ExtractionValidator, ValidationValidator
from contract_validator.data.schemas import (
    ComparisonReport,
    Contract,
    ExtractionResult,
    PromptConfig,
)


class Comparator:
    """Compares multiple prompts on the same contract dataset."""

    def __init__(
        self,
        executor: ContractExecutor,
        extraction_validator: ExtractionValidator,
        validation_validator: Optional[ValidationValidator] = None,
    ):
        """
        Initialize comparator.

        Args:
            executor: ContractExecutor instance
            extraction_validator: ExtractionValidator instance
            validation_validator: Optional ValidationValidator instance
        """
        self.executor = executor
        self.extraction_validator = extraction_validator
        self.validation_validator = validation_validator

    def compare_prompts(
        self,
        prompt_configs: List[PromptConfig],
        contracts: List[Contract],
    ) -> ComparisonReport:
        """
        Compare multiple prompts on the same dataset.

        Args:
            prompt_configs: List of PromptConfig objects to compare
            contracts: List of contracts to test on

        Returns:
            ComparisonReport with comparison results
        """
        if len(prompt_configs) < 2:
            raise ValueError("Need at least 2 prompts to compare")

        # Run each prompt on the dataset
        all_results: Dict[str, List[ExtractionResult]] = {}

        for prompt_config in prompt_configs:
            results = self.executor.execute_batch(contracts, prompt_config)
            all_results[prompt_config.name] = results

        # Calculate extraction accuracy for each prompt
        extraction_accuracy_comparison = {}
        for name, results in all_results.items():
            metrics = self.extraction_validator.calculate_metrics(results)
            extraction_accuracy_comparison[name] = metrics.overall_accuracy

        # Calculate validation accuracy if validator is available
        validation_accuracy_comparison = {}
        if self.validation_validator:
            for name, results in all_results.items():
                validation_results = self.validation_validator.validate_batch(results)
                validation_accuracy = self.validation_validator.calculate_validation_accuracy(
                    validation_results
                )
                validation_accuracy_comparison[name] = validation_accuracy

        # Calculate per-format accuracy for each prompt
        per_format_comparison = {}
        for name, results in all_results.items():
            metrics = self.extraction_validator.calculate_metrics(results)
            per_format_comparison[name] = metrics.per_format_accuracy

        # Determine winner (highest extraction accuracy)
        winner = max(extraction_accuracy_comparison.items(), key=lambda x: x[1])[0]

        return ComparisonReport(
            prompts_compared=[pc.name for pc in prompt_configs],
            extraction_accuracy_comparison=extraction_accuracy_comparison,
            validation_accuracy_comparison=validation_accuracy_comparison,
            per_format_comparison=per_format_comparison,
            winner=winner,
            test_timestamp=datetime.now(),
        )

    def get_extraction_disagreements(
        self,
        results_a: List[ExtractionResult],
        results_b: List[ExtractionResult],
    ) -> List[Dict]:
        """
        Identify cases where two prompts disagree on extraction.

        Args:
            results_a: Results from first prompt
            results_b: Results from second prompt

        Returns:
            List of disagreement dictionaries
        """
        disagreements = []

        if len(results_a) != len(results_b):
            raise ValueError("Result lists must have same length")

        for res_a, res_b in zip(results_a, results_b):
            if res_a.contract_id != res_b.contract_id:
                raise ValueError(
                    f"Contract ID mismatch: {res_a.contract_id} vs {res_b.contract_id}"
                )

            # Check for disagreements in extracted data
            disagreement_fields = []

            if res_a.extracted.student_name != res_b.extracted.student_name:
                disagreement_fields.append("student_name")
            if res_a.extracted.matrikelnummer != res_b.extracted.matrikelnummer:
                disagreement_fields.append("matrikelnummer")
            if res_a.extracted.company_name != res_b.extracted.company_name:
                disagreement_fields.append("company_name")
            if res_a.extracted.start_date != res_b.extracted.start_date:
                disagreement_fields.append("start_date")
            if res_a.extracted.end_date != res_b.extracted.end_date:
                disagreement_fields.append("end_date")

            if disagreement_fields:
                disagreements.append({
                    "contract_id": res_a.contract_id,
                    "disagreement_fields": disagreement_fields,
                    "prompt_a_correct": res_a.all_correct,
                    "prompt_b_correct": res_b.all_correct,
                    "prompt_a_extracted": {
                        "student_name": res_a.extracted.student_name,
                        "matrikelnummer": res_a.extracted.matrikelnummer,
                        "company_name": res_a.extracted.company_name,
                        "start_date": str(res_a.extracted.start_date) if res_a.extracted.start_date else None,
                        "end_date": str(res_a.extracted.end_date) if res_a.extracted.end_date else None,
                    },
                    "prompt_b_extracted": {
                        "student_name": res_b.extracted.student_name,
                        "matrikelnummer": res_b.extracted.matrikelnummer,
                        "company_name": res_b.extracted.company_name,
                        "start_date": str(res_b.extracted.start_date) if res_b.extracted.start_date else None,
                        "end_date": str(res_b.extracted.end_date) if res_b.extracted.end_date else None,
                    },
                })

        return disagreements
