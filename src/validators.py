"""Input validation and safeguards for the travel policy assistant."""
import re

SUPPORTED_MODES = ("air", "rail", "bus")
TRANSACTION_RE = re.compile(r"\b(book|cancel|purchase|reserve|change|modify)\b.{0,35}\b(for me|it now|this booking|my ticket)\b", re.I)


def normalize_mode(mode: str) -> str:
    value = (mode or "").strip().lower()
    aliases = {"flight": "air", "airline": "air", "train": "rail", "railway": "rail", "bus": "bus"}
    value = aliases.get(value, value)
    if value not in SUPPORTED_MODES:
        raise ValueError("Choose air, rail, or bus travel.")
    return value


def validate_question(question: str) -> str:
    value = " ".join((question or "").split())
    if not value:
        raise ValueError("Enter a travel policy question.")
    if len(value) > 1200:
        raise ValueError("Keep your question under 1,200 characters.")
    return value


def is_transaction_request(question: str) -> bool:
    return bool(TRANSACTION_RE.search(question or ""))
