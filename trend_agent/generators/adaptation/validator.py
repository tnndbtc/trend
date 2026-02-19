"""
Validation helpers for Script and ShotList artifacts.

Uses Pydantic v2 model validation only — no external JSON Schema library
required. Pydantic enforces required fields, enum values, type coercions,
and the extra="ignore" policy (unknown fields silently dropped per §30.2).

Raises pydantic.ValidationError for any invalid input.
"""

from __future__ import annotations

from pydantic import ValidationError  # re-exported for caller convenience

from .models import Script, ShotList

__all__ = ["validate_script", "validate_shotlist", "ValidationError"]


def validate_script(data: dict) -> Script:
    """
    Parse and validate a raw dict as a Script artifact.

    Args:
        data: Raw JSON-decoded dictionary.

    Returns:
        Validated Script Pydantic model.

    Raises:
        pydantic.ValidationError: If any required field is missing or has
            an invalid type/value.
    """
    return Script.model_validate(data)


def validate_shotlist(data: dict) -> ShotList:
    """
    Parse and validate a raw dict as a ShotList artifact.

    Args:
        data: Raw JSON-decoded dictionary.

    Returns:
        Validated ShotList Pydantic model.

    Raises:
        pydantic.ValidationError: If any required field is missing or has
            an invalid type/value.
    """
    return ShotList.model_validate(data)
