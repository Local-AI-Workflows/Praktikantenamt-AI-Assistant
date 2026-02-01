"""
Workflow validation logic and metrics calculation.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from sklearn.metrics import accuracy_score

# Add categorization module to path for imports
categorization_path = Path(__file__).parent.parent.parent.parent.parent / "categorization"
sys.path.insert(0, str(categorization_path))

from prompt_tester.core.validator import Validator as BaseValidator

from workflow_validator.data.schemas import (
    EmailLocation,
    FolderMapping,
    WorkflowMisclassification,
    WorkflowValidationReport,
)


class WorkflowValidator(BaseValidator):
    """
    Extends base Validator with workflow-specific validation.
    Reuses sklearn-based metrics calculation from parent class.
    """

    def __init__(self, categories: List[str], folder_mappings: List[FolderMapping]):
        """
        Initialize workflow validator.

        Args:
            categories: List of valid category names
            folder_mappings: IMAP folder to category mappings
        """
        super().__init__(categories)
        self.folder_mappings = {fm.folder_name: fm.category for fm in folder_mappings}

    def map_folder_to_category(self, folder_name: str) -> str:
        """
        Map IMAP folder name to category.

        Args:
            folder_name: IMAP folder name

        Returns:
            Mapped category (defaults to "uncategorized" if not found)
        """
        return self.folder_mappings.get(folder_name, "uncategorized")

    def validate_email_locations(
        self,
        email_locations: List[EmailLocation],
        folder_mappings: List[FolderMapping],
        wait_time: int,
        total_sent: int,
    ) -> WorkflowValidationReport:
        """
        Validate email routing and generate report.

        Similar to base validate_results but uses EmailLocation instead of Result.

        Args:
            email_locations: List of email locations
            folder_mappings: Folder mappings used
            wait_time: Wait time in seconds
            total_sent: Total emails sent

        Returns:
            WorkflowValidationReport with all metrics
        """
        # Extract predictions and ground truth
        y_true = [el.expected_category for el in email_locations]
        y_pred = [el.predicted_category or "uncategorized" for el in email_locations]

        # Calculate overall accuracy using sklearn
        overall_accuracy = accuracy_score(y_true, y_pred)

        # Count correct and incorrect
        correct = sum(el.is_correct for el in email_locations)
        incorrect = len(email_locations) - correct

        # Calculate per-category metrics (reuse parent method)
        per_category_metrics = self.calculate_metrics_per_category(y_true, y_pred)

        # Generate confusion matrix (reuse parent method)
        confusion_matrix = self.generate_confusion_matrix(y_true, y_pred)

        # Find misrouted emails and create simplified misclassification records
        misclassifications = [
            WorkflowMisclassification(
                email_id=el.email_id,
                predicted_category=el.predicted_category or "uncategorized",
                expected_category=el.expected_category,
                found_in_folder=el.found_in_folder or "NOT_FOUND",
            )
            for el in email_locations
            if not el.is_correct
        ]

        # Emails not found
        emails_not_found = [
            str(el.uuid)
            for el in email_locations
            if el.found_in_folder is None
        ]

        return WorkflowValidationReport(
            overall_accuracy=overall_accuracy,
            total_emails=len(email_locations),
            correct_predictions=correct,
            incorrect_predictions=incorrect,
            per_category_metrics=per_category_metrics,
            confusion_matrix=confusion_matrix,
            misclassifications=misclassifications,
            prompt_name="n8n_workflow",
            prompt_version="1.0",
            test_timestamp=datetime.now(),
            email_locations=email_locations,
            emails_not_found=emails_not_found,
            folder_mappings_used=folder_mappings,
            wait_time_seconds=wait_time,
            total_sent=total_sent,
            total_found=len([el for el in email_locations if el.found_in_folder]),
        )
