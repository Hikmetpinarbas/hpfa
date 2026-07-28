from __future__ import annotations

import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
SRC = MODULE_ROOT / "src"
sys.path.insert(0, str(SRC))

from time_layers import build_visible_time_layers  # noqa: E402


def test_missing_event_mapping_returns_structured_block_not_exception():
    binding = "msb_generic_surface"
    node = {
        "selected_action_node_id": "node_without_event_mapping",
        "match_surface_binding_id": binding,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "team_identity_candidate_id": "teamc_a",
        "actor_identity_candidate_id": "actorc_a",
        "actor_identity_applicability": "APPLICABLE_BOUND_CANDIDATE",
        "period_candidate": "1",
        "start_candidate": "10.0",
        "action_family_candidates": ["PASS"],
        "canonical_event_count": "UNKNOWN",
    }

    layers, blocks = build_visible_time_layers([node], {}, binding)

    assert len(layers) == 1
    assert layers[0]["unresolved_event_consequence_context_count"] == 0
    assert blocks == ["event_consequence_mapping_missing:node_without_event_mapping"]
    assert layers[0]["canonical_event_count"] == "UNKNOWN"
