"""
Validation logic and accuracy metrics calculation.
"""

from datetime import datetime
from typing import Dict, List

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

from prompt_tester.data.schemas import (
    AggregatedMetrics,
    AggregatedValidationReport,
    Metrics,
    Result,
    ValidationReport,
)


class Validator:
    """Validates categorization results and calculates metrics."""

    def __init__(self, categories: List[str]):
        """
        Initialize validator.

        Args:
            categories: List of valid category names
        """
        self.categories = categories

    def validate_results(
        self,
        results: List[Result],
        prompt_name: str = None,
        prompt_version: str = None,
    ) -> ValidationReport:
        """
        Validate results and generate complete report.

        Args:
            results: List of categorization results
            prompt_name: Optional prompt name for report
            prompt_version: Optional prompt version for report

        Returns:
            ValidationReport with all metrics
        """
        # Extract predictions and ground truth
        y_true = [r.expected_category for r in results]
        y_pred = [r.predicted_category for r in results]

        # Calculate overall accuracy
        overall_accuracy = accuracy_score(y_true, y_pred)

        # Count correct and incorrect predictions
        correct = sum(1 for r in results if r.is_correct)
        incorrect = len(results) - correct

        # Count parse errors and mean execution time
        parse_errors = sum(1 for r in results if r.predicted_category == "parse_error")
        mean_execution_time = float(np.mean([r.execution_time for r in results])) if results else 0.0

        # Calculate per-category metrics
        per_category_metrics = self.calculate_metrics_per_category(y_true, y_pred)

        # Generate confusion matrix
        conf_matrix = self.generate_confusion_matrix(y_true, y_pred)

        # Find misclassifications
        misclassifications = [r for r in results if not r.is_correct]

        return ValidationReport(
            overall_accuracy=overall_accuracy,
            total_emails=len(results),
            correct_predictions=correct,
            incorrect_predictions=incorrect,
            parse_errors=parse_errors,
            mean_execution_time=mean_execution_time,
            per_category_metrics=per_category_metrics,
            confusion_matrix=conf_matrix,
            misclassifications=misclassifications,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            test_timestamp=datetime.now(),
        )

    def calculate_accuracy(self, results: List[Result]) -> float:
        """
        Calculate overall accuracy.

        Args:
            results: List of categorization results

        Returns:
            Accuracy score (0.0 to 1.0)
        """
        y_true = [r.expected_category for r in results]
        y_pred = [r.predicted_category for r in results]
        return accuracy_score(y_true, y_pred)

    def calculate_metrics_per_category(
        self, y_true: List[str], y_pred: List[str]
    ) -> Dict[str, Metrics]:
        """
        Calculate precision, recall, and F1-score for each category.

        Args:
            y_true: Ground truth categories
            y_pred: Predicted categories

        Returns:
            Dictionary mapping category names to Metrics objects
        """
        # Calculate metrics using sklearn
        precision, recall, f1, support = precision_recall_fscore_support(
            y_true, y_pred, labels=self.categories, average=None, zero_division=0
        )

        # Build metrics dictionary
        per_category = {}
        for i, category in enumerate(self.categories):
            per_category[category] = Metrics(
                precision=float(precision[i]),
                recall=float(recall[i]),
                f1_score=float(f1[i]),
                support=int(support[i]),
            )

        return per_category

    def generate_confusion_matrix(
        self, y_true: List[str], y_pred: List[str]
    ) -> List[List[int]]:
        """
        Generate confusion matrix.

        Args:
            y_true: Ground truth categories
            y_pred: Predicted categories

        Returns:
            NxN confusion matrix as list of lists
        """
        cm = confusion_matrix(y_true, y_pred, labels=self.categories)
        return cm.tolist()

    def identify_misclassifications(self, results: List[Result]) -> List[Result]:
        """
        Identify all misclassified emails.

        Args:
            results: List of categorization results

        Returns:
            List of misclassified Result objects
        """
        return [r for r in results if not r.is_correct]

    def aggregate_reports(
        self, reports: List[ValidationReport]
    ) -> AggregatedValidationReport:
        """
        Aggregate multiple validation reports into summary statistics.

        Args:
            reports: List of ValidationReport objects from different runs

        Returns:
            AggregatedValidationReport with mean and std dev
        """
        if not reports:
            raise ValueError("Cannot aggregate empty list of reports")

        # Calculate mean and std for overall accuracy
        accuracies = [r.overall_accuracy for r in reports]
        mean_accuracy = float(np.mean(accuracies))
        std_accuracy = float(np.std(accuracies))

        # Aggregate parse errors and execution time
        mean_parse_errors = float(np.mean([r.parse_errors for r in reports]))
        mean_execution_time = float(np.mean([r.mean_execution_time for r in reports]))

        # Aggregate per-category metrics
        per_category_metrics = {}
        for category in self.categories:
            precisions = [r.per_category_metrics[category].precision for r in reports]
            recalls = [r.per_category_metrics[category].recall for r in reports]
            f1_scores = [r.per_category_metrics[category].f1_score for r in reports]
            support = reports[0].per_category_metrics[category].support

            per_category_metrics[category] = AggregatedMetrics(
                mean_precision=float(np.mean(precisions)),
                std_precision=float(np.std(precisions)),
                mean_recall=float(np.mean(recalls)),
                std_recall=float(np.std(recalls)),
                mean_f1_score=float(np.mean(f1_scores)),
                std_f1_score=float(np.std(f1_scores)),
                support=support,
            )

        # Aggregate confusion matrices
        confusion_matrices = [r.confusion_matrix for r in reports]
        cm_array = np.array(confusion_matrices)
        aggregated_cm = np.mean(cm_array, axis=0)
        std_cm = np.std(cm_array, axis=0)

        return AggregatedValidationReport(
            num_iterations=len(reports),
            mean_accuracy=mean_accuracy,
            std_accuracy=std_accuracy,
            mean_parse_errors=mean_parse_errors,
            mean_execution_time=mean_execution_time,
            per_category_metrics=per_category_metrics,
            confusion_matrices=confusion_matrices,
            aggregated_confusion_matrix=aggregated_cm.tolist(),
            std_confusion_matrix=std_cm.tolist(),
            individual_reports=reports,
            prompt_name=reports[0].prompt_name,
            prompt_version=reports[0].prompt_version,
            test_timestamp=datetime.now(),
        )
