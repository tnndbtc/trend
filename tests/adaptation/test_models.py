"""
Schema / model validation tests — Pydantic roundtrip and rejection.

Covers §30.2 requirements:
  - Readers tolerate unknown fields (MINOR schema bumps).
  - Readers surface clear errors for missing required fields.
  - Enum validation rejects unknown values.
  - schema_version survives roundtrip.
"""

from __future__ import annotations

import copy
import pytest
from pydantic import ValidationError

from trend_agent.generators.adaptation.models import (
    CameraFraming,
    CameraMovement,
    Script,
    Shot,
    ShotList,
    ShotType,
    TimeOfDay,
)

# ---------------------------------------------------------------------------
# Minimal valid dicts (used as base for mutation tests)
# ---------------------------------------------------------------------------

MINIMAL_SCRIPT: dict = {
    "schema_version": "1.0.0",
    "script_id": "test-script-001",
    "title": "Test Episode",
    "scenes": [
        {
            "scene_id": "s01",
            "location": "INT. ROOM",
            "time_of_day": "DAY",
            "beats": [
                {
                    "type": "dialogue",
                    "speaker_id": "char_a",
                    "text": "Hello.",
                }
            ],
        }
    ],
}

MINIMAL_SHOT: dict = {
    "shot_id": "s01_000",
    "scene_id": "s01",
    "shot_type": "ESTABLISHING",
    "camera_framing": "WIDE",
    "camera_movement": "STATIC",
    "duration_seconds": 2.5,
    "environment_notes": "INT. ROOM - DAY",
}

MINIMAL_SHOTLIST: dict = {
    "schema_version": "1.0.0",
    "shotlist_id": "test-sl-001",
    "script_id": "test-script-001",
    "timing_lock_hash": "abc123",
    "total_duration_seconds": 2.5,
    "shots": [MINIMAL_SHOT],
}


# ---------------------------------------------------------------------------
# Script — roundtrip
# ---------------------------------------------------------------------------


class TestScriptRoundtrip:
    def test_parse_and_serialize_minimal(self):
        script = Script.model_validate(MINIMAL_SCRIPT)
        dumped = script.model_dump(mode="json")
        assert dumped["script_id"] == "test-script-001"
        assert dumped["schema_version"] == "1.0.0"
        assert len(dumped["scenes"]) == 1
        assert dumped["scenes"][0]["beats"][0]["type"] == "dialogue"

    def test_schema_version_preserved(self):
        data = copy.deepcopy(MINIMAL_SCRIPT)
        data["schema_version"] = "1.2.3"
        script = Script.model_validate(data)
        assert script.schema_version == "1.2.3"

    def test_optional_emotional_tag_absent(self):
        script = Script.model_validate(MINIMAL_SCRIPT)
        beat = script.scenes[0].beats[0]
        assert beat.emotional_tag is None  # type: ignore[union-attr]

    def test_optional_emotional_tag_present(self):
        data = copy.deepcopy(MINIMAL_SCRIPT)
        data["scenes"][0]["beats"][0] = {**data["scenes"][0]["beats"][0], "emotional_tag": "joy"}
        script = Script.model_validate(data)
        assert script.scenes[0].beats[0].emotional_tag == "joy"  # type: ignore[union-attr]

    def test_action_beat_parsed(self):
        data = copy.deepcopy(MINIMAL_SCRIPT)
        data["scenes"][0]["beats"] = [{"type": "action", "description": "She runs."}]
        script = Script.model_validate(data)
        beat = script.scenes[0].beats[0]
        assert beat.type == "action"
        assert beat.description == "She runs."  # type: ignore[union-attr]

    def test_empty_scenes_allowed(self):
        data = copy.deepcopy(MINIMAL_SCRIPT)
        data["scenes"] = []
        script = Script.model_validate(data)
        assert script.scenes == []

    def test_empty_beats_allowed(self):
        data = copy.deepcopy(MINIMAL_SCRIPT)
        data["scenes"][0]["beats"] = []
        script = Script.model_validate(data)
        assert script.scenes[0].beats == []


# ---------------------------------------------------------------------------
# Script — unknown fields tolerated (§30.2)
# ---------------------------------------------------------------------------


class TestScriptUnknownFields:
    def test_unknown_top_level_field_ignored(self):
        data = copy.deepcopy(MINIMAL_SCRIPT)
        data["future_field"] = "some_value"
        script = Script.model_validate(data)
        assert not hasattr(script, "future_field")

    def test_unknown_scene_field_ignored(self):
        data = copy.deepcopy(MINIMAL_SCRIPT)
        data["scenes"][0] = {**data["scenes"][0], "extra": 42}
        script = Script.model_validate(data)
        assert not hasattr(script.scenes[0], "extra")

    def test_unknown_beat_field_ignored(self):
        data = copy.deepcopy(MINIMAL_SCRIPT)
        data["scenes"][0]["beats"][0] = {**data["scenes"][0]["beats"][0], "mystery": True}
        script = Script.model_validate(data)
        beat = script.scenes[0].beats[0]
        assert not hasattr(beat, "mystery")


# ---------------------------------------------------------------------------
# Script — required field rejections (§30.2)
# ---------------------------------------------------------------------------


class TestScriptRequiredFields:
    def test_missing_script_id_raises(self):
        data = {k: v for k, v in MINIMAL_SCRIPT.items() if k != "script_id"}
        with pytest.raises(ValidationError) as exc_info:
            Script.model_validate(data)
        assert "script_id" in str(exc_info.value)

    def test_missing_title_raises(self):
        data = {k: v for k, v in MINIMAL_SCRIPT.items() if k != "title"}
        with pytest.raises(ValidationError):
            Script.model_validate(data)

    def test_missing_scenes_raises(self):
        data = {k: v for k, v in MINIMAL_SCRIPT.items() if k != "scenes"}
        with pytest.raises(ValidationError):
            Script.model_validate(data)

    def test_missing_dialogue_speaker_id_raises(self):
        data = copy.deepcopy(MINIMAL_SCRIPT)
        data["scenes"][0]["beats"] = [{"type": "dialogue", "text": "Hello."}]
        with pytest.raises(ValidationError):
            Script.model_validate(data)

    def test_missing_dialogue_text_raises(self):
        data = copy.deepcopy(MINIMAL_SCRIPT)
        data["scenes"][0]["beats"] = [{"type": "dialogue", "speaker_id": "char_a"}]
        with pytest.raises(ValidationError):
            Script.model_validate(data)

    def test_missing_action_description_raises(self):
        data = copy.deepcopy(MINIMAL_SCRIPT)
        data["scenes"][0]["beats"] = [{"type": "action"}]
        with pytest.raises(ValidationError):
            Script.model_validate(data)


# ---------------------------------------------------------------------------
# Script — enum validation
# ---------------------------------------------------------------------------


class TestScriptEnums:
    def test_valid_time_of_day(self):
        for tod in ("DAY", "NIGHT", "DAWN", "DUSK"):
            data = copy.deepcopy(MINIMAL_SCRIPT)
            data["scenes"][0] = {**data["scenes"][0], "time_of_day": tod}
            script = Script.model_validate(data)
            assert script.scenes[0].time_of_day == TimeOfDay(tod)

    def test_invalid_time_of_day_raises(self):
        data = copy.deepcopy(MINIMAL_SCRIPT)
        data["scenes"][0] = {**data["scenes"][0], "time_of_day": "NOON"}
        with pytest.raises(ValidationError):
            Script.model_validate(data)

    def test_unknown_beat_type_raises(self):
        data = copy.deepcopy(MINIMAL_SCRIPT)
        data["scenes"][0]["beats"] = [{"type": "narration", "text": "Once upon..."}]
        with pytest.raises(ValidationError):
            Script.model_validate(data)


# ---------------------------------------------------------------------------
# ShotList — roundtrip
# ---------------------------------------------------------------------------


class TestShotListRoundtrip:
    def test_parse_and_serialize_minimal(self):
        sl = ShotList.model_validate(MINIMAL_SHOTLIST)
        dumped = sl.model_dump(mode="json")
        assert dumped["schema_version"] == "1.0.0"
        assert dumped["timing_lock_hash"] == "abc123"
        assert len(dumped["shots"]) == 1

    def test_shot_enums_preserved(self):
        sl = ShotList.model_validate(MINIMAL_SHOTLIST)
        shot = sl.shots[0]
        assert shot.shot_type == ShotType.ESTABLISHING
        assert shot.camera_framing == CameraFraming.WIDE
        assert shot.camera_movement == CameraMovement.STATIC

    def test_shotlist_unknown_field_ignored(self):
        data = {**MINIMAL_SHOTLIST, "future_field": "x"}
        sl = ShotList.model_validate(data)
        assert not hasattr(sl, "future_field")

    def test_shotlist_missing_timing_lock_hash_raises(self):
        data = {k: v for k, v in MINIMAL_SHOTLIST.items() if k != "timing_lock_hash"}
        with pytest.raises(ValidationError):
            ShotList.model_validate(data)

    def test_shot_invalid_framing_raises(self):
        shot = {**MINIMAL_SHOT, "camera_framing": "FISHEYE"}
        data = {**MINIMAL_SHOTLIST, "shots": [shot]}
        with pytest.raises(ValidationError):
            ShotList.model_validate(data)

    def test_shot_optional_fields_default(self):
        sl = ShotList.model_validate(MINIMAL_SHOTLIST)
        shot = sl.shots[0]
        assert shot.characters == []
        assert shot.expressions is None
        assert shot.action_beat is None
        assert shot.audio_intent.vo_ref is None
        assert shot.audio_intent.sfx_tags == []
        assert shot.audio_intent.music_mood is None

    def test_shotlist_id_defaults_to_uuid(self):
        data = {k: v for k, v in MINIMAL_SHOTLIST.items() if k != "shotlist_id"}
        sl = ShotList.model_validate(data)
        assert sl.shotlist_id  # non-empty string
        # Should look like a UUID (36 chars with dashes)
        assert len(sl.shotlist_id) == 36
