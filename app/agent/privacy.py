"""Privacy policy — model cannot override these levels."""

from __future__ import annotations

from enum import StrEnum


class PrivacyLevel(StrEnum):
    STANDARD = "standard"
    PRIVATE = "private"
    STRICT = "strict"


def cloud_allowed(level: PrivacyLevel) -> bool:
    return level != PrivacyLevel.STRICT


def prefer_local(level: PrivacyLevel) -> bool:
    return level in (PrivacyLevel.PRIVATE, PrivacyLevel.STRICT)
