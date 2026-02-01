"""Translator module for bilingual support."""

import os
from typing import Optional

from company_lookup.i18n.translations import TRANSLATIONS, get_translation

# Default language
_current_language: str = "en"

# Supported languages
SUPPORTED_LANGUAGES = ["en", "de"]


class Translator:
    """Translator class for managing translations."""

    def __init__(self, language: str = "en"):
        """Initialize the translator.

        Args:
            language: Language code ('en' or 'de'). Defaults to 'en'.
        """
        self.language = self._validate_language(language)

    def _validate_language(self, language: str) -> str:
        """Validate and normalize a language code.

        Args:
            language: The language code to validate.

        Returns:
            Valid language code ('en' or 'de').
        """
        lang = language.lower().strip()

        # Handle common variations
        if lang in ("de", "german", "deutsch", "de-de", "de_de"):
            return "de"
        elif lang in ("en", "english", "en-us", "en_us", "en-gb", "en_gb"):
            return "en"

        # Default to English for unknown languages
        return "en"

    def set_language(self, language: str) -> None:
        """Set the current language.

        Args:
            language: Language code to set.
        """
        self.language = self._validate_language(language)

    def get_language(self) -> str:
        """Get the current language.

        Returns:
            Current language code.
        """
        return self.language

    def t(self, key: str, **kwargs) -> str:
        """Translate a key.

        Args:
            key: The translation key.
            **kwargs: Format arguments for the translation string.

        Returns:
            The translated string.
        """
        return get_translation(key, self.language, **kwargs)

    def __call__(self, key: str, **kwargs) -> str:
        """Shorthand for t().

        Args:
            key: The translation key.
            **kwargs: Format arguments for the translation string.

        Returns:
            The translated string.
        """
        return self.t(key, **kwargs)


# Global translator instance
_translator: Optional[Translator] = None


def get_translator() -> Translator:
    """Get the global translator instance.

    The language is determined in the following order:
    1. Previously set language via set_language()
    2. COMPANY_LOOKUP_LANGUAGE environment variable
    3. LANG environment variable (first two characters)
    4. Default to 'en'

    Returns:
        The global Translator instance.
    """
    global _translator

    if _translator is None:
        # Determine language from environment
        language = os.environ.get("COMPANY_LOOKUP_LANGUAGE")

        if not language:
            # Try to get from LANG environment variable
            lang_env = os.environ.get("LANG", "en")
            # Extract language code (e.g., "de_DE.UTF-8" -> "de")
            language = lang_env[:2] if len(lang_env) >= 2 else "en"

        _translator = Translator(language)

    return _translator


def set_language(language: str) -> None:
    """Set the global language.

    Args:
        language: Language code to set ('en' or 'de').
    """
    global _current_language, _translator

    translator = get_translator()
    translator.set_language(language)
    _current_language = translator.language


def t(key: str, **kwargs) -> str:
    """Translate a key using the global translator.

    This is a convenience function for quick translations.

    Args:
        key: The translation key.
        **kwargs: Format arguments for the translation string.

    Returns:
        The translated string.

    Example:
        >>> t("mcp.lookup_company.description")
        'Look up a company in the whitelist/blacklist database'

        >>> set_language("de")
        >>> t("mcp.lookup_company.description")
        'Eine Firma in der Whitelist/Blacklist-Datenbank suchen'

        >>> t("engine.warning.fuzzy_match", query="Siemens", matched="Siemens AG")
        "Fuzzy-Treffer: 'Siemens' zugeordnet zu 'Siemens AG'"
    """
    return get_translator().t(key, **kwargs)


def get_current_language() -> str:
    """Get the current language code.

    Returns:
        Current language code ('en' or 'de').
    """
    return get_translator().get_language()
