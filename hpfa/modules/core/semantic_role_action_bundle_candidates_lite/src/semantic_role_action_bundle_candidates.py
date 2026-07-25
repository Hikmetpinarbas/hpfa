from __future__ import annotations

import argparse
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
    if not _clean(atom.get("evidence_atom_id")):
        blocks.append(f"evidence_atom_id_missing:{index}")
    if atom.get("match_surface_binding_id") != binding_id:
        blocks.append(f"atom_match_surface_binding_mismatch:{index}")
    if atom.get("source_role") not in ALLOWED_SOURCE_ROLES:
        blocks.append(f"atom_source_role_rejected:{index}")
    if atom.get("atom_class") not in ALLOWED_ATOM_CLASSES:
        blocks.append(f"atom_class_rejected:{index}")
    source_paths = atom.get("source_relative_paths") or []
    source_shas = atom.get("source_sha256_lineage") or []
    runtime_shas = atom.get("runtime_rehashed_sha256") or {}
    if not isinstance(source_paths, list) or len(source_paths) != 2 or not all(_clean(item) for item in source_paths):
        blocks.append(f"source_paths_invalid:{index}")
    if not isinstance(source_shas, list) or len(source_shas) != 2 or not all(_valid_sha256(item) for item in source_shas):
        blocks.append(f"source_sha_lineage_invalid:{index}")
    if not isinstance(runtime_shas, dict) or not _valid_sha256(runtime_shas.get("csv")) or not _valid_sha256(runtime_shas.get("xml")):
        blocks.append(f"runtime_sha_lineage_invalid:{index}")
    if isinstance(source_shas, list) and len(source_shas) == 2 and isinstance(runtime_shas, dict):
        if str(source_shas[0]).casefold() != str(runtime_shas.get("csv") or "").casefold():
            blocks.append(f"csv_sha_mismatch:{index}")
        if str(source_shas[1]).casefold() != str(runtime_shas.get("xml") or "").casefold():
            blocks.append(f"xml_sha_mismatch:{index}")
    if atom.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
        blocks.append(f"atom_canonical_event_claimed:{index}")
    if atom.get("event_instance_allowed") is True or atom.get("validated_event_identity") is True:
        blocks.append(f"atom_event_admission_claimed:{index}")
    return blocks


def _route_atom(atom: dict[str, Any], binding: dict[str, Any]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    atom_class = str(atom.get("atom_class") or "")
    source_role = str(atom.get("source_role") or "")
    semantic_role = str(atom.get("semantic_role_candidate") or "")
    identity_state = str(binding.get("decision_state") or "")

    if atom.get("atom_status") != "PASS":
        reasons.append("atom_status_not_pass")
    if identity_state not in BOUND_IDENTITY_STATES:
        reasons.append("identity_binding_not_cleared")
    if atom_class == "REVIEW_REQUIRED_ATOM":
        reasons.append("review_required_atom_class")
    if reasons:
        return "REVIEW_REQUIRED_ROUTE", sorted(set(reasons))

    if atom_class == "ADMINISTRATIVE_ATOM":
        return "ADMINISTRATIVE_ROUTE", []
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
        if binding.get("match_surface_binding_id") != evidence_binding:
            blocks.append(f"identity_binding_match_surface_mismatch:{index}")
        binding_by_atom_id[atom_id] = binding

    if set(atom_by_id) != set(binding_by_atom_id):
        blocks.append("identity_binding_atom_coverage_mismatch")

    semantic_routes: list[dict[str, Any]] = []
    eligible_groups: dict[tuple[str, ...], list[tuple[dict[str, Any], dict[str, Any], list[str]]]] = defaultdict(list)
    core_families: dict[tuple[str, ...], set[str]] = defaultdict(set)

    if not blocks:
        for atom_id in sorted(atom_by_id):
            atom = atom_by_id[atom_id]
            binding = binding_by_atom_id[atom_id]
            route, route_reasons = _route_atom(atom, binding)
            semantic_routes.append(
                {
                    "semantic_route_record_id": "srr_" + _digest(evidence_binding, atom_id)[:24],
                    "evidence_atom_id": atom_id,
                    "match_surface_binding_id": evidence_binding,
                    "source_role": atom.get("source_role"),
                    "atom_class": atom.get("atom_class"),
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
                }
            )

            if atom.get("atom_class") != "ACTION_ANCHOR_ATOM" or route == "REVIEW_REQUIRED_ROUTE":
                continue
            families = sorted({_clean(item) for item in (atom.get("action_family_candidates") or []) if _clean(item)})
            bundle_reasons: list[str] = []
            if len(families) != 1:
                bundle_reasons.append("action_anchor_family_not_single")
                continue
            source_role = _clean(atom.get("source_role"))
            team_id, actor_id = _identity_key(binding, source_role)
            if not team_id:
                bundle_reasons.append("team_identity_candidate_missing")
            if source_role != "TEAM_SURFACE_CANDIDATE" and not actor_id:
                bundle_reasons.append("actor_identity_candidate_missing")
            if not _clean(atom.get("period_candidate")):
                bundle_reasons.append("period_candidate_missing")
            if not _clean(atom.get("start_candidate")) or not _clean(atom.get("end_candidate")):
                bundle_reasons.append("time_candidate_missing")
            if atom.get("pos_x_candidate") is None or atom.get("pos_y_candidate") is None:
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
        action_bundles.append(
            {
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
                "coordinate_evidence_status": representative.get("coordinate_evidence_status"),
                "action_family_candidate": family,
                "supporting_evidence_atom_ids": atom_ids,
                "provider_row_id_candidates": provider_row_ids,
                "raw_labels": raw_labels,
                "normalized_labels": normalized_labels,
                "bundle_status": bundle_status,
                "review_hits": sorted(reasons),
                "same_role_exact_grouping": True,
                "cross_role_fusion_allowed": False,
                "validated_event_identity": False,
                "event_instance_allowed": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
                "claim_ceiling": CLAIM_CEILING,
            }
        )

    relation_groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for bundle in action_bundles:
        relation_groups[_relation_key(bundle)].append(bundle)
    cross_role_stubs: list[dict[str, Any]] = []
    for relation_key, grouped in sorted(relation_groups.items()):
        roles = sorted({_clean(bundle.get("source_role")) for bundle in grouped})
        if len(roles) < 2:
            continue
        bundle_ids = sorted(_clean(bundle.get("action_bundle_candidate_id")) for bundle in grouped)
        cross_role_stubs.append(
            {
                "cross_role_relation_candidate_id": "crc_" + _digest(relation_key, bundle_ids)[:24],
                "match_surface_binding_id": evidence_binding,
                "action_bundle_candidate_ids": bundle_ids,
                "source_roles": roles,
                "relation_status": "CANDIDATE_EXACT_SURFACE_OVERLAP_NOT_FUSED",
                "cross_role_fusion_allowed": False,
                "event_instance_allowed": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
                "claim_ceiling": CLAIM_CEILING,
            }
        )

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
        "base_event_admission_allowed": False,
        "event_instance_count": 0,
        "cross_role_fusion_allowed": False,
        "metric_value_output_allowed": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }


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
    summary = [
        "HPFA SEMANTIC ROLE AND ACTION BUNDLE CANDIDATES LITE V1",
        f"status={result['status']}",
        f"semantic_route_record_count={result['semantic_route_record_count']}",
        f"action_bundle_candidate_count={result['action_bundle_candidate_count']}",
        f"action_bundle_pass_count={result['action_bundle_pass_count']}",
        f"action_bundle_review_required_count={result['action_bundle_review_required_count']}",
        f"cross_role_relation_candidate_count={result['cross_role_relation_candidate_count']}",
        f"hard_block_hits={result['hard_block_hits']}",
        f"review_hits={result['review_hits']}",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    (output_dir / OUTPUTS["summary"]).write_text("\n".join(summary) + "\n", encoding="utf-8")
    analyst = [
        "HPFA ANALYST AUDIT — SEMANTIC ROUTES AND ACTION BUNDLE CANDIDATES",
        f"Visible evidence atoms routed: {result['semantic_route_record_count']}",
        f"Same-role exact action-bundle candidates: {result['action_bundle_candidate_count']}",
        f"Review-required action-bundle candidates: {result['action_bundle_review_required_count']}",
        f"Cross-role overlap candidates kept separate: {result['cross_role_relation_candidate_count']}",
        "These records are visible-surface candidates, not canonical events or physical-action truth.",
        "Cross-role records are not fused at this layer.",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    (output_dir / OUTPUTS["analyst"]).write_text("\n".join(analyst) + "\n", encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-atoms", required=True)
    parser.add_argument("--identity-candidates", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        result = write_outputs(args.evidence_atoms, args.identity_candidates, args.out)
    except ValueError as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "hard_block_hits": [str(exc)]}, indent=2))
        return 2
    print(
        json.dumps(
            {
                "status": result.get("status"),
                "semantic_route_record_count": result.get("semantic_route_record_count"),
                "action_bundle_candidate_count": result.get("action_bundle_candidate_count"),
                "action_bundle_review_required_count": result.get("action_bundle_review_required_count"),
                "cross_role_relation_candidate_count": result.get("cross_role_relation_candidate_count"),
                "canonical_event_count": result.get("canonical_event_count"),
                "production_release": result.get("production_release"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if result.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
