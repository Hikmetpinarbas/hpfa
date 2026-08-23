from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "semantic_role_action_bundle_candidates_lite_v1"
EVIDENCE_MODULE_ID = "evidence_atom_inventory_lite_v1"
IDENTITY_MODULE_ID = "match_local_identity_candidates_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "ACTION_BUNDLE_CANDIDATE_ONLY"

ALLOWED_SOURCE_ROLES = {
    "GOALKEEPER_SURFACE_CANDIDATE",
    "PLAYER_SURFACE_CANDIDATE",
    "TEAM_SURFACE_CANDIDATE",
}
SOURCE_ROLE_SHORT = {
    "GOALKEEPER_SURFACE_CANDIDATE": "GOALKEEPER",
    "PLAYER_SURFACE_CANDIDATE": "PLAYER",
    "TEAM_SURFACE_CANDIDATE": "TEAM",
}
ALLOWED_ATOM_CLASSES = {
    "ACTION_ANCHOR_ATOM",
    "ADMINISTRATIVE_ATOM",
    "CONTEXT_INTERVAL_ATOM",
    "DERIVED_CONSEQUENCE_ATOM",
    "PARTICIPATION_INTERVAL_ATOM",
    "REFERENCE_ATOM",
    "REVIEW_REQUIRED_ATOM",
    "TERMINAL_OUTCOME_ATOM",
}
BOUND_IDENTITY_STATES = {
    "ACTOR_IDENTITY_CANDIDATE_BOUND",
    "TEAM_IDENTITY_CANDIDATE_BOUND",
    "IDENTITY_NOT_APPLICABLE",
}
OUTPUTS = {
    "json": "semantic_role_action_bundle_candidates_lite_v1.json",
    "summary": "semantic_role_action_bundle_candidates_lite_v1.txt",
    "analyst": "semantic_role_action_bundle_candidates_analyst_audit_v1.txt",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _number_key(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    try:
        return f"{float(text):.6f}"
    except (TypeError, ValueError):
        return text


def _missing_scalar(value: Any) -> bool:
    return _clean(value).casefold() in {"", "none", "null", "unknown", "n/a"}


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def load_json(path: str | Path, error_code: str) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(error_code) from exc
    if not isinstance(payload, dict):
        raise ValueError(error_code)
    return payload


def _validate_atom(atom: dict[str, Any], index: int, binding_id: str) -> list[str]:
    blocks: list[str] = []
    atom_id = _clean(atom.get("evidence_atom_id"))
    if not atom_id:
        blocks.append(f"evidence_atom_id_missing:{index}")
    if atom.get("match_surface_binding_id") != binding_id:
        blocks.append(f"atom_match_surface_binding_mismatch:{index}")
    source_role = atom.get("source_role")
    if source_role not in ALLOWED_SOURCE_ROLES:
        blocks.append(f"atom_source_role_rejected:{index}")
    if atom.get("atom_class") not in ALLOWED_ATOM_CLASSES:
        blocks.append(f"atom_class_rejected:{index}")
    if atom.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
        blocks.append(f"atom_canonical_event_claimed:{index}")
    if atom.get("event_instance_allowed") is True or atom.get("validated_event_identity") is True:
        blocks.append(f"atom_event_admission_claimed:{index}")
    if atom.get("physical_action_identity_truth") is True:
        blocks.append(f"atom_physical_action_identity_claimed:{index}")
    if atom.get("cross_role_fusion_allowed") is True:
        blocks.append(f"atom_cross_role_fusion_open:{index}")
    if atom.get("independent_source_vote_allowed") is True or int(atom.get("independent_support_vote_count") or 0) != 0:
        blocks.append(f"atom_independent_source_vote_claimed:{index}")
    if atom.get("same_time_link_allowed") is True:
        blocks.append(f"atom_same_time_link_open:{index}")
    if atom.get("negative_time_link_allowed") is True:
        blocks.append(f"atom_negative_time_link_open:{index}")
    if atom.get("cross_period_link_allowed") is True:
        blocks.append(f"atom_cross_period_link_open:{index}")

    lineage = atom.get("source_lineage_records")
    if not isinstance(lineage, list) or not lineage:
        blocks.append(f"source_lineage_records_missing:{index}")
        return blocks
    expected_short = SOURCE_ROLE_SHORT.get(str(source_role))
    for j, record in enumerate(lineage):
        if not isinstance(record, dict):
            blocks.append(f"source_lineage_record_invalid:{index}:{j}")
            continue
        fmt = _clean(record.get("source_format")).casefold()
        if fmt not in {"csv", "xml"}:
            blocks.append(f"source_lineage_format_rejected:{index}:{fmt or 'UNKNOWN'}")
        if not _valid_sha256(record.get("source_sha256")):
            blocks.append(f"source_lineage_sha_invalid:{index}:{j}")
        if record.get("source_row_index_is_order_truth") is True:
            blocks.append(f"source_row_index_promoted_to_order_truth:{index}:{j}")
        record_role = _clean(record.get("source_role"))
        if expected_short and record_role and record_role != expected_short:
            blocks.append(f"source_lineage_role_mismatch:{index}:{j}")
    return blocks


def _validate_binding(binding: dict[str, Any], atom: dict[str, Any], index: int, binding_id: str) -> list[str]:
    blocks: list[str] = []
    if binding.get("match_surface_binding_id") != binding_id:
        blocks.append(f"identity_binding_match_surface_mismatch:{index}")
    if binding.get("source_role") != atom.get("source_role"):
        blocks.append(f"identity_binding_source_role_mismatch:{index}")
    if binding.get("event_instance_allowed") is True or binding.get("validated_event_identity") is True:
        blocks.append(f"identity_binding_event_admission_claimed:{index}")
    if binding.get("cross_role_fusion_allowed") is True:
        blocks.append(f"identity_binding_cross_role_fusion_open:{index}")
    return blocks


def _route_atom(atom: dict[str, Any], binding: dict[str, Any]) -> tuple[str, list[str]]:
    atom_class = _clean(atom.get("atom_class"))
    source_role = _clean(atom.get("source_role"))
    semantic_role = _clean(atom.get("semantic_role_candidate"))
    identity_state = _clean(binding.get("decision_state"))
    reasons: list[str] = []

    if identity_state not in BOUND_IDENTITY_STATES:
        reasons.append("identity_binding_not_cleared")

    # Preserve the administrative role even when an upstream serialization
    # discrepancy remains review-required. Admit the role, not the equality.
    if atom_class == "ADMINISTRATIVE_ATOM":
        if identity_state != "IDENTITY_NOT_APPLICABLE":
            reasons.append("administrative_identity_state_mismatch")
        if atom.get("atom_status") != "PASS":
            reasons.append("upstream_atom_review_preserved")
        return "ADMINISTRATIVE_ROUTE", sorted(set(reasons))

    if atom.get("atom_status") != "PASS":
        reasons.append("atom_status_not_pass")
    if atom_class == "REVIEW_REQUIRED_ATOM":
        reasons.append("review_required_atom_class")
    if reasons:
        return "REVIEW_REQUIRED_ROUTE", sorted(set(reasons))

    if atom_class == "CONTEXT_INTERVAL_ATOM":
        return "CONTEXT_INTERVAL_ROUTE", []
    if atom_class == "PARTICIPATION_INTERVAL_ATOM":
        return "PARTICIPATION_INTERVAL_ROUTE", []
    if atom_class == "DERIVED_CONSEQUENCE_ATOM":
        return "DERIVED_CONSEQUENCE_ROUTE", []
    if atom_class == "TERMINAL_OUTCOME_ATOM":
        return "TERMINAL_OUTCOME_ROUTE", []
    if atom_class == "REFERENCE_ATOM":
        if source_role == "GOALKEEPER_SURFACE_CANDIDATE" and semantic_role == "OPPONENT_ACTION_REFERENCE":
            return "GOALKEEPER_OPPONENT_REFERENCE_ROUTE", []
        return "REFERENCE_ROUTE", []
    if atom_class == "ACTION_ANCHOR_ATOM":
        if source_role == "TEAM_SURFACE_CANDIDATE":
            return "TEAM_ACTION_REFLECTION_ROUTE", []
        if source_role == "GOALKEEPER_SURFACE_CANDIDATE":
            return "GOALKEEPER_ACTION_ROUTE", []
        if source_role == "PLAYER_SURFACE_CANDIDATE":
            return "PRIMARY_ACTION_ANCHOR_ROUTE", []
    return "REVIEW_REQUIRED_ROUTE", ["semantic_route_not_registered"]


def _identity_key(binding: dict[str, Any], source_role: str) -> tuple[str, str]:
    team_id = _clean(binding.get("team_identity_candidate_id"))
    actor_id = _clean(binding.get("actor_identity_candidate_id"))
    if source_role == "TEAM_SURFACE_CANDIDATE":
        return team_id, ""
    return team_id, actor_id


def _action_core_key(atom: dict[str, Any], binding: dict[str, Any]) -> tuple[str, ...]:
    source_role = _clean(atom.get("source_role"))
    team_id, actor_id = _identity_key(binding, source_role)
    return (
        _clean(atom.get("match_surface_binding_id")),
        source_role,
        team_id,
        actor_id,
        _clean(atom.get("period_candidate")),
        _number_key(atom.get("start_candidate")),
        _number_key(atom.get("end_candidate")),
        _number_key(atom.get("pos_x_candidate")),
        _number_key(atom.get("pos_y_candidate")),
    )


def _relation_key(bundle: dict[str, Any]) -> tuple[str, ...]:
    return (
        _clean(bundle.get("match_surface_binding_id")),
        _clean(bundle.get("team_identity_candidate_id")),
        _clean(bundle.get("period_candidate")),
        _number_key(bundle.get("start_candidate")),
        _number_key(bundle.get("end_candidate")),
        _number_key(bundle.get("pos_x_candidate")),
        _number_key(bundle.get("pos_y_candidate")),
        _clean(bundle.get("action_family_candidate")),
    )


def build_semantic_role_action_bundle_candidates(
    evidence_payload: dict[str, Any],
    identity_payload: dict[str, Any],
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if evidence_payload.get("module_id") != EVIDENCE_MODULE_ID:
        blocks.append("evidence_atom_module_id_mismatch")
    if identity_payload.get("module_id") != IDENTITY_MODULE_ID:
        blocks.append("identity_module_id_mismatch")
    for prefix, payload in (("evidence", evidence_payload), ("identity", identity_payload)):
        if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
            blocks.append(f"{prefix}_canonical_event_count_claimed")
        if payload.get("production_release") is True:
            blocks.append(f"{prefix}_production_claimed")
        if payload.get("hard_block_hits"):
            blocks.append(f"{prefix}_hard_blocks_present")

    evidence_binding = _clean(evidence_payload.get("match_surface_binding_id"))
    identity_binding = _clean(identity_payload.get("match_surface_binding_id"))
    if not evidence_binding or evidence_binding != identity_binding:
        blocks.append("match_surface_binding_mismatch")

    atoms = evidence_payload.get("evidence_atoms") or []
    bindings = identity_payload.get("identity_bindings") or []
    if not isinstance(atoms, list) or not atoms:
        blocks.append("evidence_atom_inventory_empty_or_invalid")
        atoms = []
    if not isinstance(bindings, list) or not bindings:
        blocks.append("identity_binding_inventory_empty_or_invalid")
        bindings = []
    if evidence_payload.get("evidence_atom_count") != len(atoms):
        blocks.append("evidence_atom_count_mismatch")
    if identity_payload.get("identity_binding_record_count") != len(bindings):
        blocks.append("identity_binding_count_mismatch")

    atom_by_id: dict[str, dict[str, Any]] = {}
    for index, atom in enumerate(atoms):
        if not isinstance(atom, dict):
            blocks.append(f"evidence_atom_record_invalid:{index}")
            continue
        blocks.extend(_validate_atom(atom, index, evidence_binding))
        atom_id = _clean(atom.get("evidence_atom_id"))
        if atom_id in atom_by_id:
            blocks.append(f"duplicate_evidence_atom_id:{atom_id}")
        atom_by_id[atom_id] = atom

    binding_by_atom_id: dict[str, dict[str, Any]] = {}
    for index, binding in enumerate(bindings):
        if not isinstance(binding, dict):
            blocks.append(f"identity_binding_record_invalid:{index}")
            continue
        atom_id = _clean(binding.get("evidence_atom_id"))
        if not atom_id:
            blocks.append(f"identity_binding_atom_id_missing:{index}")
            continue
        if atom_id in binding_by_atom_id:
            blocks.append(f"duplicate_identity_binding_atom_id:{atom_id}")
        binding_by_atom_id[atom_id] = binding

    if set(atom_by_id) != set(binding_by_atom_id):
        blocks.append("identity_binding_atom_coverage_mismatch")

    if not blocks:
        for index, atom_id in enumerate(sorted(atom_by_id)):
            blocks.extend(_validate_binding(binding_by_atom_id[atom_id], atom_by_id[atom_id], index, evidence_binding))

    blocks = sorted(set(blocks))
    semantic_routes: list[dict[str, Any]] = []
    eligible_groups: dict[tuple[str, ...], list[tuple[dict[str, Any], dict[str, Any], list[str]]]] = defaultdict(list)
    core_families: dict[tuple[str, ...], set[str]] = defaultdict(set)

    if not blocks:
        for atom_id in sorted(atom_by_id):
            atom = atom_by_id[atom_id]
            binding = binding_by_atom_id[atom_id]
            route, route_reasons = _route_atom(atom, binding)
            semantic_routes.append({
                "semantic_route_record_id": "srr_" + _digest(evidence_binding, atom_id)[:24],
                "evidence_atom_id": atom_id,
                "match_surface_binding_id": evidence_binding,
                "source_role": atom.get("source_role"),
                "atom_class": atom.get("atom_class"),
                "atom_status": atom.get("atom_status"),
                "semantic_role_candidate": atom.get("semantic_role_candidate"),
                "action_family_candidates": atom.get("action_family_candidates") or [],
                "identity_decision_state": binding.get("decision_state"),
                "team_identity_candidate_id": binding.get("team_identity_candidate_id"),
                "actor_identity_candidate_id": binding.get("actor_identity_candidate_id"),
                "semantic_route": route,
                "route_status": "REVIEW_REQUIRED" if route_reasons else "PASS",
                "review_hits": route_reasons,
                "cross_role_fusion_allowed": False,
                "event_instance_allowed": False,
                "claim_ceiling": CLAIM_CEILING,
            })

            if atom.get("atom_class") != "ACTION_ANCHOR_ATOM" or route == "REVIEW_REQUIRED_ROUTE":
                continue
            families = sorted({_clean(item) for item in (atom.get("action_family_candidates") or []) if _clean(item)})
            if len(families) != 1:
                continue
            source_role = _clean(atom.get("source_role"))
            team_id, actor_id = _identity_key(binding, source_role)
            bundle_reasons: list[str] = []
            if not team_id:
                bundle_reasons.append("team_identity_candidate_missing")
            if source_role != "TEAM_SURFACE_CANDIDATE" and not actor_id:
                bundle_reasons.append("actor_identity_candidate_missing")
            if _missing_scalar(atom.get("period_candidate")):
                bundle_reasons.append("period_candidate_missing")
            if _missing_scalar(atom.get("start_candidate")) or _missing_scalar(atom.get("end_candidate")):
                bundle_reasons.append("time_candidate_missing")
            if _missing_scalar(atom.get("pos_x_candidate")) or _missing_scalar(atom.get("pos_y_candidate")):
                bundle_reasons.append("coordinate_surface_missing_preserved")
            core_key = _action_core_key(atom, binding)
            family = families[0]
            core_families[core_key].add(family)
            eligible_groups[core_key + (family,)].append((atom, binding, bundle_reasons))

    family_conflict_cores = {key for key, families in core_families.items() if len(families) > 1}
    action_bundles: list[dict[str, Any]] = []
    for group_key in sorted(eligible_groups):
        rows = eligible_groups[group_key]
        representative, binding, _ = rows[0]
        core_key = group_key[:-1]
        family = group_key[-1]
        reasons = {reason for _, _, item_reasons in rows for reason in item_reasons}
        if core_key in family_conflict_cores:
            reasons.add("same_surface_multiple_action_families")
        source_role = _clean(representative.get("source_role"))
        team_id, actor_id = _identity_key(binding, source_role)
        atom_ids = sorted(_clean(atom.get("evidence_atom_id")) for atom, _, _ in rows)
        raw_labels = sorted({_clean(atom.get("raw_label")) for atom, _, _ in rows if _clean(atom.get("raw_label"))})
        normalized_labels = sorted({_clean(atom.get("normalized_label")) for atom, _, _ in rows if _clean(atom.get("normalized_label"))})
        provider_row_ids = sorted({_clean(atom.get("provider_row_id_candidate")) for atom, _, _ in rows if _clean(atom.get("provider_row_id_candidate"))})
        bundle_status = "REVIEW_REQUIRED" if reasons else "PASS"
        action_bundles.append({
            "action_bundle_candidate_id": "abc_" + _digest(group_key, atom_ids)[:24],
            "match_surface_binding_id": evidence_binding,
            "source_role": source_role,
            "team_identity_candidate_id": team_id or None,
            "actor_identity_candidate_id": actor_id or None,
            "period_candidate": representative.get("period_candidate"),
            "start_candidate": representative.get("start_candidate"),
            "end_candidate": representative.get("end_candidate"),
            "pos_x_candidate": representative.get("pos_x_candidate"),
            "pos_y_candidate": representative.get("pos_y_candidate"),
            "coordinate_evidence_status": "COORDINATE_PRESENT",
            "action_family_candidate": family,
            "supporting_evidence_atom_ids": atom_ids,
            "provider_row_id_candidates": provider_row_ids,
            "raw_labels": raw_labels,
            "normalized_labels": normalized_labels,
            "bundle_status": bundle_status,
            "review_hits": sorted(reasons),
            "same_role_exact_grouping": True,
            "source_row_order_is_temporal_truth": False,
            "same_time_order_truth_admitted": False,
            "cross_role_fusion_allowed": False,
            "validated_event_identity": False,
            "event_instance_allowed": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "claim_ceiling": CLAIM_CEILING,
        })

    relation_groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for bundle in action_bundles:
        relation_groups[_relation_key(bundle)].append(bundle)
    cross_role_stubs: list[dict[str, Any]] = []
    for relation_key, grouped in sorted(relation_groups.items()):
        roles = sorted({_clean(bundle.get("source_role")) for bundle in grouped})
        if len(roles) < 2:
            continue
        bundle_ids = sorted(_clean(bundle.get("action_bundle_candidate_id")) for bundle in grouped)
        cross_role_stubs.append({
            "cross_role_relation_candidate_id": "crc_" + _digest(relation_key, bundle_ids)[:24],
            "match_surface_binding_id": evidence_binding,
            "action_bundle_candidate_ids": bundle_ids,
            "source_roles": roles,
            "relation_status": "CANDIDATE_EXACT_SURFACE_OVERLAP_NOT_FUSED",
            "cross_role_fusion_allowed": False,
            "event_instance_allowed": False,
            "independent_source_vote_allowed": False,
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "claim_ceiling": CLAIM_CEILING,
        })

    evidence_status = str(evidence_payload.get("module_status") or evidence_payload.get("status") or "UNKNOWN")
    identity_status = str(identity_payload.get("module_status") or identity_payload.get("status") or "UNKNOWN")
    if evidence_status == "FAIL_CLOSED":
        blocks.append("evidence_atom_input_fail_closed")
    elif evidence_status == "REVIEW_REQUIRED":
        reviews.append("evidence_atom_upstream_review_required")
    elif evidence_status != "PASS":
        reviews.append(f"evidence_atom_upstream_status_review:{evidence_status}")
    if identity_status == "FAIL_CLOSED":
        blocks.append("identity_input_fail_closed")
    elif identity_status == "REVIEW_REQUIRED":
        reviews.append("identity_upstream_review_required")
    elif identity_status != "PASS":
        reviews.append(f"identity_upstream_status_review:{identity_status}")

    route_review_count = sum(item.get("route_status") == "REVIEW_REQUIRED" for item in semantic_routes)
    bundle_review_count = sum(item.get("bundle_status") == "REVIEW_REQUIRED" for item in action_bundles)
    blocked_action_route_count = sum(
        item.get("semantic_route") == "REVIEW_REQUIRED_ROUTE" and item.get("atom_class") == "ACTION_ANCHOR_ATOM"
        for item in semantic_routes
    )
    if route_review_count:
        reviews.append("semantic_route_review_required")
    if bundle_review_count:
        reviews.append("action_bundle_candidate_review_required")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")
    route_counts = Counter(item.get("semantic_route") for item in semantic_routes)
    family_counts = Counter(item.get("action_family_candidate") for item in action_bundles)
    source_role_counts = Counter(item.get("source_role") for item in action_bundles)

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": evidence_binding or None,
        "semantic_route_records": semantic_routes,
        "semantic_route_record_count": len(semantic_routes),
        "semantic_route_review_required_count": route_review_count,
        "semantic_route_blocked_action_anchor_count": blocked_action_route_count,
        "semantic_route_counts": dict(sorted(route_counts.items())),
        "action_bundle_candidates": action_bundles,
        "action_bundle_candidate_count": len(action_bundles),
        "action_bundle_pass_count": len(action_bundles) - bundle_review_count,
        "action_bundle_review_required_count": bundle_review_count,
        "action_bundle_family_counts": dict(sorted(family_counts.items())),
        "action_bundle_source_role_counts": dict(sorted(source_role_counts.items())),
        "cross_role_relation_candidates": cross_role_stubs,
        "cross_role_relation_candidate_count": len(cross_role_stubs),
        "source_evidence_atom_count": len(atoms),
        "source_identity_binding_count": len(bindings),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "action_bundle_is_canonical_event": False,
        "validated_event_identity": False,
        "physical_action_identity_truth": False,
        "base_event_admission_allowed": False,
        "event_instance_count": 0,
        "cross_role_fusion_allowed": False,
        "independent_source_vote_allowed": False,
        "metric_value_output_allowed": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def render_summary(result: dict[str, Any]) -> str:
    lines = [
        "HPFA SEMANTIC ROLE AND ACTION BUNDLE CANDIDATES LITE V1",
        f"status={result.get('status')}",
        f"semantic_route_record_count={result.get('semantic_route_record_count')}",
        f"semantic_route_review_required_count={result.get('semantic_route_review_required_count')}",
        f"semantic_route_blocked_action_anchor_count={result.get('semantic_route_blocked_action_anchor_count')}",
        f"action_bundle_candidate_count={result.get('action_bundle_candidate_count')}",
        f"action_bundle_pass_count={result.get('action_bundle_pass_count')}",
        f"action_bundle_review_required_count={result.get('action_bundle_review_required_count')}",
        f"cross_role_relation_candidate_count={result.get('cross_role_relation_candidate_count')}",
        f"hard_block_hits={result.get('hard_block_hits')}",
        f"review_hits={result.get('review_hits')}",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
        "",
    ]
    return "\n".join(lines)


def render_analyst(result: dict[str, Any]) -> str:
    return "\n".join([
        "HPFA ANALYST AUDIT — CURRENT SEMANTIC ROUTES AND ACTION BUNDLE CANDIDATES",
        f"Visible evidence atoms routed: {result.get('semantic_route_record_count')}",
        f"Review-status route records: {result.get('semantic_route_review_required_count')}",
        f"Action anchors blocked by semantic review: {result.get('semantic_route_blocked_action_anchor_count')}",
        f"Same-role exact action-bundle candidates: {result.get('action_bundle_candidate_count')}",
        f"Review-required action-bundle candidates: {result.get('action_bundle_review_required_count')}",
        f"Cross-role overlap candidates kept separate: {result.get('cross_role_relation_candidate_count')}",
        "",
        "Safe meaning:",
        "Visible Evidence Atoms are routed by already-admitted atom class, semantic role, source role and match-local identity candidates.",
        "Administrative review markers retain their administrative role while their upstream discrepancy remains visible.",
        "PLAYER, TEAM and GOALKEEPER surfaces remain separate. Cross-role overlap is candidate-only and is never fused here.",
        "Action bundles are visible-surface grouping candidates, not canonical events or physical-action truth.",
        "No source-row or same-time ordering is promoted to football order.",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
        "",
    ])


def write_outputs(
    evidence_json: str | Path,
    identity_json: str | Path,
    out_dir: str | Path,
) -> dict[str, Any]:
    output_dir = validate_out(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_payload = load_json(evidence_json, "evidence_atom_output_unreadable_or_malformed")
    identity_payload = load_json(identity_json, "identity_output_unreadable_or_malformed")
    result = build_semantic_role_action_bundle_candidates(evidence_payload, identity_payload)
    (output_dir / OUTPUTS["json"]).write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / OUTPUTS["summary"]).write_text(render_summary(result), encoding="utf-8")
    (output_dir / OUTPUTS["analyst"]).write_text(render_analyst(result), encoding="utf-8")
    return result
