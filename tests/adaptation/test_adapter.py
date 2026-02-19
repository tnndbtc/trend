"""
Unit tests for ScriptToShotListAdapter shot-boundary rules.

Validates each shot template trigger in isolation, covering:
  - ESTABLISHING shot always opens a scene
  - MEDIUM_DIALOGUE per speaker
  - REACTION inserted on speaker change
  - CLOSE_UP_EMOTIONAL appended after beat with emotional_tag
  - ACTION_BEAT with word-count-based duration
  - Duration formula bounds (min / max caps)
  - Empty scenes produce no shots beyond ESTABLISHING
  - Speaker tracking resets after ACTION beat
"""

from __future__ import annotations

import pytest

from trend_agent.generators.adaptation.adapter import ScriptToShotListAdapter
from trend_agent.generators.adaptation.models import Script, ShotType
from trend_agent.generators.adaptation.shot_templates import (
    MAX_ACTION_DUR,
    MAX_DIALOGUE_DUR,
    MIN_ACTION_DUR,
    MIN_DIALOGUE_DUR,
)


def _make_script(scenes_data: list[dict]) -> Script:
    """Helper: build a Script from a plain list-of-dicts."""
    return Script.model_validate(
        {
            "schema_version": "1.0.0",
            "script_id": "test-adapter-001",
            "title": "Adapter Test",
            "scenes": scenes_data,
        }
    )


adapter = ScriptToShotListAdapter()


# ---------------------------------------------------------------------------
# Establishing shot
# ---------------------------------------------------------------------------


class TestEstablishingShot:
    def test_empty_scene_produces_only_establishing(self):
        script = _make_script(
            [{"scene_id": "s01", "location": "INT. HALL", "time_of_day": "NIGHT", "beats": []}]
        )
        sl = adapter.adapt(script)
        assert len(sl.shots) == 1
        assert sl.shots[0].shot_type == ShotType.ESTABLISHING
        assert sl.shots[0].duration_seconds == 2.5

    def test_establishing_is_first_shot_in_scene(self):
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "EXT. PARK",
                    "time_of_day": "DAY",
                    "beats": [
                        {"type": "dialogue", "speaker_id": "x", "text": "Hi."}
                    ],
                }
            ]
        )
        sl = adapter.adapt(script)
        assert sl.shots[0].shot_type == ShotType.ESTABLISHING

    def test_each_scene_opens_with_establishing(self):
        script = _make_script(
            [
                {"scene_id": "s01", "location": "A", "time_of_day": "DAY", "beats": []},
                {"scene_id": "s02", "location": "B", "time_of_day": "NIGHT", "beats": []},
            ]
        )
        sl = adapter.adapt(script)
        assert sl.shots[0].shot_type == ShotType.ESTABLISHING
        assert sl.shots[0].scene_id == "s01"
        assert sl.shots[1].shot_type == ShotType.ESTABLISHING
        assert sl.shots[1].scene_id == "s02"

    def test_establishing_environment_notes(self):
        script = _make_script(
            [{"scene_id": "s01", "location": "INT. LAB", "time_of_day": "DAWN", "beats": []}]
        )
        sl = adapter.adapt(script)
        assert sl.shots[0].environment_notes == "INT. LAB - DAWN"


# ---------------------------------------------------------------------------
# MEDIUM_DIALOGUE shot
# ---------------------------------------------------------------------------


class TestDialogueShot:
    def test_single_dialogue_beat_produces_medium_dialogue(self):
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [{"type": "dialogue", "speaker_id": "alice", "text": "Hello."}],
                }
            ]
        )
        sl = adapter.adapt(script)
        dialogue_shots = [s for s in sl.shots if s.shot_type == ShotType.MEDIUM_DIALOGUE]
        assert len(dialogue_shots) == 1
        assert dialogue_shots[0].characters == ["alice"]
        assert dialogue_shots[0].audio_intent.vo_ref == "alice"

    def test_dialogue_duration_computed_from_text(self):
        text = "A" * 28  # 28 chars / 14 = 2.0 s
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [{"type": "dialogue", "speaker_id": "a", "text": text}],
                }
            ]
        )
        sl = adapter.adapt(script)
        d_shot = next(s for s in sl.shots if s.shot_type == ShotType.MEDIUM_DIALOGUE)
        assert d_shot.duration_seconds == pytest.approx(2.0, abs=0.01)

    def test_dialogue_duration_min_cap(self):
        """Very short line (1 char) should be clamped to MIN_DIALOGUE_DUR."""
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [{"type": "dialogue", "speaker_id": "a", "text": "K"}],
                }
            ]
        )
        sl = adapter.adapt(script)
        d_shot = next(s for s in sl.shots if s.shot_type == ShotType.MEDIUM_DIALOGUE)
        assert d_shot.duration_seconds == MIN_DIALOGUE_DUR

    def test_dialogue_duration_max_cap(self):
        """Very long line should be clamped to MAX_DIALOGUE_DUR."""
        text = "x" * 500  # 500 chars >> 12.0 s cap
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [{"type": "dialogue", "speaker_id": "a", "text": text}],
                }
            ]
        )
        sl = adapter.adapt(script)
        d_shot = next(s for s in sl.shots if s.shot_type == ShotType.MEDIUM_DIALOGUE)
        assert d_shot.duration_seconds == MAX_DIALOGUE_DUR

    def test_same_speaker_back_to_back_no_reaction(self):
        """No REACTION shot when the same character speaks consecutively."""
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [
                        {"type": "dialogue", "speaker_id": "alice", "text": "First line."},
                        {"type": "dialogue", "speaker_id": "alice", "text": "Second line."},
                    ],
                }
            ]
        )
        sl = adapter.adapt(script)
        reaction_shots = [s for s in sl.shots if s.shot_type == ShotType.REACTION]
        assert reaction_shots == []


# ---------------------------------------------------------------------------
# REACTION shot
# ---------------------------------------------------------------------------


class TestReactionShot:
    def test_speaker_change_inserts_reaction(self):
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [
                        {"type": "dialogue", "speaker_id": "alice", "text": "Hi."},
                        {"type": "dialogue", "speaker_id": "bob", "text": "Hello."},
                    ],
                }
            ]
        )
        sl = adapter.adapt(script)
        reaction_shots = [s for s in sl.shots if s.shot_type == ShotType.REACTION]
        assert len(reaction_shots) == 1
        # Reaction shows the NEW speaker (bob) listening before they respond.
        assert reaction_shots[0].characters == ["bob"]

    def test_reaction_fixed_duration(self):
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [
                        {"type": "dialogue", "speaker_id": "alice", "text": "Hi."},
                        {"type": "dialogue", "speaker_id": "bob", "text": "Hello."},
                    ],
                }
            ]
        )
        sl = adapter.adapt(script)
        reaction = next(s for s in sl.shots if s.shot_type == ShotType.REACTION)
        assert reaction.duration_seconds == 1.5

    def test_reaction_appears_before_new_speaker(self):
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [
                        {"type": "dialogue", "speaker_id": "alice", "text": "Hi."},
                        {"type": "dialogue", "speaker_id": "bob", "text": "Hello."},
                    ],
                }
            ]
        )
        sl = adapter.adapt(script)
        types = [s.shot_type for s in sl.shots]
        reaction_idx = types.index(ShotType.REACTION)
        # The MEDIUM_DIALOGUE for bob must come AFTER the reaction.
        bob_dialogue_idx = next(
            i for i, s in enumerate(sl.shots) if s.shot_type == ShotType.MEDIUM_DIALOGUE
            and s.characters == ["bob"]
        )
        assert reaction_idx < bob_dialogue_idx

    def test_action_resets_speaker_tracking(self):
        """After an action beat, there should be no reaction on the next dialogue."""
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [
                        {"type": "dialogue", "speaker_id": "alice", "text": "Watch this."},
                        {"type": "action", "description": "She flips the table."},
                        # After action, bob speaks. prev_speaker is None → no reaction.
                        {"type": "dialogue", "speaker_id": "bob", "text": "Wow."},
                    ],
                }
            ]
        )
        sl = adapter.adapt(script)
        reaction_shots = [s for s in sl.shots if s.shot_type == ShotType.REACTION]
        assert reaction_shots == []


# ---------------------------------------------------------------------------
# CLOSE_UP_EMOTIONAL shot
# ---------------------------------------------------------------------------


class TestEmotionalShot:
    def test_emotional_tag_on_dialogue_appends_close_up(self):
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [
                        {
                            "type": "dialogue",
                            "speaker_id": "alice",
                            "text": "I love you.",
                            "emotional_tag": "love",
                        }
                    ],
                }
            ]
        )
        sl = adapter.adapt(script)
        close_ups = [s for s in sl.shots if s.shot_type == ShotType.CLOSE_UP_EMOTIONAL]
        assert len(close_ups) == 1
        assert close_ups[0].expressions == "love"
        assert close_ups[0].characters == ["alice"]
        assert close_ups[0].audio_intent.music_mood == "romantic"

    def test_emotional_tag_on_action_appends_close_up(self):
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "EXT. CLIFF",
                    "time_of_day": "DUSK",
                    "beats": [
                        {
                            "type": "action",
                            "description": "She jumps.",
                            "emotional_tag": "fear",
                        }
                    ],
                }
            ]
        )
        sl = adapter.adapt(script)
        close_ups = [s for s in sl.shots if s.shot_type == ShotType.CLOSE_UP_EMOTIONAL]
        assert len(close_ups) == 1
        assert close_ups[0].expressions == "fear"
        assert close_ups[0].audio_intent.music_mood == "suspense"

    def test_no_emotional_tag_no_close_up(self):
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [{"type": "dialogue", "speaker_id": "a", "text": "Plain line."}],
                }
            ]
        )
        sl = adapter.adapt(script)
        close_ups = [s for s in sl.shots if s.shot_type == ShotType.CLOSE_UP_EMOTIONAL]
        assert close_ups == []

    def test_emotional_close_up_fixed_duration(self):
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [
                        {
                            "type": "dialogue",
                            "speaker_id": "a",
                            "text": "So sad.",
                            "emotional_tag": "sadness",
                        }
                    ],
                }
            ]
        )
        sl = adapter.adapt(script)
        cu = next(s for s in sl.shots if s.shot_type == ShotType.CLOSE_UP_EMOTIONAL)
        assert cu.duration_seconds == 2.0

    def test_close_up_follows_dialogue_shot(self):
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [
                        {
                            "type": "dialogue",
                            "speaker_id": "a",
                            "text": "Joy!",
                            "emotional_tag": "joy",
                        }
                    ],
                }
            ]
        )
        sl = adapter.adapt(script)
        types = [s.shot_type for s in sl.shots]
        dialogue_idx = types.index(ShotType.MEDIUM_DIALOGUE)
        close_up_idx = types.index(ShotType.CLOSE_UP_EMOTIONAL)
        assert close_up_idx == dialogue_idx + 1


# ---------------------------------------------------------------------------
# ACTION_BEAT shot
# ---------------------------------------------------------------------------


class TestActionBeatShot:
    def test_action_beat_shot_type(self):
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "EXT. FIELD",
                    "time_of_day": "DAY",
                    "beats": [{"type": "action", "description": "The car crashes."}],
                }
            ]
        )
        sl = adapter.adapt(script)
        action_shots = [s for s in sl.shots if s.shot_type == ShotType.ACTION_BEAT]
        assert len(action_shots) == 1
        assert action_shots[0].action_beat == "The car crashes."

    def test_action_duration_word_count(self):
        # 4 words → 4/2.0 = 2.0 → max(2.0, 2.0) = 2.0
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [{"type": "action", "description": "She walks away slowly."}],
                }
            ]
        )
        sl = adapter.adapt(script)
        action = next(s for s in sl.shots if s.shot_type == ShotType.ACTION_BEAT)
        # "She walks away slowly." = 4 words → 4/2.0 = 2.0
        assert action.duration_seconds == pytest.approx(2.0, abs=0.01)

    def test_action_duration_min_cap(self):
        """Single-word action → clamped to MIN_ACTION_DUR."""
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [{"type": "action", "description": "Bang."}],
                }
            ]
        )
        sl = adapter.adapt(script)
        action = next(s for s in sl.shots if s.shot_type == ShotType.ACTION_BEAT)
        assert action.duration_seconds == MIN_ACTION_DUR

    def test_action_duration_max_cap(self):
        """Very long action description → clamped to MAX_ACTION_DUR."""
        description = " ".join(["run"] * 100)
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [{"type": "action", "description": description}],
                }
            ]
        )
        sl = adapter.adapt(script)
        action = next(s for s in sl.shots if s.shot_type == ShotType.ACTION_BEAT)
        assert action.duration_seconds == MAX_ACTION_DUR


# ---------------------------------------------------------------------------
# ShotList totals and metadata
# ---------------------------------------------------------------------------


class TestShotListMetadata:
    def test_total_duration_is_sum_of_shots(self):
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [],
                }
            ]
        )
        sl = adapter.adapt(script)
        expected = sum(s.duration_seconds for s in sl.shots)
        assert sl.total_duration_seconds == pytest.approx(expected, abs=0.001)

    def test_script_id_propagated(self):
        script = _make_script([{"scene_id": "s01", "location": "A", "time_of_day": "DAY", "beats": []}])
        sl = adapter.adapt(script)
        assert sl.script_id == script.script_id

    def test_shotlist_id_is_uuid_string(self):
        script = _make_script([{"scene_id": "s01", "location": "A", "time_of_day": "DAY", "beats": []}])
        sl = adapter.adapt(script)
        assert isinstance(sl.shotlist_id, str)
        assert len(sl.shotlist_id) == 36  # UUID4 with hyphens

    def test_shot_ids_are_stable_and_sequential(self):
        script = _make_script(
            [
                {
                    "scene_id": "s01",
                    "location": "INT. X",
                    "time_of_day": "DAY",
                    "beats": [
                        {"type": "dialogue", "speaker_id": "a", "text": "Hi."},
                    ],
                }
            ]
        )
        sl = adapter.adapt(script)
        shot_ids = [s.shot_id for s in sl.shots]
        assert shot_ids[0] == "s01_000"
        assert shot_ids[1] == "s01_001"
