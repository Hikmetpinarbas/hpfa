from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "episode_feature_vector_lite" / "src"
TESTS = ROOT / "hpfa" / "modules" / "core" / "episode_feature_vector_lite" / "tests"
sys.path.insert(0, str(SRC))
sys.path.insert(0, str(TESTS))

from episode_feature_vector import build_episode_feature_vectors
from test_episode_feature_vector import _payloads


@pytest.mark.parametrize("invalid_duration", [None, "bad", -1, float("nan"), float("inf"), float("-inf")])
def test_invalid_episode_duration_fails_closed(invalid_duration: object) -> None:
    episode, semantics = _payloads()
    episode = copy.deepcopy(episode)
    episode["episode_candidates"][0]["duration_candidate_seconds"] = invalid_duration

    result = build_episode_feature_vectors(episode, semantics)

    assert result["status"] == "FAIL_CLOSED"
    assert result["feature_assignment_complete"] is False
    assert "episode_duration_invalid:ep_1" in result["hard_block_hits"]
    assert result["episode_feature_vectors"] == []
    assert result["canonical_event_count"] == "UNKNOWN"
    assert result["production_release"] is False


def test_exact_zero_duration_remains_valid_point_episode() -> None:
    episode, semantics = _payloads()
    result = build_episode_feature_vectors(episode, semantics)

    second = result["episode_feature_vectors"][1]
    assert second["duration_seconds_candidate"] == 0.0
    assert second["density_feature_status"] == "NOT_APPLICABLE_ZERO_DURATION"
    assert second["eligible_visible_action_candidate_density_per_minute"] is None
