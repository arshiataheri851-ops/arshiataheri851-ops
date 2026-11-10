import re

_ARABIC_TO_PERSIAN = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک"})
_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670]")
_WHITESPACE = re.compile(r"\s+")


def normalize_persian_text(text: str) -> str:
    """Apply conservative, deterministic normalization to Persian/Arabic text.

    Keep punctuation, Latin characters, and the zero-width non-joiner intact:
    aggressive rewriting can change meaning or damage Persian morphology.
    """
    normalized = text.translate(_ARABIC_TO_PERSIAN)
    normalized = _DIACRITICS.sub("", normalized)
    normalized = normalized.replace("ـ", "")
    return _WHITESPACE.sub(" ", normalized).strip()
