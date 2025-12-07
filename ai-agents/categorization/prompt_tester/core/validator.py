"""
Validation logic and accuracy metrics calculation.
"""

from datetime import datetime
from typing import Dict, List

from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

from prompt_tester.data.schemas import Metrics, Result, ValidationReport


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
