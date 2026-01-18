"""
Template and prompt comparison functionality.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from response_generator.core.evaluator import ResponseEvaluator
from response_generator.core.generator import ResponseGenerator
from response_generator.core.personalizer import Personalizer, create_personalizer_from_config
from response_generator.data.loader import DataLoader, TemplateLoader
from response_generator.data.schemas import (
    CategorizedEmail,
    ComparisonReport,
    Config,
    EvaluationReport,
)


class TemplateComparator:
    """Compares multiple template sets or personalization prompts."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize comparator.

        Args:
            config: Optional configuration
        """
        self.config = config or Config()
        self.evaluator = ResponseEvaluator(config)

    def compare_templates(
        self,
        template_dirs: List[str],
        emails: List[CategorizedEmail],
    ) -> ComparisonReport:
        """
        Compare multiple template directories.

        Args:
            template_dirs: List of template directory paths
            emails: List of emails to test on

        Returns:
            ComparisonReport with comparison results
        """
        quality_comparison: Dict[str, float] = {}
        per_category_comparison: Dict[str, Dict[str, float]] = {}
        all_reports: Dict[str, EvaluationReport] = {}

        for template_dir in template_dirs:
            template_name = Path(template_dir).name

            # Load templates
            template_loader = TemplateLoader(template_dir)

            # Create generator (without personalization for fair comparison)
            config_no_personalization = Config(
                **self.config.model_dump(),
            )
            config_no_personalization.personalization_enabled = False

            generator = ResponseGenerator(
                template_loader=template_loader,
                personalizer=None,
                config=config_no_personalization,
            )

            # Generate responses
            suggestions = generator.generate_batch(emails)

            # Evaluate
            report = self.evaluator.evaluate_batch(
                suggestions, emails, prompt_name=template_name
            )
            all_reports[template_name] = report

            # Store quality score
            quality_comparison[template_name] = report.average_quality

            # Store per-category scores
            per_category_comparison[template_name] = {
                category: stats.get("average_quality", 0.0)
                for category, stats in report.per_category_stats.items()
            }

        # Determine winner
        winner = max(quality_comparison, key=quality_comparison.get) if quality_comparison else None

        return ComparisonReport(
            templates_compared=template_dirs,
            quality_comparison=quality_comparison,
            per_category_comparison=per_category_comparison,
            winner=winner,
            test_timestamp=datetime.now(),
        )

    def compare_prompts(
        self,
        prompt_dirs: List[str],
        emails: List[CategorizedEmail],
        template_dir: str,
    ) -> ComparisonReport:
        """
        Compare multiple personalization prompt sets.

        Args:
            prompt_dirs: List of prompt directory paths
            emails: List of emails to test on
            template_dir: Template directory to use (same for all)

        Returns:
            ComparisonReport with comparison results
        """
        quality_comparison: Dict[str, float] = {}
        per_category_comparison: Dict[str, Dict[str, float]] = {}

        # Load templates (shared across comparisons)
        template_loader = TemplateLoader(template_dir)

        for prompt_dir in prompt_dirs:
            prompt_name = Path(prompt_dir).name

            # Create personalizer for this prompt set
            config_for_prompt = Config(**self.config.model_dump())
            config_for_prompt.prompts_directory = prompt_dir
            config_for_prompt.personalization_enabled = True

            personalizer = create_personalizer_from_config(config_for_prompt)

            # Create generator
            generator = ResponseGenerator(
                template_loader=template_loader,
                personalizer=personalizer,
                config=config_for_prompt,
            )

            # Generate responses
            suggestions = generator.generate_batch(emails)

            # Evaluate
            report = self.evaluator.evaluate_batch(
                suggestions, emails, prompt_name=prompt_name
            )

            # Store quality score
            quality_comparison[prompt_name] = report.average_quality

            # Store per-category scores
            per_category_comparison[prompt_name] = {
                category: stats.get("average_quality", 0.0)
                for category, stats in report.per_category_stats.items()
            }

        # Determine winner
        winner = max(quality_comparison, key=quality_comparison.get) if quality_comparison else None

        return ComparisonReport(
            templates_compared=prompt_dirs,
            quality_comparison=quality_comparison,
            per_category_comparison=per_category_comparison,
            winner=winner,
            test_timestamp=datetime.now(),
        )
