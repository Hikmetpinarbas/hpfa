from __future__ import annotations

from copy import deepcopy
from typing import Any

MODULE_ID = "team_attribution_projection_v1"
SEMANTIC_MODULE_ID = "context_action_semantics_rebind_lite_v1"
EVIDENCE_MODULE_ID = "evidence_atom_inventory_lite_v1"
IDENTITY_MODULE_ID = "match_local_identity_candidates_lite_v1"
IDENTITY_BRIDGE_MODE = "EXACT_SUFFIX_ONLY_WHEN_TEAM_FIELD_ABSENT"
UNKNOWN_TEAM_VALUES = {"", "unknown", "none", "null"}


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _status(value: Any) -> str:
    return _clean(value).upper() or "UNKNOWN"


def _is_unknown(value: Any) -> bool:
    return _clean(value).casefold() in UNKNOWN_TEAM_VALUES


def _identity_team_candidate(binding: dict[str, Any] | None) -> str:
    if not isinstance(binding, dict):
        return ""
    subject = _clean(binding.get("team_subject_raw_candidate"))
    if not _is_unknown(subject):
        return subject
    name = _clean(binding.get("team_name_raw_candidate"))
    return "" if _is_unknown(name) else name


def _index_unique(rows: Any, key: str, label: str, blocks: list[str]) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        blocks.append(f"{label}_collection_invalid")
        return {}
    out: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            blocks.append(f"{label}_record_invalid:{index}")
            continue
        value = _clean(row.get(key))
        if not value:
            blocks.append(f"{label}_identity_missing:{index}")
            continue
        if value in out:
            blocks.append(f"{label}_identity_duplicate:{value}")
            continue
        out[value] = row
    return out


def project_team_attribution(
    semantic_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
    identity_payload: dict[str, Any],
) -> dict[str, Any]:
    """Project existing match-local team identity candidates into reviewed semantics.

    This function never parses a team name, never guesses the opponent and never
    creates an identity. It only reuses the existing evidence-atom -> match-local
    identity binding when the raw context team is unknown.
    """
    blocks: list[str] = []
    reviews: list[str] = []

    if semantic_payload.get("module_id") != SEMANTIC_MODULE_ID:
        blocks.append("semantic_module_id_mismatch")
    if evidence_payload.get("module_id") != EVIDENCE_MODULE_ID:
        blocks.append("evidence_module_id_mismatch")
    if identity_payload.get("module_id") != IDENTITY_MODULE_ID:
        blocks.append("identity_module_id_mismatch")
    if identity_payload.get("team_subject_code_prefix_bridge_mode") != IDENTITY_BRIDGE_MODE:
        blocks.append("identity_team_bridge_mode_mismatch")

    for label, payload in (
        ("semantic", semantic_payload),
        ("evidence", evidence_payload),
        ("identity", identity_payload),
    ):
        if payload.get("canonical_event_count") != "UNKNOWN":
            blocks.append(f"{label}_canonical_event_count_claimed")
        if payload.get("true_action_count") not in {None, "UNKNOWN"}:
            blocks.append(f"{label}_true_action_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{label}_production_release_claimed")
        upstream_status = _status(payload.get("status") or payload.get("module_status"))
        if upstream_status == "FAIL_CLOSED":
            blocks.append(f"{label}_upstream_fail_closed")
        elif upstream_status == "REVIEW_REQUIRED":
            reviews.append(f"{label}_upstream_review_required")

    semantic_rows = semantic_payload.get("context_action_semantic_records") or []
    atom_by_nucleus = _index_unique(
        evidence_payload.get("evidence_atoms") or [],
        "row_nucleus_candidate_id",
        "evidence_atom_by_row_nucleus",
        blocks,
    )
    binding_by_atom = _index_unique(
        identity_payload.get("identity_bindings") or [],
        "evidence_atom_id",
        "identity_binding_by_evidence_atom",
        blocks,
    )

    if not isinstance(semantic_rows, list):
        blocks.append("semantic_record_collection_invalid")
        semantic_rows = []

    if blocks:
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "decision": "TEAM_ATTRIBUTION_PROJECTION_REJECTED",
            "context_action_semantic_records": [],
            "input_action_occurrence_eligible_count": 0,
            "direct_known_team_eligible_count": 0,
            "recovered_team_eligible_count": 0,
            "unresolved_team_eligible_count": 0,
            "raw_known_team_coverage_candidate": None,
            "effective_known_team_coverage_candidate": None,
            "hard_block_hits": sorted(set(blocks)),
            "review_hits": sorted(set(reviews)),
            "team_attribution_is_validated_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    projected_rows: list[dict[str, Any]] = []
    direct_eligible = recovered_eligible = unresolved_eligible = eligible_total = 0
    recovered_all = 0

    for index, raw_row in enumerate(semantic_rows):
        if not isinstance(raw_row, dict):
            blocks.append(f"semantic_record_invalid:{index}")
            continue
        row = deepcopy(raw_row)
        raw_team = _clean(raw_row.get("context_team_candidate")) or "unknown"
        row["context_team_candidate_raw_surface"] = raw_team
        row["team_identity_candidate_id"] = None
        row["team_attribution_recovered"] = False
        row["team_attribution_is_validated_truth"] = False

        eligible = raw_row.get("action_occurrence_eligible") is True
        if eligible:
            eligible_total += 1

        if not _is_unknown(raw_team):
            row["team_attribution_state_candidate"] = "DIRECT_VISIBLE_CONTEXT_TEAM"
            row["team_attribution_basis"] = "DIRECT_VISIBLE_CONTEXT_TEAM"
            if eligible:
                direct_eligible += 1
            projected_rows.append(row)
            continue

        nucleus_id = _clean(raw_row.get("row_nucleus_candidate_id"))
        atom = atom_by_nucleus.get(nucleus_id)
        binding = binding_by_atom.get(_clean(atom.get("evidence_atom_id")) if atom else "")
        identity_team = _identity_team_candidate(binding)

        can_recover = (
            raw_row.get("source_role") == "TEAM"
            and isinstance(atom, dict)
            and atom.get("source_role_short") == "TEAM"
            and isinstance(binding, dict)
            and binding.get("source_role") == "TEAM_SURFACE_CANDIDATE"
            and binding.get("decision_state") == "TEAM_IDENTITY_CANDIDATE_BOUND"
            and bool(_clean(binding.get("team_identity_candidate_id")))
            and not _is_unknown(identity_team)
            and binding.get("validated_team_identity") is False
        )

        if can_recover:
            row["context_team_candidate"] = identity_team
            row["team_identity_candidate_id"] = _clean(binding.get("team_identity_candidate_id"))
            row["team_attribution_state_candidate"] = "RECOVERED_FROM_MATCH_LOCAL_IDENTITY_CANDIDATE"
            row["team_attribution_basis"] = "EXISTING_MATCH_LOCAL_IDENTITY_BINDING"
            row["team_attribution_recovered"] = True
            recovered_all += 1
            if eligible:
                recovered_eligible += 1
        else:
            row["context_team_candidate"] = raw_team
            row["team_attribution_state_candidate"] = "UNRESOLVED_TEAM_CANDIDATE"
            row["team_attribution_basis"] = "NO_ADMISSIBLE_MATCH_LOCAL_IDENTITY_BINDING"
            if eligible:
                unresolved_eligible += 1

        projected_rows.append(row)

    if len(projected_rows) != len(semantic_rows):
        blocks.append("semantic_projection_population_mismatch")

    if direct_eligible + recovered_eligible + unresolved_eligible != eligible_total:
        blocks.append("eligible_team_attribution_accounting_mismatch")

    raw_known = direct_eligible
    effective_known = direct_eligible + recovered_eligible
    raw_coverage = round(raw_known / eligible_total, 6) if eligible_total else None
    effective_coverage = round(effective_known / eligible_total, 6) if eligible_total else None

    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "decision": "TEAM_ATTRIBUTION_PROJECTED_FROM_EXISTING_MATCH_LOCAL_IDENTITY" if not blocks else "TEAM_ATTRIBUTION_PROJECTION_REJECTED",
        "context_action_semantic_records": projected_rows if not blocks else [],
        "input_action_occurrence_eligible_count": eligible_total if not blocks else 0,
        "direct_known_team_eligible_count": direct_eligible if not blocks else 0,
        "recovered_team_eligible_count": recovered_eligible if not blocks else 0,
        "unresolved_team_eligible_count": unresolved_eligible if not blocks else 0,
        "recovered_team_record_count_all_semantic_roles": recovered_all if not blocks else 0,
        "raw_known_team_coverage_candidate": raw_coverage if not blocks else None,
        "effective_known_team_coverage_candidate": effective_coverage if not blocks else None,
        "action_occurrence_count_changed_by_projection": False,
        "new_team_identity_created": False,
        "fuzzy_team_matching_used": False,
        "opponent_guessing_used": False,
        "filename_team_inference_used": False,
        "episode_majority_vote_used": False,
        "team_attribution_is_validated_truth": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "production_release": False,
    }
