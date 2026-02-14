"""
OCR corruption simulator for test contract generation.

Simulates character-level errors introduced by optical character recognition
on scanned documents. Text-only simulation — no images or PDFs are involved.
"""

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from contract_validator.data.schemas import OcrSeverity


# Probability parameters per severity level
_SEVERITY_PARAMS: Dict[str, Dict[str, float]] = {
    OcrSeverity.LOW: {
        "char_sub_prob": 0.02,
        "double_space_prob": 0.03,
        "missing_space_prob": 0.01,
        "extra_break_prob": 0.05,
        "table_pipe_prob": 0.03,
        "noise_char_prob": 0.005,
        "char_missing_prob": 0.005,
        "char_double_prob": 0.005,
    },
    OcrSeverity.MEDIUM: {
        "char_sub_prob": 0.07,
        "double_space_prob": 0.10,
        "missing_space_prob": 0.04,
        "extra_break_prob": 0.15,
        "table_pipe_prob": 0.10,
        "noise_char_prob": 0.02,
        "char_missing_prob": 0.015,
        "char_double_prob": 0.015,
    },
    OcrSeverity.HIGH: {
        "char_sub_prob": 0.15,
        "double_space_prob": 0.20,
        "missing_space_prob": 0.10,
        "extra_break_prob": 0.30,
        "table_pipe_prob": 0.25,
        "noise_char_prob": 0.05,
        "char_missing_prob": 0.03,
        "char_double_prob": 0.03,
    },
}

# Classic OCR confusion pairs — ordered so multi-char entries are checked first
_MULTI_CHAR_CONFUSIONS: List[Tuple[str, str]] = [
    ("rn", "m"),
    ("m", "rn"),
    ("vv", "w"),
    ("cl", "d"),
]

_SINGLE_CHAR_CONFUSIONS: List[Tuple[str, str]] = [
    ("0", "O"),
    ("O", "0"),
    ("o", "0"),
    ("1", "l"),
    ("l", "1"),
    ("1", "I"),
    ("I", "1"),
    ("l", "I"),
    ("5", "S"),
    ("S", "5"),
    ("6", "G"),
    ("8", "B"),
    ("B", "8"),
]

_NOISE_CHARS: List[str] = [".", ",", "~", "`", "'", "^", ";"]


@dataclass
class CorruptionStats:
    """Counts of each corruption type applied to a contract."""

    char_substitutions: int = 0
    spacing_artifacts: int = 0
    line_break_irregularities: int = 0
    table_corruption: int = 0
    noise_characters: int = 0
    missing_characters: int = 0
    doubled_characters: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "char_substitutions": self.char_substitutions,
            "spacing_artifacts": self.spacing_artifacts,
            "line_break_irregularities": self.line_break_irregularities,
            "table_corruption": self.table_corruption,
            "noise_characters": self.noise_characters,
            "missing_characters": self.missing_characters,
            "doubled_characters": self.doubled_characters,
        }


class OcrSimulator:
    """
    Simulates OCR corruption on contract text.

    Applies a 6-stage pipeline of realistic text degradation that mirrors
    common OCR errors from scanning physical documents:
      1. Character substitutions (classic OCR confusions)
      2. Spacing artifacts (double/missing spaces)
      3. Line break irregularities (extra blank lines)
      4. Table formatting corruption (pipe characters)
      5. Noise characters (stray symbols)
      6. Missing/doubled characters

    Usage::

        simulator = OcrSimulator(seed=42)
        corrupted_text, stats = simulator.corrupt(clean_text, OcrSeverity.MEDIUM)
    """

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)

    def corrupt(self, text: str, severity: OcrSeverity) -> Tuple[str, CorruptionStats]:
        """
        Apply OCR-like corruption to contract text.

        Args:
            text: Clean contract text
            severity: Corruption intensity level

        Returns:
            Tuple of (corrupted_text, CorruptionStats)
        """
        params = _SEVERITY_PARAMS[severity]
        stats = CorruptionStats()

        text = self._apply_char_substitutions(text, params["char_sub_prob"], stats)
        text = self._apply_spacing_artifacts(
            text, params["double_space_prob"], params["missing_space_prob"], stats
        )
        text = self._apply_line_break_irregularities(text, params["extra_break_prob"], stats)
        text = self._apply_table_corruption(text, params["table_pipe_prob"], stats)
        text = self._apply_noise_characters(text, params["noise_char_prob"], stats)
        text = self._apply_missing_doubled(
            text, params["char_missing_prob"], params["char_double_prob"], stats
        )

        return text, stats

    def _apply_char_substitutions(
        self, text: str, prob: float, stats: CorruptionStats
    ) -> str:
        """Substitute characters using OCR confusion pairs."""
        chars = list(text)
        i = 0
        while i < len(chars):
            # Try multi-char confusions first (rn→m etc.)
            matched = False
            for src, dst in _MULTI_CHAR_CONFUSIONS:
                src_len = len(src)
                if "".join(chars[i : i + src_len]) == src and self._rng.random() < prob:
                    chars[i : i + src_len] = list(dst)
                    stats.char_substitutions += 1
                    i += len(dst)
                    matched = True
                    break
            if not matched:
                for src, dst in _SINGLE_CHAR_CONFUSIONS:
                    if chars[i] == src and self._rng.random() < prob:
                        chars[i] = dst
                        stats.char_substitutions += 1
                        break
                i += 1
        return "".join(chars)

    def _apply_spacing_artifacts(
        self,
        text: str,
        double_prob: float,
        missing_prob: float,
        stats: CorruptionStats,
    ) -> str:
        """Introduce double spaces and fused words (missing spaces)."""
        words = text.split(" ")
        result: List[str] = []
        for word in words:
            result.append(word)
            r = self._rng.random()
            if r < double_prob:
                result.append("")  # extra empty string → double space on join
                stats.spacing_artifacts += 1
            elif r < double_prob + missing_prob and len(result) >= 2:
                # Fuse last two tokens (removes space between them)
                merged = result[-2] + result[-1]
                result = result[:-2] + [merged]
                stats.spacing_artifacts += 1
        return " ".join(result)

    def _apply_line_break_irregularities(
        self, text: str, prob: float, stats: CorruptionStats
    ) -> str:
        """Insert extra blank lines to simulate scanner feed artifacts."""
        lines = text.split("\n")
        result: List[str] = []
        for line in lines:
            result.append(line)
            if self._rng.random() < prob:
                result.append("")  # extra blank line
                stats.line_break_irregularities += 1
        return "\n".join(result)

    def _apply_table_corruption(
        self, text: str, prob: float, stats: CorruptionStats
    ) -> str:
        """Corrupt pipe characters in tabular contracts."""
        lines = text.split("\n")
        result: List[str] = []
        for line in lines:
            if "|" in line:
                chars = list(line)
                for j, ch in enumerate(chars):
                    if ch == "|" and self._rng.random() < prob:
                        chars[j] = self._rng.choice([" ", "!", "l", "i"])
                        stats.table_corruption += 1
                line = "".join(chars)
            result.append(line)
        return "\n".join(result)

    def _apply_noise_characters(
        self, text: str, prob: float, stats: CorruptionStats
    ) -> str:
        """Insert stray noise characters at word boundaries."""
        chars = list(text)
        insertions: List[Tuple[int, str]] = []
        for i, ch in enumerate(chars):
            if ch == " " and self._rng.random() < prob:
                noise = self._rng.choice(_NOISE_CHARS)
                insertions.append((i, noise))
                stats.noise_characters += 1
        # Insert in reverse order to preserve indices
        for i, noise in reversed(insertions):
            chars.insert(i, noise)
        return "".join(chars)

    def _apply_missing_doubled(
        self,
        text: str,
        missing_prob: float,
        double_prob: float,
        stats: CorruptionStats,
    ) -> str:
        """Drop or duplicate individual alphabetic characters."""
        result: List[str] = []
        for ch in text:
            if ch.isalpha():
                r = self._rng.random()
                if r < missing_prob:
                    stats.missing_characters += 1
                    continue  # drop character
                elif r < missing_prob + double_prob:
                    result.append(ch)
                    result.append(ch)  # double character
                    stats.doubled_characters += 1
                    continue
            result.append(ch)
        return "".join(result)
