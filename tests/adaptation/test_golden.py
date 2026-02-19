"""
Golden fixture regression test: Script → ShotList.

Loads tests/fixtures/script_fixture.json, runs the adapter, and compares
the structural output field-by-field against tests/fixtures/shotlist_fixture.json.

What is checked:
  - Number of shots matches.
  - Each shot's id, scene_id, shot_type, camera_framing, camera_movement,
    duration_seconds, characters, expressions, environment_notes, action_beat,
    and audio_intent fields match the fixture exactly.
  - total_duration_seconds matches the fixture.
  - timing_lock_hash is deterministic (adapter run twice → same hash).

What is NOT checked against the fixture:
  - shotlist_id — intentionally a new UUID per run.
  - timing_lock_hash exact value — pinned separately in test_timing_hash_pinned.

To regenerate the shotlist_fixture.json after intentional changes:
    python -c "
    import json
    from trend_agent.generators.adaptation import ScriptToShotListAdapter, validate_script
    script = validate_script(json.load(open('tests/fixtures/script_fixture.json')))
    sl = ScriptToShotListAdapter().adapt(script)
    data = sl.model_dump(mode='json')
    data.pop('shotlist_id')          # exclude volatile field
    print(json.dumps(data, indent=2))
    "
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from trend_agent.generators.adaptation.adapter import ScriptToShotListAdapter
from trend_agent.generators.adaptation.models import ShotList
from trend_agent.generators.adaptation.validator import validate_script

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
SCRIPT_FIXTURE = FIXTURES_DIR / "script_fixture.json"
SHOTLIST_FIXTURE = FIXTURES_DIR / "shotlist_fixture.json"

adapter = ScriptToShotListAdapter()


@pytest.fixture(scope="module")
def script():
    raw = json.loads(SCRIPT_FIXTURE.read_text())
    return validate_script(raw)


@pytest.fixture(scope="module")
def expected() -> dict:
    return json.loads(SHOTLIST_FIXTURE.read_text())


@pytest.fixture(scope="module")
def actual(script) -> ShotList:
    return adapter.adapt(script)


# ---------------------------------------------------------------------------
# Structural tests
# ---------------------------------------------------------------------------


class TestGoldenStructure:
    def test_shot_count(self, actual, expected):
        assert len(actual.shots) == len(expected["shots"]), (
            f"Expected {len(expected['shots'])} shots, got {len(actual.shots)}"
        )

    def test_total_duration(self, actual, expected):
        assert actual.total_duration_seconds == pytest.approx(
            expected["total_duration_seconds"], abs=0.001
        )

    def test_script_id_propagated(self, actual, expected):
        assert actual.script_id == expected["script_id"]

    def test_schema_version(self, actual, expected):
        assert actual.schema_version == expected["schema_version"]

    @pytest.mark.parametrize("idx", range(11))  # 11 shots in the fixture
    def test_shot_fields(self, actual, expected, idx):
        got = actual.shots[idx]
        want = expected["shots"][idx]

        assert got.shot_id == want["shot_id"], f"shot[{idx}] shot_id mismatch"
        assert got.scene_id == want["scene_id"], f"shot[{idx}] scene_id mismatch"
        assert got.shot_type.value == want["shot_type"], f"shot[{idx}] shot_type mismatch"
        assert got.camera_framing.value == want["camera_framing"], (
            f"shot[{idx}] camera_framing mismatch"
        )
        assert got.camera_movement.value == want["camera_movement"], (
            f"shot[{idx}] camera_movement mismatch"
        )
        assert got.duration_seconds == pytest.approx(want["duration_seconds"], abs=0.001), (
            f"shot[{idx}] duration_seconds mismatch"
        )
        assert got.characters == want["characters"], f"shot[{idx}] characters mismatch"
        assert got.expressions == want["expressions"], f"shot[{idx}] expressions mismatch"
        assert got.environment_notes == want["environment_notes"], (
            f"shot[{idx}] environment_notes mismatch"
        )
        assert got.action_beat == want["action_beat"], f"shot[{idx}] action_beat mismatch"
        assert got.audio_intent.vo_ref == want["audio_intent"]["vo_ref"], (
            f"shot[{idx}] audio_intent.vo_ref mismatch"
        )
        assert got.audio_intent.sfx_tags == want["audio_intent"]["sfx_tags"], (
            f"shot[{idx}] audio_intent.sfx_tags mismatch"
        )
        assert got.audio_intent.music_mood == want["audio_intent"]["music_mood"], (
            f"shot[{idx}] audio_intent.music_mood mismatch"
        )


# ---------------------------------------------------------------------------
# Determinism test (timing_lock_hash stability)
# ---------------------------------------------------------------------------


class TestGoldenDeterminism:
    def test_timing_lock_hash_stable_across_runs(self, script):
        """
        Running the adapter multiple times on the same Script must always
        produce the same timing_lock_hash. This is the Phase 0 acceptance
        criterion for Workstream B (§19.0).
        """
        hashes = {adapter.adapt(script).timing_lock_hash for _ in range(10)}
        assert len(hashes) == 1, (
            f"Non-deterministic timing_lock_hash! Got {len(hashes)} distinct values: {hashes}"
        )

    def test_timing_lock_hash_is_sha256_hex(self, actual):
        h = actual.timing_lock_hash
        assert len(h) == 64
        assert h == h.lower()
        int(h, 16)  # valid hex

    def test_shotlist_id_differs_between_runs(self, script):
        """shotlist_id is a new UUID4 each run — must differ."""
        ids = {adapter.adapt(script).shotlist_id for _ in range(5)}
        assert len(ids) == 5, "shotlist_id should be unique per run"


# ---------------------------------------------------------------------------
# Schema validation of actual output
# ---------------------------------------------------------------------------


class TestGoldenSchemaValid:
    def test_actual_output_roundtrips_through_pydantic(self, actual):
        """The adapter output must be serializable and re-parseable by Pydantic."""
        dumped = actual.model_dump(mode="json")
        reloaded = ShotList.model_validate(dumped)
        assert reloaded.timing_lock_hash == actual.timing_lock_hash
        assert reloaded.total_duration_seconds == actual.total_duration_seconds
        assert len(reloaded.shots) == len(actual.shots)

    def test_all_shots_have_valid_enums(self, actual):
        from trend_agent.generators.adaptation.models import (
            CameraFraming,
            CameraMovement,
            ShotType,
        )

        for shot in actual.shots:
            assert isinstance(shot.shot_type, ShotType)
            assert isinstance(shot.camera_framing, CameraFraming)
            assert isinstance(shot.camera_movement, CameraMovement)

    def test_all_durations_positive(self, actual):
        for shot in actual.shots:
            assert shot.duration_seconds > 0, (
                f"Shot {shot.shot_id} has non-positive duration: {shot.duration_seconds}"
            )

    def test_total_duration_matches_shot_sum(self, actual):
        expected_total = round(sum(s.duration_seconds for s in actual.shots), 3)
        assert actual.total_duration_seconds == pytest.approx(expected_total, abs=0.001)
