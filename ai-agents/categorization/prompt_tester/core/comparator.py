"""
Side-by-side comparison of multiple prompts.
"""

from datetime import datetime
from typing import Dict, List

from prompt_tester.core.executor import PromptExecutor
from prompt_tester.core.validator import Validator
from prompt_tester.data.schemas import (
    ComparisonReport,
    Disagreement,
    Email,
    PromptConfig,
    Result,
)


class Comparator:
    """Compares multiple prompts on the same dataset."""

    def __init__(self, executor: PromptExecutor, validator: Validator):
        """
        Initialize comparator.

        Args:
            executor: PromptExecutor instance
            validator: Validator instance
        """
        self.executor = executor
        self.validator = validator

    def compare_prompts(
        self, prompt_configs: List[PromptConfig], dataset: List[Email]
    ) -> ComparisonReport:
        """
        Compare multiple prompts on the same dataset.

        Args:
            prompt_configs: List of PromptConfig objects to compare
            dataset: List of emails to test on

        Returns:
            ComparisonReport with comparison results
        """
        if len(prompt_configs) < 2:
            raise ValueError("Need at least 2 prompts to compare")

        # Run each prompt on the dataset
        all_results: Dict[str, List[Result]] = {}

        for prompt_config in prompt_configs:
            results = self.executor.execute_batch(dataset, prompt_config)
            all_results[prompt_config.name] = results

        # Calculate accuracy for each prompt
        accuracy_comparison = {}
        for name, results in all_results.items():
            accuracy = self.validator.calculate_accuracy(results)
            accuracy_comparison[name] = accuracy

        # Find disagreements (for first two prompts for simplicity)
        # Can be extended to compare all pairs
        prompt_names = list(all_results.keys())
        results_a = all_results[prompt_names[0]]
        results_b = all_results[prompt_names[1]]
        disagreements = self.identify_disagreements(results_a, results_b)

        # Determine winner (highest accuracy)
        winner = max(accuracy_comparison.items(), key=lambda x: x[1])[0]

        return ComparisonReport(
            prompts_compared=[pc.name for pc in prompt_configs],
            accuracy_comparison=accuracy_comparison,
            disagreements=disagreements,
            winner=winner,
            test_timestamp=datetime.now(),
        )

    def identify_disagreements(
        self, results_a: List[Result], results_b: List[Result]
    ) -> List[Disagreement]:
        """
        Identify cases where two prompts disagree on categorization.

        Args:
            results_a: Results from first prompt
            results_b: Results from second prompt

        Returns:
            List of Disagreement objects
        """
        disagreements = []

        # Ensure results are for the same emails
        if len(results_a) != len(results_b):
            raise ValueError("Result lists must have same length")

        for res_a, res_b in zip(results_a, results_b):
            # Check if same email
            if res_a.email_id != res_b.email_id:
                raise ValueError(f"Email ID mismatch: {res_a.email_id} vs {res_b.email_id}")

            # Check if predictions differ
            if res_a.predicted_category != res_b.predicted_category:
                disagreements.append(
                    Disagreement(
                        email_id=res_a.email_id,
                        prompt_a_prediction=res_a.predicted_category,
                        prompt_b_prediction=res_b.predicted_category,
                        expected_category=res_a.expected_category,
                        prompt_a_correct=res_a.is_correct,
                        prompt_b_correct=res_b.is_correct,
                    )
                )

        return disagreements
