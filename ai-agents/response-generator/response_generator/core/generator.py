"""
Response generation orchestration.
"""

import re
import time
import uuid
from datetime import datetime
from typing import List, Optional

from response_generator.data.loader import TemplateLoader
from response_generator.data.schemas import (
    CategorizedEmail,
    Config,
    GeneratedResponse,
    ResponseSuggestion,
    ResponseTone,
)


class ResponseGenerator:
    """Orchestrates response generation from templates and personalization."""

    def __init__(
        self,
        template_loader: TemplateLoader,
        personalizer: Optional["Personalizer"] = None,  # noqa: F821
        config: Optional[Config] = None,
    ):
        """
        Initialize response generator.

        Args:
            template_loader: TemplateLoader instance for loading templates
            personalizer: Optional Personalizer instance for LLM personalization
            config: Optional configuration (uses defaults if not provided)
        """
        self.template_loader = template_loader
        self.personalizer = personalizer
        self.config = config or Config()

    def generate_response(
        self,
        email: CategorizedEmail,
        tones: Optional[List[ResponseTone]] = None,
    ) -> ResponseSuggestion:
        """
        Generate response suggestions for an email.

        Args:
            email: Categorized email to respond to
            tones: List of tones to generate (defaults based on config)

        Returns:
            ResponseSuggestion with all generated responses
        """
        # Determine which tones to generate
        if tones is None:
            if self.config.generate_both_tones:
                tones = [ResponseTone.FORMAL, ResponseTone.INFORMAL]
            else:
                tones = [ResponseTone(self.config.default_tone)]

        responses: List[GeneratedResponse] = []

        for tone in tones:
            response = self._generate_single_response(email, tone)
            if response:
                responses.append(response)

        # Select recommended response (highest confidence)
        if responses:
            recommended = max(responses, key=lambda r: r.confidence)
            recommended_id = recommended.id
        else:
            recommended_id = ""

        return ResponseSuggestion(
            email_id=email.id,
            category=email.category,
            responses=responses,
            recommended_response_id=recommended_id,
            timestamp=datetime.now(),
        )

    def _generate_single_response(
        self, email: CategorizedEmail, tone: ResponseTone
    ) -> Optional[GeneratedResponse]:
        """
        Generate a single response for a specific tone.

        Args:
            email: Email to respond to
            tone: Tone of the response

        Returns:
            GeneratedResponse or None if template not found
        """
        start_time = time.time()

        # Get template
        template = self.template_loader.get_template(email.category, tone)
        if not template:
            return None

        # Extract sender name from email
        sender_name = self._extract_sender_name(email.sender)

        # Generate personalized content if enabled
        personalized_content = ""
        raw_llm_output = None
        personalization_applied = False

        if self.config.personalization_enabled and self.personalizer:
            try:
                personalized_content, raw_llm_output = self.personalizer.personalize(
                    email, tone
                )
                personalization_applied = True
            except Exception as e:
                # Fall back to no personalization on error
                print(f"Warning: Personalization failed: {e}")
                personalized_content = ""

        # Apply template
        subject, body = self._apply_template(
            template, email, sender_name, personalized_content, tone
        )

        # Calculate confidence
        confidence = self._calculate_confidence(
            email, personalization_applied, len(personalized_content) > 0
        )

        generation_time = time.time() - start_time

        return GeneratedResponse(
            id=str(uuid.uuid4()),
            email_id=email.id,
            tone=tone,
            subject=subject,
            body=body,
            confidence=confidence,
            template_used=f"{email.category.value}/{tone.value}",
            personalization_applied=personalization_applied,
            generation_time=generation_time,
            raw_llm_output=raw_llm_output,
        )

    def _extract_sender_name(self, sender: str) -> str:
        """
        Extract name from email address.

        Examples:
            - max.mueller@haw-hamburg.de -> Max Mueller
            - sarah.schmidt@student.haw.de -> Sarah Schmidt
            - unknown@test.de -> Unknown

        Args:
            sender: Email address

        Returns:
            Extracted name with proper capitalization
        """
        # Extract local part before @
        match = re.match(r"([^@]+)@", sender)
        if not match:
            return "Unbekannt"

        local_part = match.group(1)

        # Split by common separators
        parts = re.split(r"[._-]", local_part)

        # Capitalize each part
        name_parts = []
        for part in parts:
            if part:
                # Skip numbers
                if part.isdigit():
                    continue
                name_parts.append(part.capitalize())

        if name_parts:
            return " ".join(name_parts)

        return "Unbekannt"

    def _apply_template(
        self,
        template,
        email: CategorizedEmail,
        sender_name: str,
        personalized_content: str,
        tone: ResponseTone,
    ) -> tuple:
        """
        Apply template with all placeholders filled.

        Args:
            template: ResponseTemplate to apply
            email: Original email
            sender_name: Extracted sender name
            personalized_content: LLM-generated personalized content
            tone: Response tone

        Returns:
            Tuple of (subject, body)
        """
        # Determine greeting and closing based on tone
        if tone == ResponseTone.FORMAL:
            greeting = "Sehr geehrte/r"
            closing = "Mit freundlichen Gruessen"
            signature = "Praktikantenamt HAW Hamburg"
        else:
            greeting = "Hallo"
            closing = ""
            signature = ""

        # Prepare placeholder values
        placeholders = {
            "original_subject": email.subject,
            "sender_name": sender_name,
            "greeting": greeting,
            "closing": closing,
            "signature": signature,
            "personalized_content": personalized_content,
        }

        # Apply to subject
        subject = template.subject_template
        for key, value in placeholders.items():
            subject = subject.replace(f"{{{key}}}", value)

        # Apply to body
        body = template.body_template
        for key, value in placeholders.items():
            body = body.replace(f"{{{key}}}", value)

        # Clean up empty lines from missing placeholders
        body = self._clean_body(body)

        return subject, body

    def _clean_body(self, body: str) -> str:
        """
        Clean up response body by removing excess whitespace.

        Args:
            body: Raw body text

        Returns:
            Cleaned body text
        """
        # Remove lines that are just whitespace
        lines = body.split("\n")
        cleaned_lines = []
        prev_empty = False

        for line in lines:
            is_empty = not line.strip()
            # Avoid multiple consecutive empty lines
            if is_empty and prev_empty:
                continue
            cleaned_lines.append(line)
            prev_empty = is_empty

        return "\n".join(cleaned_lines).strip()

    def _calculate_confidence(
        self,
        email: CategorizedEmail,
        personalization_applied: bool,
        has_personalized_content: bool,
    ) -> float:
        """
        Calculate confidence score for generated response.

        Args:
            email: Original email
            personalization_applied: Whether personalization was attempted
            has_personalized_content: Whether personalized content was generated

        Returns:
            Confidence score between 0 and 1
        """
        base_confidence = 0.7

        # Boost for personalization
        if personalization_applied and has_personalized_content:
            base_confidence += 0.15

        # Boost for high categorization confidence
        if email.categorization_confidence:
            if email.categorization_confidence > 0.9:
                base_confidence += 0.1
            elif email.categorization_confidence > 0.7:
                base_confidence += 0.05

        # Penalty for uncategorized
        if email.category.value == "uncategorized":
            base_confidence -= 0.1

        return min(1.0, max(0.0, base_confidence))

    def generate_batch(
        self,
        emails: List[CategorizedEmail],
        tones: Optional[List[ResponseTone]] = None,
    ) -> List[ResponseSuggestion]:
        """
        Generate responses for a batch of emails.

        Args:
            emails: List of categorized emails
            tones: Optional list of tones to generate

        Returns:
            List of ResponseSuggestion objects
        """
        suggestions = []
        for email in emails:
            suggestion = self.generate_response(email, tones)
            suggestions.append(suggestion)
        return suggestions
