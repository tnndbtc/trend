"""
Script → ShotList adaptation module (Phase 0, Workstream B).

Public API surface:
    ScriptToShotListAdapter  — main adapter class
    Script, ShotList         — Pydantic artifact models
    validate_script          — validate a raw dict as a Script
    validate_shotlist        — validate a raw dict as a ShotList
    compute_timing_lock_hash — timing authority function (§38.6 blocking interface)
"""

from .adapter import ScriptToShotListAdapter
from .models import (
    ActionBeat,
    AudioIntent,
    CameraFraming,
    CameraMovement,
    DialogueBeat,
    Scene,
    Script,
    Shot,
    ShotList,
    ShotType,
    TimeOfDay,
)
from .timing import compute_timing_lock_hash
from .validator import validate_script, validate_shotlist

__all__ = [
    # Adapter
    "ScriptToShotListAdapter",
    # Models — Script side
    "Script",
    "Scene",
    "DialogueBeat",
    "ActionBeat",
    "TimeOfDay",
    # Models — ShotList side
    "ShotList",
    "Shot",
    "ShotType",
    "CameraFraming",
    "CameraMovement",
    "AudioIntent",
    # Utilities
    "compute_timing_lock_hash",
    "validate_script",
    "validate_shotlist",
]
