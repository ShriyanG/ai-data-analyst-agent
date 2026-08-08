"""Validation helpers for agent outputs."""


REQUIRED_SECTIONS = [
    "Direct Answer:",
    "Evidence:",
    "Method Note:",
    "Assumptions/Interpretation:",
]


def _missing_sections(text: str) -> list[str]:
    lowered = text.lower()
    return [section for section in REQUIRED_SECTIONS if section.lower() not in lowered]


def validate_analysis_output(text: str) -> tuple[bool, str]:
    """Phase 1 quality gate for contract-compliant analysis responses."""
    if not text or not text.strip():
        return False, "Analysis output is empty."
    if len(text.strip()) < 20:
        return False, "Analysis output is too short to be useful."

    missing = _missing_sections(text)
    if missing:
        return False, (
            "Analysis output is missing required sections: "
            + ", ".join(missing)
        )

    return True, "ok"
