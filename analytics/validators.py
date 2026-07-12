"""Validation helpers for agent outputs."""


def validate_analysis_output(text: str) -> tuple[bool, str]:
    """Basic quality gate for analysis responses."""
    if not text or not text.strip():
        return False, "Analysis output is empty."
    if len(text.strip()) < 20:
        return False, "Analysis output is too short to be useful."
    return True, "ok"
