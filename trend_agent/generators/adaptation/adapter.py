"""
ScriptToShotListAdapter: converts Script.json → ShotList.json.

Phase 0 implementation — rules-based, no AI, no media lookup.
All shot boundaries and durations are derived purely from the Script's
scene/beat structure using the template library in shot_templates.py.

Pipeline flow per §8:
    Script
        → Scene Breakdown  (one scene at a time, in order)
        → Shot Planner     (template selection per beat type)
        → Emotional Tagger (CLOSE_UP_EMOTIONAL appended when tag present)
        → Timing Estimator (duration computed from text length / word count)
        → ShotList Finalizer (timing_lock_hash computed and locked)

Determinism guarantee:
    Given identical Script input, the adapter produces identical ShotList
    output (excluding shotlist_id, which is a new UUID each run).
    timing_lock_hash is stable across all reruns.

Shot boundary rules:
    • Every scene opens with one ESTABLISHING shot.
    • Each DIALOGUE beat → MEDIUM_DIALOGUE shot on the speaker.
    • Speaker change → REACTION shot (next speaker shown listening) inserted
      before the new speaker's MEDIUM_DIALOGUE.
    • Emotional tag on any beat → CLOSE_UP_EMOTIONAL shot appended after.
    • Each ACTION beat → ACTION_BEAT shot; resets speaker-change tracking.
"""

from __future__ import annotations

import uuid

from .models import (
    ActionBeat,
    AudioIntent,
    DialogueBeat,
    Scene,
    Script,
    Shot,
    ShotList,
    ShotType,
)
from .shot_templates import TEMPLATES, resolve_music_mood
from .timing import compute_timing_lock_hash


class ScriptToShotListAdapter:
    """
    Converts a validated Script into a locked ShotList.

    Usage::

        from trend_agent.generators.adaptation import ScriptToShotListAdapter, validate_script

        raw = json.load(open("script.json"))
        script = validate_script(raw)
        adapter = ScriptToShotListAdapter()
        shotlist = adapter.adapt(script)
        print(shotlist.timing_lock_hash)
    """

    def adapt(self, script: Script) -> ShotList:
        """
        Convert a validated Script into a timing-locked ShotList.

        Args:
            script: A validated Script Pydantic model.

        Returns:
            ShotList with timing_lock_hash set and total_duration_seconds summed.
        """
        shots: list[Shot] = []
        for scene in script.scenes:
            shots.extend(self._process_scene(scene))

        timing_lock_hash = compute_timing_lock_hash(shots)
        total_duration = round(sum(s.duration_seconds for s in shots), 3)

        return ShotList(
            schema_version="1.0.0",
            shotlist_id=str(uuid.uuid4()),
            script_id=script.script_id,
            timing_lock_hash=timing_lock_hash,
            total_duration_seconds=total_duration,
            shots=shots,
        )

    # ------------------------------------------------------------------
    # Scene breakdown
    # ------------------------------------------------------------------

    def _process_scene(self, scene: Scene) -> list[Shot]:
        """
        Convert one Scene into an ordered list of Shots.

        Opens every scene with an ESTABLISHING shot, then processes
        each beat in order applying template selection rules.
        """
        shots: list[Shot] = []
        env_notes = f"{scene.location} - {scene.time_of_day.value}"
        shot_index = 0

        def next_shot_id() -> str:
            nonlocal shot_index
            sid = f"{scene.scene_id}_{shot_index:03d}"
            shot_index += 1
            return sid

        # Every scene opens with a wide establishing shot.
        shots.append(self._make_establishing(scene, next_shot_id(), env_notes))

        prev_speaker: str | None = None

        for beat in scene.beats:
            if isinstance(beat, DialogueBeat):
                # Insert a REACTION shot when the speaker changes.
                # The reaction shows the *new* speaker listening before
                # they begin speaking — standard continuity cut convention.
                if prev_speaker is not None and prev_speaker != beat.speaker_id:
                    shots.append(
                        self._make_reaction(
                            scene_id=scene.scene_id,
                            shot_id=next_shot_id(),
                            env_notes=env_notes,
                            characters=[beat.speaker_id],
                        )
                    )

                shots.append(
                    self._make_dialogue(beat, scene.scene_id, next_shot_id(), env_notes)
                )

                # Emotional tag → insert close-up immediately after dialogue.
                if beat.emotional_tag:
                    shots.append(
                        self._make_emotional(
                            scene_id=scene.scene_id,
                            shot_id=next_shot_id(),
                            env_notes=env_notes,
                            characters=[beat.speaker_id],
                            emotional_tag=beat.emotional_tag,
                        )
                    )

                prev_speaker = beat.speaker_id

            elif isinstance(beat, ActionBeat):
                shots.append(
                    self._make_action(beat, scene.scene_id, next_shot_id(), env_notes)
                )

                if beat.emotional_tag:
                    shots.append(
                        self._make_emotional(
                            scene_id=scene.scene_id,
                            shot_id=next_shot_id(),
                            env_notes=env_notes,
                            characters=[],
                            emotional_tag=beat.emotional_tag,
                        )
                    )

                # Action beats break the dialogue speaker-change tracking.
                prev_speaker = None

        return shots

    # ------------------------------------------------------------------
    # Shot factories — one per template type
    # ------------------------------------------------------------------

    def _make_establishing(self, scene: Scene, shot_id: str, env_notes: str) -> Shot:
        tmpl = TEMPLATES[ShotType.ESTABLISHING]
        return Shot(
            shot_id=shot_id,
            scene_id=scene.scene_id,
            shot_type=ShotType.ESTABLISHING,
            camera_framing=tmpl.camera_framing,
            camera_movement=tmpl.camera_movement,
            duration_seconds=tmpl.fixed_duration(),
            characters=[],
            expressions=None,
            environment_notes=env_notes,
            action_beat=None,
            audio_intent=AudioIntent(),
        )

    def _make_dialogue(
        self,
        beat: DialogueBeat,
        scene_id: str,
        shot_id: str,
        env_notes: str,
    ) -> Shot:
        tmpl = TEMPLATES[ShotType.MEDIUM_DIALOGUE]
        return Shot(
            shot_id=shot_id,
            scene_id=scene_id,
            shot_type=ShotType.MEDIUM_DIALOGUE,
            camera_framing=tmpl.camera_framing,
            camera_movement=tmpl.camera_movement,
            duration_seconds=tmpl.duration_for_dialogue(beat.text),
            characters=[beat.speaker_id],
            expressions=beat.emotional_tag,
            environment_notes=env_notes,
            action_beat=None,
            audio_intent=AudioIntent(
                vo_ref=beat.speaker_id,
                music_mood=resolve_music_mood(beat.emotional_tag),
            ),
        )

    def _make_reaction(
        self,
        scene_id: str,
        shot_id: str,
        env_notes: str,
        characters: list[str],
    ) -> Shot:
        tmpl = TEMPLATES[ShotType.REACTION]
        return Shot(
            shot_id=shot_id,
            scene_id=scene_id,
            shot_type=ShotType.REACTION,
            camera_framing=tmpl.camera_framing,
            camera_movement=tmpl.camera_movement,
            duration_seconds=tmpl.fixed_duration(),
            characters=characters,
            expressions=None,
            environment_notes=env_notes,
            action_beat=None,
            audio_intent=AudioIntent(),
        )

    def _make_action(
        self,
        beat: ActionBeat,
        scene_id: str,
        shot_id: str,
        env_notes: str,
    ) -> Shot:
        tmpl = TEMPLATES[ShotType.ACTION_BEAT]
        return Shot(
            shot_id=shot_id,
            scene_id=scene_id,
            shot_type=ShotType.ACTION_BEAT,
            camera_framing=tmpl.camera_framing,
            camera_movement=tmpl.camera_movement,
            duration_seconds=tmpl.duration_for_action(beat.description),
            characters=[],
            expressions=beat.emotional_tag,
            environment_notes=env_notes,
            action_beat=beat.description,
            audio_intent=AudioIntent(
                music_mood=resolve_music_mood(beat.emotional_tag),
            ),
        )

    def _make_emotional(
        self,
        scene_id: str,
        shot_id: str,
        env_notes: str,
        characters: list[str],
        emotional_tag: str,
    ) -> Shot:
        tmpl = TEMPLATES[ShotType.CLOSE_UP_EMOTIONAL]
        return Shot(
            shot_id=shot_id,
            scene_id=scene_id,
            shot_type=ShotType.CLOSE_UP_EMOTIONAL,
            camera_framing=tmpl.camera_framing,
            camera_movement=tmpl.camera_movement,
            duration_seconds=tmpl.fixed_duration(),
            characters=characters,
            expressions=emotional_tag,
            environment_notes=env_notes,
            action_beat=None,
            audio_intent=AudioIntent(
                music_mood=resolve_music_mood(emotional_tag),
            ),
        )
