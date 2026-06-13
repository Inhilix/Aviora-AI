import re

PII_PATTERNS = {
    "email":    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phone":    r"\b(\+?880|0)[-.\s]?\d{10,11}\b",
    "passport": r"\b[A-Z]{1,2}\d{6,9}\b",
    "nid":      r"\b\d{10,17}\b",
}


def strip_pii(text: str, student_name: str | None = None) -> tuple[str, dict]:
    """
    Remove PII from text before sending to Haiku.
    Returns (sanitised_text, restore_map) — restore_map can re-attach PII to output if needed.
    """
    stripped = text
    restore: dict[str, str] = {}

    if student_name:
        stripped = stripped.replace(student_name, "[STUDENT]")
        restore["[STUDENT]"] = student_name

    for pii_type, pattern in PII_PATTERNS.items():
        for i, match in enumerate(re.findall(pattern, stripped)):
            placeholder = f"[{pii_type.upper()}_{i + 1}]"
            stripped = stripped.replace(match, placeholder)
            restore[placeholder] = match

    return stripped, restore


def restore_pii(text: str, restore_map: dict) -> str:
    """Re-attach PII tokens to LLM output where placeholders appear."""
    for placeholder, original in restore_map.items():
        text = text.replace(placeholder, original)
    return text
