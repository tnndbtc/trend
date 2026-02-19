"""
timing_lock_hash stability and sensitivity tests.

Validates §38.6 timing authority guarantees:
  - Same Script → same hash across N runs (determinism).
  - Any change to shot count, shot_id, or duration → different hash.
  - Float representation drift does not affect the hash.
  - Empty shot list produces a valid, stable hash.
  - Hash is a 64-character lowercase hex string (SHA-256).
"""

from __future__ import annotations

import hashlib
import json

import pytest

from trend_agent.generators.adaptation.adapter import ScriptToShotListAdapter
from trend_agent.generators.adaptation.models import (
    AudioIntent,
    CameraFraming,
    CameraMovement,
    Script,
    Shot,
    ShotType,
)
from trend_agent.generators.adaptation.timing import compute_timing_lock_hash


def _make_script(beats: list[dict] | None = None) -> Script:
    return Script.model_validate(
        {
            "schema_version": "1.0.0",
            "script_id": "timing-test-001",
            "title": "Timing Test",
            "scenes": [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": beats or [],
                }
            ],
        }
    )


def _make_shot(shot_id: str, duration: float) -> Shot:
    return Shot(
        shot_id=shot_id,
        scene_id="s01",
        shot_type=ShotType.ESTABLISHING,
        camera_framing=CameraFraming.WIDE,
        camera_movement=CameraMovement.STATIC,
        duration_seconds=duration,
        environment_notes="INT. X - DAY",
    )


adapter = ScriptToShotListAdapter()


# ---------------------------------------------------------------------------
# Determinism (same input → same hash)
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_empty_shots_deterministic(self):
        h1 = compute_timing_lock_hash([])
        h2 = compute_timing_lock_hash([])
        assert h1 == h2

    def test_same_shots_deterministic(self):
        shots = [_make_shot("s01_000", 2.5), _make_shot("s01_001", 1.5)]
        h1 = compute_timing_lock_hash(shots)
        h2 = compute_timing_lock_hash(shots)
        assert h1 == h2

    def test_adapter_same_script_50_runs(self):
        """Core acceptance criterion: identical Script → identical hash every time."""
        script = _make_script(
            [
                {"type": "dialogue", "speaker_id": "alice", "text": "Hello."},
                {"type": "action", "description": "She waves."},
            ]
        )
        hashes = {adapter.adapt(script).timing_lock_hash for _ in range(50)}
        assert len(hashes) == 1, f"Non-deterministic! Got {len(hashes)} distinct hashes."

    def test_shotlist_id_differs_but_hash_same(self):
        """shotlist_id (UUID4) must not influence timing_lock_hash."""
        script = _make_script(
            [{"type": "dialogue", "speaker_id": "a", "text": "Hi."}]
        )
        sl1 = adapter.adapt(script)
        sl2 = adapter.adapt(script)
        assert sl1.shotlist_id != sl2.shotlist_id  # UUIDs differ
        assert sl1.timing_lock_hash == sl2.timing_lock_hash  # hash is stable


# ---------------------------------------------------------------------------
# Sensitivity (any timing change → different hash)
# ---------------------------------------------------------------------------


class TestSensitivity:
    def test_duration_change_changes_hash(self):
        shots_v1 = [_make_shot("s01_000", 2.5)]
        shots_v2 = [_make_shot("s01_000", 2.501)]  # 1 ms delta
        assert compute_timing_lock_hash(shots_v1) != compute_timing_lock_hash(shots_v2)

    def test_shot_count_change_changes_hash(self):
        shots_1 = [_make_shot("s01_000", 2.5)]
        shots_2 = [_make_shot("s01_000", 2.5), _make_shot("s01_001", 1.5)]
        assert compute_timing_lock_hash(shots_1) != compute_timing_lock_hash(shots_2)

    def test_shot_id_change_changes_hash(self):
        shots_v1 = [_make_shot("s01_000", 2.5)]
        shots_v2 = [_make_shot("s02_000", 2.5)]  # same duration, different id
        assert compute_timing_lock_hash(shots_v1) != compute_timing_lock_hash(shots_v2)

    def test_shot_order_change_changes_hash(self):
        """Timeline order is part of the hash — swapping shots changes it."""
        shot_a = _make_shot("s01_000", 2.5)
        shot_b = _make_shot("s01_001", 1.5)
        h1 = compute_timing_lock_hash([shot_a, shot_b])
        h2 = compute_timing_lock_hash([shot_b, shot_a])
        assert h1 != h2

    def test_empty_vs_one_shot_different_hash(self):
        h_empty = compute_timing_lock_hash([])
        h_one = compute_timing_lock_hash([_make_shot("s01_000", 2.5)])
        assert h_empty != h_one


# ---------------------------------------------------------------------------
# Float representation stability (1.5 == 1.500 == 1.5000 → same hash)
# ---------------------------------------------------------------------------


class TestFloatStability:
    def test_float_rounding_stability(self):
        """round(x, 3) eliminates float representation drift."""
        shot_a = _make_shot("s01_000", 1.5)
        shot_b = _make_shot("s01_000", 1.500)
        shot_c = _make_shot("s01_000", 1.5000)
        h_a = compute_timing_lock_hash([shot_a])
        h_b = compute_timing_lock_hash([shot_b])
        h_c = compute_timing_lock_hash([shot_c])
        assert h_a == h_b == h_c

    def test_sub_millisecond_differences_collapsed_by_rounding(self):
        """Differences smaller than 0.001 s are collapsed by round(..., 3)."""
        shot_exact = _make_shot("s01_000", 2.0)
        shot_near = _make_shot("s01_000", 2.0004)  # rounds to 2.0
        assert compute_timing_lock_hash([shot_exact]) == compute_timing_lock_hash([shot_near])

    def test_differences_above_rounding_threshold_preserved(self):
        shot_exact = _make_shot("s01_000", 2.0)
        shot_diff = _make_shot("s01_000", 2.001)  # rounds to 2.001 ≠ 2.0
        assert compute_timing_lock_hash([shot_exact]) != compute_timing_lock_hash([shot_diff])


# ---------------------------------------------------------------------------
# Hash format
# ---------------------------------------------------------------------------


class TestHashFormat:
    def test_hash_is_64_char_lowercase_hex(self):
        h = compute_timing_lock_hash([])
        assert len(h) == 64
        assert h == h.lower()
        int(h, 16)  # raises ValueError if not valid hex

    def test_hash_is_sha256(self):
        """Verify the hash matches a manually computed SHA-256."""
        shots: list[Shot] = []
        canonical = json.dumps([], sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        expected = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        assert compute_timing_lock_hash(shots) == expected

    def test_non_empty_hash_is_sha256(self):
        shots = [_make_shot("s01_000", 2.5)]
        canonical = [{"duration_seconds": 2.5, "shot_id": "s01_000"}]
        payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        assert compute_timing_lock_hash(shots) == expected
