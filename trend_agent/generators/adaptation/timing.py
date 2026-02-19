"""
Timing lock hash generation for ShotList artifacts.

The timing_lock_hash is a SHA-256 digest of the canonicalized shot-timing list.
It encodes the temporal skeleton of an episode; any change to shot count,
shot ordering, or any individual duration changes the hash.

⚠️  BLOCKING INTERFACE (§38.6)
Changing the hash algorithm, canonicalization rules, or which fields are
included requires explicit cross-team approval and a coordinated rollout.
Modifying this function is NOT a non-blocking internal change.

Canonicalization rules (stability guarantees):
  1. Only shot_id and duration_seconds are included — no volatile fields
     (no shotlist_id, no script content, no timestamps).
  2. duration_seconds is rounded to 3 decimal places to eliminate
     floating-point representation drift (1.5 == 1.500 == 1.5000).
  3. Dict keys are sorted alphabetically (json sort_keys=True).
  4. No whitespace (separators=(',', ':')).
  5. ASCII encoding only (ensure_ascii=True) — locale-independent.
  6. Shot order is preserved — it encodes the timeline sequence.
"""

from __future__ import annotations

import hashlib
import json

from .models import Shot


def compute_timing_lock_hash(shots: list[Shot]) -> str:
    """
    Produce a stable SHA-256 hex digest of the shot-timing list.

    Args:
        shots: Ordered list of Shot objects (timeline order).

    Returns:
        Lowercase SHA-256 hex string, 64 characters.

    Example:
        >>> shots = [Shot(shot_id="s01_000", duration_seconds=2.5, ...)]
        >>> h = compute_timing_lock_hash(shots)
        >>> len(h)
        64
        >>> h == compute_timing_lock_hash(shots)  # deterministic
        True
    """
    canonical: list[dict] = [
        {
            # Keys will be sorted by json.dumps(sort_keys=True), but we
            # define them in alphabetical order here for readability.
            "duration_seconds": round(s.duration_seconds, 3),
            "shot_id": s.shot_id,
        }
        for s in shots  # preserve shot order — this IS the timeline
    ]

    payload: str = json.dumps(
        canonical,
        sort_keys=True,       # deterministic key ordering across Python versions
        separators=(",", ":"), # no whitespace — no formatting variation
        ensure_ascii=True,    # locale-independent encoding
    )

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
