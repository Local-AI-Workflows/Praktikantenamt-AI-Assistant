"""
Response quality evaluation using heuristics and metrics.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional

from response_generator.data.schemas import (
    CategorizedEmail,
    Config,
    EvaluationReport,
    EvaluationResult,
    GeneratedResponse,
    QualityMetrics,
    ResponseSuggestion,
)


class ResponseEvaluator:
    """Evaluates quality of generated responses."""

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize evaluator.

        Args:
            config: Optional configuration
        """
        self.config = config or Config()

        # German stop words for content analysis
        self._stop_words = {
            "der", "die", "das", "den", "dem", "des",
            "ein", "eine", "einer", "einem", "einen",
            "und", "oder", "aber", "denn", "weil",
            "ich", "du", "er", "sie", "es", "wir", "ihr",
            "mein", "dein", "sein", "ihr", "unser", "euer",
            "ist", "sind", "war", "waren", "wird", "werden",
            "hat", "haben", "hatte", "hatten",
            "bei", "mit", "zu", "von", "aus", "nach", "in", "auf", "an",
            "fuer", "um", "ueber", "unter", "vor", "hinter",
            "sich", "auch", "noch", "nur", "schon", "dann",
        }

    def evaluate_response(
        self,
        response: GeneratedResponse,
        email: CategorizedEmail,
        expected_response: Optional[str] = None,
    ) -> EvaluationResult:
        """
        Evaluate a single generated response.

        Args:
            response: Generated response to evaluate
            email: Original email
            expected_response: Optional expected/reference response

        Returns:
            EvaluationResult with quality metrics
        """
        metrics = self._calculate_metrics(response, email, expected_response)
        feedback = self._generate_feedback(metrics, response)
        passed = metrics.overall_score >= self.config.quality_threshold

        return EvaluationResult(
            email_id=email.id,
            response_id=response.id,
            generated_response=response,
            expected_response=expected_response,
            metrics=metrics,
            passed=passed,
            feedback=feedback,
        )

    def evaluate_batch(
        self,
        suggestions: List[ResponseSuggestion],
        emails: List[CategorizedEmail],
        prompt_name: str = "default",
    ) -> EvaluationReport:
        """
        Evaluate a batch of response suggestions.

        Args:
            suggestions: List of response suggestions
            emails: List of original emails
            prompt_name: Name of the prompt/template set used

        Returns:
            EvaluationReport with aggregate statistics
        """
        # Create email lookup
        email_lookup = {email.id: email for email in emails}

        results: List[EvaluationResult] = []
        total_confidence = 0.0
        total_quality = 0.0
        total_responses = 0

        per_category_stats: Dict[str, Dict[str, float]] = {}
        per_tone_stats: Dict[str, Dict[str, float]] = {}

        for suggestion in suggestions:
            email = email_lookup.get(suggestion.email_id)
            if not email:
                continue

            for response in suggestion.responses:
                result = self.evaluate_response(response, email)
                results.append(result)

                total_confidence += response.confidence
                total_quality += result.metrics.overall_score
                total_responses += 1

                # Aggregate per-category stats
                category = suggestion.category.value
                if category not in per_category_stats:
                    per_category_stats[category] = {
                        "count": 0,
                        "total_quality": 0.0,
                        "passed": 0,
                    }
                per_category_stats[category]["count"] += 1
                per_category_stats[category]["total_quality"] += result.metrics.overall_score
                if result.passed:
                    per_category_stats[category]["passed"] += 1

                # Aggregate per-tone stats
                tone = response.tone.value
                if tone not in per_tone_stats:
                    per_tone_stats[tone] = {
                        "count": 0,
                        "total_quality": 0.0,
                        "passed": 0,
                    }
                per_tone_stats[tone]["count"] += 1
                per_tone_stats[tone]["total_quality"] += result.metrics.overall_score
                if result.passed:
                    per_tone_stats[tone]["passed"] += 1

        # Calculate averages
        avg_confidence = total_confidence / total_responses if total_responses > 0 else 0.0
        avg_quality = total_quality / total_responses if total_responses > 0 else 0.0
        passed_count = sum(1 for r in results if r.passed)
        pass_rate = passed_count / total_responses if total_responses > 0 else 0.0

        # Calculate per-category averages
        for category in per_category_stats:
            count = per_category_stats[category]["count"]
            if count > 0:
                per_category_stats[category]["average_quality"] = (
                    per_category_stats[category]["total_quality"] / count
                )
                per_category_stats[category]["pass_rate"] = (
                    per_category_stats[category]["passed"] / count
                )
            del per_category_stats[category]["total_quality"]
            del per_category_stats[category]["passed"]

        # Calculate per-tone averages
        for tone in per_tone_stats:
            count = per_tone_stats[tone]["count"]
            if count > 0:
                per_tone_stats[tone]["average_quality"] = (
                    per_tone_stats[tone]["total_quality"] / count
                )
                per_tone_stats[tone]["pass_rate"] = (
                    per_tone_stats[tone]["passed"] / count
                )
            del per_tone_stats[tone]["total_quality"]
            del per_tone_stats[tone]["passed"]

        return EvaluationReport(
            total_emails=len(emails),
            total_responses=total_responses,
            average_confidence=avg_confidence,
            average_quality=avg_quality,
            pass_rate=pass_rate,
            per_category_stats=per_category_stats,
            per_tone_stats=per_tone_stats,
            results=results,
            prompt_name=prompt_name,
            test_timestamp=datetime.now(),
        )

    def _calculate_metrics(
        self,
        response: GeneratedResponse,
        email: CategorizedEmail,
        expected_response: Optional[str] = None,
    ) -> QualityMetrics:
        """
        Calculate quality metrics for a response.

        Args:
            response: Generated response
            email: Original email
            expected_response: Optional expected response

        Returns:
            QualityMetrics
        """
        relevance = self._calculate_relevance(response, email)
        completeness = self._calculate_completeness(response)
        tone_appropriateness = self._calculate_tone_appropriateness(response)
        grammar = self._calculate_grammar_score(response)

        # Calculate overall score as weighted average
        overall = (
            relevance * 0.35
            + completeness * 0.25
            + tone_appropriateness * 0.25
            + grammar * 0.15
        )

        return QualityMetrics(
            relevance_score=relevance,
            completeness_score=completeness,
            tone_appropriateness=tone_appropriateness,
            grammar_score=grammar,
            overall_score=overall,
        )

    def _calculate_relevance(
        self, response: GeneratedResponse, email: CategorizedEmail
    ) -> float:
        """
        Calculate relevance score based on content overlap.

        Args:
            response: Generated response
            email: Original email

        Returns:
            Relevance score between 0 and 1
        """
        # Extract keywords from email
        email_words = self._extract_keywords(email.body + " " + email.subject)

        # Extract keywords from response
        response_words = self._extract_keywords(response.body)

        if not email_words:
            return 0.5  # Default score if no keywords

        # Calculate overlap
        overlap = len(email_words.intersection(response_words))
        relevance = min(1.0, overlap / max(3, len(email_words) * 0.3))

        # Boost for personalization
        if response.personalization_applied:
            relevance = min(1.0, relevance + 0.2)

        return relevance

    def _extract_keywords(self, text: str) -> set:
        """Extract meaningful keywords from text."""
        # Normalize and tokenize
        words = re.findall(r"\b[a-zA-ZaeuoeAEUOE]+\b", text.lower())

        # Filter stop words and short words
        keywords = {
            word for word in words
            if word not in self._stop_words and len(word) > 3
        }

        return keywords

    def _calculate_completeness(self, response: GeneratedResponse) -> float:
        """
        Calculate completeness score based on response structure.

        Args:
            response: Generated response

        Returns:
            Completeness score between 0 and 1
        """
        score = 0.0
        body = response.body

        # Check for greeting
        if any(
            greeting in body.lower()
            for greeting in ["hallo", "sehr geehrte", "guten tag"]
        ):
            score += 0.25

        # Check for content (minimum length)
        if len(body) > 100:
            score += 0.25
        elif len(body) > 50:
            score += 0.15

        # Check for closing
        if any(
            closing in body.lower()
            for closing in ["gruesse", "gruss", "gruessen", "mit freundlichen"]
        ):
            score += 0.25

        # Check for signature
        if "praktikantenamt" in body.lower():
            score += 0.25

        return min(1.0, score)

    def _calculate_tone_appropriateness(self, response: GeneratedResponse) -> float:
        """
        Calculate tone appropriateness score.

        Args:
            response: Generated response

        Returns:
            Tone appropriateness score between 0 and 1
        """
        body = response.body.lower()

        if response.tone.value == "formal":
            # Check for formal indicators
            formal_indicators = [
                "sehr geehrte",
                "mit freundlichen gruessen",
                "vielen dank",
                "ihnen",
                "ihre",
            ]
            informal_indicators = ["hallo", "hi", "hey", "du", "dein", "dir"]

            formal_count = sum(1 for ind in formal_indicators if ind in body)
            informal_count = sum(1 for ind in informal_indicators if ind in body)

            if formal_count > 0 and informal_count == 0:
                return 1.0
            elif formal_count > informal_count:
                return 0.7
            else:
                return 0.4

        else:  # Informal
            informal_indicators = ["hallo", "danke", "gruesse", "du", "dein", "dir"]
            formal_indicators = ["sehr geehrte", "mit freundlichen", "ihnen"]

            informal_count = sum(1 for ind in informal_indicators if ind in body)
            formal_count = sum(1 for ind in formal_indicators if ind in body)

            if informal_count > 0 and formal_count == 0:
                return 1.0
            elif informal_count > formal_count:
                return 0.7
            else:
                return 0.4

    def _calculate_grammar_score(self, response: GeneratedResponse) -> float:
        """
        Calculate basic grammar/formatting score.

        Args:
            response: Generated response

        Returns:
            Grammar score between 0 and 1
        """
        body = response.body
        score = 1.0

        # Check for common issues
        issues = 0

        # Multiple consecutive spaces
        if "  " in body:
            issues += 1

        # Missing punctuation at end of sentences
        sentences = body.split("\n")
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and not sentence[-1] in ".!?,;:":
                if len(sentence) > 30:  # Only count longer sentences
                    issues += 0.5

        # Empty lines issues (too many)
        if body.count("\n\n\n") > 0:
            issues += 1

        # Deduct for issues
        score = max(0.0, 1.0 - (issues * 0.1))

        return score

    def _generate_feedback(
        self, metrics: QualityMetrics, response: GeneratedResponse
    ) -> List[str]:
        """
        Generate feedback messages based on metrics.

        Args:
            metrics: Quality metrics
            response: Generated response

        Returns:
            List of feedback messages
        """
        feedback = []

        if metrics.relevance_score < 0.5:
            feedback.append(
                "Die Antwort scheint nicht spezifisch genug auf die E-Mail einzugehen."
            )

        if metrics.completeness_score < 0.5:
            feedback.append(
                "Die Antwort ist moeglicherweise unvollstaendig (fehlende Begruessung, Signatur, etc.)."
            )

        if metrics.tone_appropriateness < 0.6:
            feedback.append(
                f"Der Ton der Antwort entspricht nicht dem gewuenschten Stil ({response.tone.value})."
            )

        if metrics.grammar_score < 0.7:
            feedback.append(
                "Es wurden Formatierungsprobleme in der Antwort gefunden."
            )

        if metrics.overall_score >= self.config.quality_threshold:
            feedback.append("Die Antwort erfuellt die Qualitaetsanforderungen.")

        return feedback
