"""
Shot template library for the rules-based Script → ShotList adapter.

Each ShotTemplate encodes a camera framing, movement, and duration rule for a
given shot type. All logic is deterministic and requires no external calls.

Duration constants are tuned for a standard ~140 wpm speaking pace and a
3-second-per-beat action pacing, matching typical animatic timing.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import CameraFraming, CameraMovement, ShotType

# ---------------------------------------------------------------------------
# Duration constants
# ---------------------------------------------------------------------------

#: Average speaking rate used for dialogue shots (~140 wpm at ~6 chars/word).
CHARS_PER_SEC: float = 14.0

MIN_DIALOGUE_DUR: float = 1.5   # seconds — floor for very short lines
MAX_DIALOGUE_DUR: float = 12.0  # seconds — cap for very long monologues

#: Action shots: every word of description contributes ~0.5 s of screen time.
WORDS_PER_SEC_ACTION: float = 2.0  # word_count / WORDS_PER_SEC_ACTION = seconds

MIN_ACTION_DUR: float = 2.0   # seconds
MAX_ACTION_DUR: float = 8.0   # seconds

#: Fixed durations for non-text-driven shot types.
ESTABLISHING_DUR: float = 2.5
REACTION_DUR: float = 1.5
EMOTIONAL_DUR: float = 2.0


# ---------------------------------------------------------------------------
# Template dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShotTemplate:
    """
    Immutable description of camera framing, movement, and duration strategy
    for a single shot type.
    """

    shot_type: ShotType
    camera_framing: CameraFraming
    camera_movement: CameraMovement

    # ------------------------------------------------------------------
    # Duration calculators — call the appropriate one per shot type.
    # ------------------------------------------------------------------

    def duration_for_dialogue(self, text: str) -> float:
        """Estimate shot duration from dialogue character count."""
        raw = len(text) / CHARS_PER_SEC
        return round(max(MIN_DIALOGUE_DUR, min(MAX_DIALOGUE_DUR, raw)), 3)

    def duration_for_action(self, description: str) -> float:
        """Estimate shot duration from action word count."""
        word_count = len(description.split())
        raw = word_count / WORDS_PER_SEC_ACTION
        return round(max(MIN_ACTION_DUR, min(MAX_ACTION_DUR, raw)), 3)

    def fixed_duration(self) -> float:
        """Return the fixed duration for template types that don't use text length."""
        _fixed: dict[ShotType, float] = {
            ShotType.ESTABLISHING: ESTABLISHING_DUR,
            ShotType.REACTION: REACTION_DUR,
            ShotType.CLOSE_UP_EMOTIONAL: EMOTIONAL_DUR,
        }
        return round(_fixed[self.shot_type], 3)


# ---------------------------------------------------------------------------
# Template singletons — one per ShotType
# ---------------------------------------------------------------------------

TEMPLATES: dict[ShotType, ShotTemplate] = {
    ShotType.ESTABLISHING: ShotTemplate(
        shot_type=ShotType.ESTABLISHING,
        camera_framing=CameraFraming.WIDE,
        camera_movement=CameraMovement.STATIC,
    ),
    ShotType.MEDIUM_DIALOGUE: ShotTemplate(
        shot_type=ShotType.MEDIUM_DIALOGUE,
        camera_framing=CameraFraming.MEDIUM,
        camera_movement=CameraMovement.STATIC,
    ),
    ShotType.REACTION: ShotTemplate(
        shot_type=ShotType.REACTION,
        camera_framing=CameraFraming.MEDIUM,
        camera_movement=CameraMovement.STATIC,
    ),
    ShotType.ACTION_BEAT: ShotTemplate(
        shot_type=ShotType.ACTION_BEAT,
        camera_framing=CameraFraming.MEDIUM,
        camera_movement=CameraMovement.SLOW_PAN,
    ),
    ShotType.CLOSE_UP_EMOTIONAL: ShotTemplate(
        shot_type=ShotType.CLOSE_UP_EMOTIONAL,
        camera_framing=CameraFraming.CLOSE_UP,
        camera_movement=CameraMovement.PUSH_IN,
    ),
}

# ---------------------------------------------------------------------------
# Emotional tag → music mood lookup (freeform string → standardised label)
# ---------------------------------------------------------------------------

EMOTIONAL_TAG_TO_MOOD: dict[str, str] = {
    "joy": "uplifting",
    "happiness": "uplifting",
    "sadness": "melancholic",
    "grief": "mournful",
    "anger": "tense",
    "tension": "tense",
    "fear": "suspense",
    "love": "romantic",
    "surprise": "whimsical",
    "disgust": "dissonant",
    "triumph": "epic",
    "hope": "uplifting",
    "despair": "mournful",
    "wonder": "whimsical",
}


def resolve_music_mood(emotional_tag: str | None) -> str | None:
    """
    Map a freeform emotional_tag string to a standardised music_mood label.

    Falls back to lowercased emotional_tag if no mapping is found, so any
    tag passes through rather than being silently dropped.
    """
    if emotional_tag is None:
        return None
    return EMOTIONAL_TAG_TO_MOOD.get(emotional_tag.lower(), emotional_tag.lower())
