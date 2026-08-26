import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "context_action_semantics_rebind_lite" / "src"
sys.path.insert(0, str(SRC))

from context_action_semantics_rebind import _goalkeeper_opponent_shot_reference_label


def test_actual_normalized_goalkeeper_shot_reference_spellings_are_captured() -> None:
    assert _goalkeeper_opponent_shot_reference_label("shots on target") is True
    assert _goalkeeper_opponent_shot_reference_label("shots off target") is True
    assert _goalkeeper_opponent_shot_reference_label("free kick shots") is True
    assert _goalkeeper_opponent_shot_reference_label("opponent s long range shots on target") is True
    assert _goalkeeper_opponent_shot_reference_label("opponent s close range shots on target") is True


def test_goalkeeper_action_labels_are_not_mistaken_for_opponent_shot_references() -> None:
    assert _goalkeeper_opponent_shot_reference_label("shots saved") is False
    assert _goalkeeper_opponent_shot_reference_label("goal kicks") is False
