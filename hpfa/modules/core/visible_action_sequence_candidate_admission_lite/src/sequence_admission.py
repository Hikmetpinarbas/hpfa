from __future__ import annotations

try:
    from .sequence_engine import admit_visible_sequences
    from .sequence_profiles import build_sequence_profiles
except ImportError:
    from sequence_engine import admit_visible_sequences
    from sequence_profiles import build_sequence_profiles

__all__ = ["admit_visible_sequences", "build_sequence_profiles"]
