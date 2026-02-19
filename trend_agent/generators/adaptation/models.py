"""
Pydantic v2 data models for the Script → ShotList pipeline.

Implements the artifact schemas defined in:
  - §5.5  Script  (scenes, dialogue, actions, emotional tags)
  - §5.6  ShotList (film-ready breakdown with duration, framing, audio intent)

Schema version: 1.0.0
Ownership: trend/world-engine (Workstream B) per §38.1

Design rules (§30.2):
  - model_config extra="ignore" — tolerate unknown fields from future MINOR bumps.
  - Missing required fields raise ValidationError — never silently swallowed.
  - schema_version embedded in every artifact.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Script models — §5.5
# ---------------------------------------------------------------------------


class TimeOfDay(str, Enum):
    """Valid time-of-day values for a scene."""

    DAY = "DAY"
    NIGHT = "NIGHT"
    DAWN = "DAWN"
    DUSK = "DUSK"


class DialogueBeat(BaseModel):
    """A spoken line attributed to a single character."""

    model_config = {"extra": "ignore"}

    type: Literal["dialogue"]
    speaker_id: str = Field(..., description="Character identifier who speaks this line.")
    text: str = Field(..., description="Verbatim dialogue text; drives duration estimation.")
    emotional_tag: Optional[str] = Field(
        None,
        description="Optional freeform emotional label (e.g. 'joy', 'tension').",
    )


class ActionBeat(BaseModel):
    """A scripted physical action or visual event (no spoken dialogue)."""

    model_config = {"extra": "ignore"}

    type: Literal["action"]
    description: str = Field(..., description="Action description; drives duration estimation.")
    emotional_tag: Optional[str] = Field(
        None,
        description="Optional freeform emotional label.",
    )


# Discriminated union; Pydantic dispatches on the 'type' literal field.
Beat = Annotated[Union[DialogueBeat, ActionBeat], Field(discriminator="type")]


class Scene(BaseModel):
    """A contiguous block of story in a single location / time-of-day."""

    model_config = {"extra": "ignore"}

    scene_id: str = Field(..., description="Unique identifier within the script.")
    location: str = Field(..., description="Location slug, e.g. 'INT. CAFE'.")
    time_of_day: TimeOfDay
    beats: list[Beat] = Field(default_factory=list)


class Script(BaseModel):
    """
    Full screenplay artifact (§5.5).

    Produced upstream; consumed by ScriptToShotListAdapter.
    No camera instructions — all framing is assigned by the adapter.
    """

    model_config = {"extra": "ignore"}

    schema_version: str = Field("1.0.0", description="Semver schema version (§30.1).")
    script_id: str = Field(..., description="Globally unique artifact identifier.")
    title: str
    scenes: list[Scene] = Field(..., min_length=0)


# ---------------------------------------------------------------------------
# ShotList models — §5.6
# ---------------------------------------------------------------------------


class ShotType(str, Enum):
    """Cinematic shot template type."""

    ESTABLISHING = "ESTABLISHING"
    MEDIUM_DIALOGUE = "MEDIUM_DIALOGUE"
    REACTION = "REACTION"
    ACTION_BEAT = "ACTION_BEAT"
    CLOSE_UP_EMOTIONAL = "CLOSE_UP_EMOTIONAL"


class CameraFraming(str, Enum):
    """Camera distance / focal framing."""

    WIDE = "WIDE"
    MEDIUM = "MEDIUM"
    CLOSE_UP = "CLOSE_UP"
    INSERT = "INSERT"
    CUTAWAY = "CUTAWAY"


class CameraMovement(str, Enum):
    """Camera motion during the shot."""

    STATIC = "STATIC"
    SLOW_PAN = "SLOW_PAN"
    PUSH_IN = "PUSH_IN"


class AudioIntent(BaseModel):
    """Audio metadata for a single shot (VO refs, SFX tags, music mood)."""

    model_config = {"extra": "ignore"}

    vo_ref: Optional[str] = Field(
        None,
        description="Speaker ID providing voice-over for this shot (if dialogue).",
    )
    sfx_tags: list[str] = Field(
        default_factory=list,
        description="Sound effect labels. Always empty in Phase 0.",
    )
    music_mood: Optional[str] = Field(
        None,
        description="Derived from emotional_tag; guides music selection in later phases.",
    )


class Shot(BaseModel):
    """A single cinematic shot within the ShotList."""

    model_config = {"extra": "ignore"}

    shot_id: str = Field(
        ...,
        description="Stable ID: '{scene_id}_{index:03d}'. Used in timing_lock_hash.",
    )
    scene_id: str
    shot_type: ShotType
    camera_framing: CameraFraming
    camera_movement: CameraMovement
    duration_seconds: float = Field(
        ...,
        description="Shot duration in seconds, rounded to 3 dp. Authoritative after lock.",
    )
    characters: list[str] = Field(
        default_factory=list,
        description="Character IDs visible in frame.",
    )
    expressions: Optional[str] = Field(
        None,
        description="Expression / pose hint derived from emotional_tag.",
    )
    environment_notes: str = Field(
        ...,
        description="'{location} - {time_of_day}' from the source scene.",
    )
    action_beat: Optional[str] = Field(
        None,
        description="Action description text (for ACTION_BEAT shots).",
    )
    audio_intent: AudioIntent = Field(default_factory=AudioIntent)


class ShotList(BaseModel):
    """
    Film-ready shot breakdown artifact (§5.6).

    timing_lock_hash is set at creation and must not be mutated.
    Any re-generation from the same Script produces the same hash (deterministic).
    Changing the hash generation logic is a BLOCKING change per §38.6.
    """

    model_config = {"extra": "ignore"}

    schema_version: str = Field("1.0.0", description="Semver schema version (§30.1).")
    shotlist_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="New UUID per run; excluded from timing_lock_hash.",
    )
    script_id: str = Field(..., description="Source Script artifact ID.")
    timing_lock_hash: str = Field(
        ...,
        description=(
            "SHA-256 hex digest of canonicalized shot-timing list. "
            "Stable across reruns for identical Script input. "
            "Changing this field's computation is a §38.6 blocking change."
        ),
    )
    total_duration_seconds: float = Field(
        ...,
        description="Sum of all shot durations, rounded to 3 dp.",
    )
    shots: list[Shot]
