from __future__ import annotations

import argparse
import json
from pathlib import Path

import evidence_atom_inventory_lite as current_atoms
from hpfa.modules.core.match_local_identity_candidates_lite.src import (
    match_local_identity_candidates as identity,
)

ROOT = Path(__file__).resolve().parent


def _bridge_team_subject_candidates(evidence: dict) -> tuple[dict, int, int]:
    """Adapt current TEAM atoms without mutating the upstream Evidence Atom artifact.

    Current TEAM surfaces may have no direct team field while the exact visible
    subject is preserved in ``code_raw`` as ``<team subject> - <raw label>``.
    Promote that prefix only when the raw-label suffix matches exactly. This is
    a match-local identity candidate bridge, not provider/global identity truth.
    """
    bridged = dict(evidence)
    bridged_atoms: list[dict] = []
    applied = 0
    review = 0

    for atom in list(evidence.get("evidence_atoms") or []):
        if not isinstance(atom, dict):
            bridged_atoms.append(atom)
            continue
        row = dict(atom)
        is_team = row.get("source_role") == "TEAM_SURFACE_CANDIDATE"
        is_admin = bool(row.get("identity_not_applicable")) or row.get("atom_class") == "ADMINISTRATIVE_ATOM"
        has_team = bool(str(row.get("team_raw_candidate") or "").strip())
        if is_team and not is_admin and not has_team:
            prefix = identity._exact_subject_prefix(row.get("code_raw"), row.get("raw_label"))
            if prefix:
                row["team_raw_candidate"] = prefix
                row["team_subject_bridge"] = "EXACT_CODE_PREFIX_CANDIDATE"
                applied += 1
            else:
                row["team_subject_bridge"] = "EXACT_CODE_PREFIX_UNAVAILABLE"
                review += 1
        bridged_atoms.append(row)

    bridged["evidence_atoms"] = bridged_atoms
    return bridged, applied, review


def _decorate_current_context(payload: dict, evidence: dict, *, bridge_applied: int, bridge_review: int) -> dict:
    payload["current_evidence_atom_status"] = evidence.get("status")
    payload["current_evidence_atom_count"] = evidence.get("evidence_atom_count")
    payload["current_evidence_atom_pass_count"] = evidence.get("evidence_atom_pass_count")
    payload["current_evidence_atom_review_required_count"] = evidence.get(
        "evidence_atom_review_required_count"
    )
    payload["current_content_source_role_bridge_status"] = evidence.get(
        "current_content_source_role_bridge_status"
    )
    payload["team_subject_code_prefix_bridge_mode"] = "EXACT_SUFFIX_ONLY_WHEN_TEAM_FIELD_ABSENT"
    payload["team_subject_code_prefix_bridge_applied_count"] = bridge_applied
    payload["team_subject_code_prefix_bridge_review_count"] = bridge_review
    return payload


def _build_identity_payload(evidence: dict) -> dict:
    bridged, applied, review = _bridge_team_subject_candidates(evidence)
    payload = identity.build_match_local_identity_candidates(bridged)
    return _decorate_current_context(
        payload,
        evidence,
        bridge_applied=applied,
        bridge_review=review,
    )


def _failure_from_evidence(evidence: dict) -> dict:
    return {
        "module_id": identity.MODULE_ID,
        "status": "FAIL_CLOSED",
        "module_status": "FAIL_CLOSED",
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": evidence.get("match_surface_binding_id"),
        "evidence_atom_count": evidence.get("evidence_atom_count", 0),
        "identity_binding_record_count": 0,
        "team_identity_candidate_count": 0,
        "actor_identity_candidate_count": 0,
        "identity_candidate_bound_atom_count": 0,
        "identity_not_applicable_atom_count": 0,
        "identity_review_required_atom_count": 0,
        "decision_state_counts": {},
        "team_identity_candidates": [],
        "actor_identity_candidates": [],
        "identity_bindings": [],
        "hard_block_hits": ["current_evidence_atom_fail_closed"],
        "review_hits": [],
        "active_match_evidence_pass": False,
        "identity_scope": "MATCH_LOCAL_CANDIDATE_ONLY",
        "identity_truth_admitted": False,
        "global_roster_identity_admitted": False,
        "cross_match_identity_admitted": False,
        "validated_team_identity": False,
        "validated_player_identity": False,
        "validated_event_identity": False,
        "physical_action_identity_truth": False,
        "event_instance_allowed": False,
        "cross_role_fusion_allowed": False,
        "independent_source_vote_allowed": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": identity.CLAIM_CEILING,
        "current_evidence_atom_status": evidence.get("status"),
        "team_subject_code_prefix_bridge_mode": "EXACT_SUFFIX_ONLY_WHEN_TEAM_FIELD_ABSENT",
        "team_subject_code_prefix_bridge_applied_count": 0,
        "team_subject_code_prefix_bridge_review_count": 0,
    }


def build_from_existing_evidence(evidence: dict) -> dict:
    """Build match-local identity candidates from the current Evidence Atom payload.

    This is an orchestration adapter over the existing identity producer. It
    preserves candidate-only semantics and avoids recomputing upstream evidence.
    """
    if evidence.get("status") == "FAIL_CLOSED":
        return _failure_from_evidence(evidence)
    return _build_identity_payload(evidence)


def runtime_build_report(input_dir: str | Path) -> dict:
    evidence = current_atoms.runtime_build_report(input_dir)
    return build_from_existing_evidence(evidence)


def write_outputs_from_existing_evidence(evidence: dict, out_dir: str | Path) -> dict:
    output = identity.validate_output_root(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    payload = build_from_existing_evidence(evidence)
    paths = identity.write_outputs(payload, output)
    payload["outputs"] = {key: str(path) for key, path in paths.items()}
    return payload


def runtime_write_outputs(input_dir: str | Path, out_dir: str | Path) -> dict:
    output = identity.validate_output_root(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    evidence = current_atoms.runtime_write_outputs(input_dir, output)
    return write_outputs_from_existing_evidence(evidence, output)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="HPFA current Evidence Atom to Match-Local Identity migration adapter"
    )
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    payload = runtime_write_outputs(args.input_dir, args.out_dir)
    print(
        json.dumps(
            {
                "status": payload.get("status"),
                "current_evidence_atom_status": payload.get("current_evidence_atom_status"),
                "evidence_atom_count": payload.get("evidence_atom_count"),
                "team_identity_candidate_count": payload.get("team_identity_candidate_count"),
                "actor_identity_candidate_count": payload.get("actor_identity_candidate_count"),
                "identity_candidate_bound_atom_count": payload.get("identity_candidate_bound_atom_count"),
                "team_candidate_bound_atom_count": payload.get("team_candidate_bound_atom_count"),
                "actor_candidate_bound_atom_count": payload.get("actor_candidate_bound_atom_count"),
                "identity_not_applicable_atom_count": payload.get("identity_not_applicable_atom_count"),
                "identity_review_required_atom_count": payload.get("identity_review_required_atom_count"),
                "team_subject_code_prefix_bridge_applied_count": payload.get(
                    "team_subject_code_prefix_bridge_applied_count"
                ),
                "team_subject_code_prefix_bridge_review_count": payload.get(
                    "team_subject_code_prefix_bridge_review_count"
                ),
                "decision_state_counts": payload.get("decision_state_counts") or {},
                "hard_block_hits": payload.get("hard_block_hits") or [],
                "review_hits": payload.get("review_hits") or [],
                "canonical_event_count": "UNKNOWN",
                "production_release": False,
                "outputs": payload.get("outputs") or {},
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
