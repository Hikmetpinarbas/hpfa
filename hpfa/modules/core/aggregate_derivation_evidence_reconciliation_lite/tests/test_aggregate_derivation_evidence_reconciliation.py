from __future__ import annotations

import copy
import pathlib
import sys

import pytest

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import aggregate_derivation_evidence_reconciliation as mod

BINDING = "msb_test_binding"
SUCCESS_REQ = {
    "source_roles": ["PLAYER_SURFACE_CANDIDATE"],
    "normalized_label": "passes accurate",
    "action_family_candidate": "PASS",
    "outcome_candidate": "SUCCESS",
}
FAIL_REQ = {
    "source_roles": ["PLAYER_SURFACE_CANDIDATE"],
    "normalized_label": "inaccurate passes",
    "action_family_candidate": "PASS",
    "outcome_candidate": "FAILURE",
}


def atom(eid, label, outcome, *, family="PASS", role="PLAYER_SURFACE_CANDIDATE", mapping="EXACT_REVIEWED_CANDIDATE"):
    return {
        "evidence_atom_id": eid,
        "match_surface_binding_id": BINDING,
        "source_role": role,
        "atom_class": "ACTION_ANCHOR_ATOM",
        "atom_status": "PASS",
        "normalized_label": label,
        "action_family_candidates": [family],
        "outcome_candidates": [outcome],
        "mapping_statuses": [mapping],
    }


def binding(eid):
    return {
        "evidence_atom_id": eid,
        "match_surface_binding_id": BINDING,
        "source_role": "PLAYER_SURFACE_CANDIDATE",
        "decision_state": "ACTOR_IDENTITY_CANDIDATE_BOUND",
        "team_identity_candidate_id": "teamc_1",
        "actor_identity_candidate_id": "actorc_1",
    }


def payloads(*, success=1, failure=1, raw=0.5, value_kind="number", fmt="0%"):
    atoms = [atom(f"ea_s{i}", "passes accurate", "SUCCESS") for i in range(success)]
    atoms += [atom(f"ea_f{i}", "inaccurate passes", "FAILURE") for i in range(failure)]
    ids = [binding(a["evidence_atom_id"]) for a in atoms]
    common = {"status": "PASS", "hard_block_hits": [], "canonical_event_count": "UNKNOWN", "production_release": False}
    xlsx = common | {
        "module_id": "xlsx_entity_metric_row_projection_lite_v1",
        "files": [{"sheets": [{"rows": [{
            "row_projection_id": "xrp_1",
            "relative_path": "players.xlsx",
            "source_sha256": "a" * 64,
            "source_role": "PLAYER_SURFACE_CANDIDATE",
            "sheet_name": "Players",
            "source_row_number": 2,
            "identity_candidates": {"team_raw_candidate": "Team A", "player_raw_candidate": "Player One"},
            "metric_values": {"passes_accurate_percent": {
                "raw_metric_label": "Passes accurate, %",
                "raw_value": raw,
                "value_kind": value_kind,
                "number_format": fmt,
                "value_admitted": True,
            }},
        }]}]}],
    }
    evidence = common | {
        "module_id": "evidence_atom_inventory_lite_v1",
        "match_surface_binding_id": BINDING,
        "evidence_atoms": atoms,
    }
    identity = common | {
        "module_id": "match_local_identity_candidates_lite_v1",
        "match_surface_binding_id": BINDING,
        "team_identity_candidates": [{
            "team_identity_candidate_id": "teamc_1",
            "match_surface_binding_id": BINDING,
            "team_normalized_key": "team_a",
            "decision_state": "TEAM_IDENTITY_CANDIDATE_BOUND",
        }],
        "actor_identity_candidates": [{
            "actor_identity_candidate_id": "actorc_1",
            "team_identity_candidate_id": "teamc_1",
            "match_surface_binding_id": BINDING,
            "team_normalized_key": "team_a",
            "actor_normalized_key": "player_one",
            "decision_state": "ACTOR_IDENTITY_CANDIDATE_BOUND",
        }],
        "identity_bindings": ids,
    }
    semantics = common | {
        "module_id": "provider_label_value_semantics_lite_v1",
        "provider_label_records": [
            {"normalized_label": "passes accurate", "surface_row_volume": 9999},
            {"normalized_label": "inaccurate passes", "surface_row_volume": 9999},
        ],
    }
    alignment = common | {
        "module_id": "aggregate_definition_alignment_lite_v1",
        "alignment_rows": [{
            "definition_id": "sportsbase_pass_completion_candidate_v1",
            "semantic_support": [
                {"requirement": SUCCESS_REQ, "match_count": 1},
                {"requirement": FAIL_REQ, "match_count": 1},
            ],
        }],
    }
    registry = {"definitions": [{
        "definition_id": "sportsbase_pass_completion_candidate_v1",
        "provider_id": "sportsbase",
        "provider_version": "provider_definition_unverified",
        "source_roles": ["PLAYER_SURFACE_CANDIDATE"],
        "aggregate_label": "Passes accurate, %",
        "required_occurrence_semantics": [SUCCESS_REQ, FAIL_REQ],
        "definition_evidence_status": "PROVIDER_DEFINITION_REQUIRED",
        "independence_status": "NON_INDEPENDENT_SAME_PROVIDER",
    }]}
    return xlsx, evidence, identity, semantics, alignment, registry


def run(ps):
    return mod.build_reconciliation(*ps)


def rec(out):
    assert len(out["reconciliation_records"]) == 1
    return out["reconciliation_records"][0]


def test_exact_numerator_denominator_semantics_admitted():
    r = rec(run(payloads()))
    assert r["numerator_observed_candidate"] == 1
    assert r["denominator_observed_candidate"] == 2
    assert r["g16_recheck_admission"] == "G16_RECHECK_ADMITTED"


def test_visible_percent_precision_reproduces_without_epsilon():
    r = rec(run(payloads(success=2, failure=1, raw=0.67, fmt="0%")))
    assert r["observed_arithmetic_status"] == "ARITHMETIC_CANDIDATE_REPRODUCED"
    assert r["arithmetic_comparison_method"] == "OBSERVED_SIMPLE_PERCENT_DISPLAY_PRECISION"


def test_unsupported_format_does_not_invent_tolerance():
    r = rec(run(payloads(success=2, failure=1, raw=0.67, fmt="General")))
    assert r["observed_arithmetic_status"] == "ARITHMETIC_CANDIDATE_MISMATCH"
    assert r["arithmetic_comparison_method"] == "UNSUPPORTED_DISPLAY_FORMAT_NO_TOLERANCE"


def test_wrong_action_family_rejected():
    ps = list(payloads())
    ps[1]["evidence_atoms"][0]["action_family_candidates"] = ["SHOT"]
    r = rec(run(tuple(ps)))
    assert r["semantic_near_miss_record_ids"]
    assert r["g16_recheck_admission"] == "G16_RECHECK_BLOCKED"


def test_wrong_outcome_rejected():
    ps = list(payloads())
    ps[1]["evidence_atoms"][0]["outcome_candidates"] = ["FAILURE"]
    r = rec(run(tuple(ps)))
    assert r["semantic_near_miss_record_ids"]
    assert r["g16_recheck_admission"] == "G16_RECHECK_BLOCKED"


def test_wrong_source_role_rejected():
    ps = list(payloads())
    ps[1]["evidence_atoms"][0]["source_role"] = "TEAM_SURFACE_CANDIDATE"
    r = rec(run(tuple(ps)))
    assert r["semantic_near_miss_record_ids"]
    assert r["g16_recheck_admission"] == "G16_RECHECK_BLOCKED"


def test_wrong_entity_blocks_scope():
    ps = list(payloads())
    ps[0]["files"][0]["sheets"][0]["rows"][0]["identity_candidates"]["player_raw_candidate"] = "Different Player"
    r = rec(run(tuple(ps)))
    assert r["scope_alignment_status"] == "SCOPE_ALIGNMENT_REVIEW_REQUIRED"
    assert r["g16_recheck_admission"] == "G16_RECHECK_BLOCKED"


def test_ambiguous_entity_blocks_scope():
    ps = list(payloads())
    duplicate = copy.deepcopy(ps[2]["actor_identity_candidates"][0])
    duplicate["actor_identity_candidate_id"] = "actorc_2"
    ps[2]["actor_identity_candidates"].append(duplicate)
    assert rec(run(tuple(ps)))["scope_alignment_status"] == "SCOPE_ALIGNMENT_REVIEW_REQUIRED"


def test_provider_id_or_shirt_number_cannot_rescue_missing_name():
    ps = list(payloads())
    row = ps[0]["files"][0]["sheets"][0]["rows"][0]
    row["identity_candidates"]["player_raw_candidate"] = None
    row["identity_candidates"]["shirt_number_raw_candidate"] = 10
    r = rec(run(tuple(ps)))
    assert r["actor_identity_candidate_id"] is None
    assert r["g16_recheck_admission"] == "G16_RECHECK_BLOCKED"


def test_wrong_match_binding_fails_closed():
    ps = list(payloads())
    ps[1]["evidence_atoms"][0]["match_surface_binding_id"] = "msb_wrong"
    out = run(tuple(ps))
    assert out["status"] == "FAIL_CLOSED"
    assert any("evidence_atom_match_surface_binding_mismatch" in x for x in out["hard_block_hits"])


def test_missing_denominator_semantic_support_blocks_recheck():
    ps = list(payloads())
    ps[4]["alignment_rows"][0]["semantic_support"][1]["match_count"] = 0
    r = rec(run(tuple(ps)))
    assert r["derivation_lineage_status"] == "DERIVATION_LINEAGE_REVIEW_REQUIRED"
    assert r["g16_recheck_admission"] == "G16_RECHECK_BLOCKED"


def test_zero_denominator_dash_is_not_computable_but_reviewable():
    r = rec(run(payloads(success=0, failure=0, raw="-", value_kind="string")))
    assert r["zero_denominator_state"] == "ZERO_DENOMINATOR"
    assert r["observed_arithmetic_status"] == "ARITHMETIC_CANDIDATE_NOT_COMPUTABLE"
    assert r["g16_recheck_admission"] == "G16_RECHECK_ADMITTED"


def test_zero_denominator_numeric_zero_still_not_computable():
    r = rec(run(payloads(success=0, failure=0, raw=0, value_kind="number")))
    assert r["zero_denominator_state"] == "ZERO_DENOMINATOR"
    assert r["observed_arithmetic_status"] == "ARITHMETIC_CANDIDATE_NOT_COMPUTABLE"


def test_numeric_zero_is_not_missing():
    r = rec(run(payloads(success=1, failure=1, raw=0, value_kind="number")))
    assert r["aggregate_value_observed"] == 0
    assert r["observed_arithmetic_status"] == "ARITHMETIC_CANDIDATE_MISMATCH"


def test_missing_value_is_not_numeric_zero():
    r = rec(run(payloads(success=1, failure=1, raw=None, value_kind="blank")))
    assert r["aggregate_value_observed"] is None
    assert r["observed_arithmetic_status"] == "ARITHMETIC_CANDIDATE_NOT_COMPUTABLE"


def test_duplicate_evidence_atom_id_fails_closed():
    ps = list(payloads())
    ps[1]["evidence_atoms"].append(copy.deepcopy(ps[1]["evidence_atoms"][0]))
    out = run(tuple(ps))
    assert out["status"] == "FAIL_CLOSED"
    assert any("duplicate_evidence_atom_id" in x for x in out["hard_block_hits"])


def test_same_provider_is_not_promoted_to_independent_confirmation():
    out = run(payloads())
    assert rec(out)["independence_status"] == "NON_INDEPENDENT_SAME_PROVIDER"
    assert out["same_provider_is_independent_confirmation"] is False


def test_label_profile_volume_cannot_inflate_entity_counts():
    r = rec(run(payloads()))
    assert r["numerator_observed_candidate"] == 1
    assert r["denominator_observed_candidate"] == 2


def test_provider_definition_remains_separate_from_arithmetic():
    r = rec(run(payloads()))
    assert r["observed_arithmetic_status"] == "ARITHMETIC_CANDIDATE_REPRODUCED"
    assert r["provider_definition_evidence_status"] == "PROVIDER_DEFINITION_REQUIRED"


def test_nested_phone_output_rejected():
    with pytest.raises(ValueError, match="nested_phone_output_directory_rejected"):
        mod.validate_out("/sdcard/Download/HPFA/nested")


def test_active_match_path_contract():
    assert mod._active_match_path(pathlib.Path("/tmp/runtime/active_single_match/current"))
    assert not mod._active_match_path(pathlib.Path("/tmp/runtime/active_single_match/other"))


def test_no_sample_match_identity_leak():
    text = (SRC / "aggregate_derivation_evidence_reconciliation.py").read_text(encoding="utf-8").casefold()
    for forbidden in ("australia 2-0 turkey", "hakan calhanoglu", "mohamed toure"):
        assert forbidden not in text
