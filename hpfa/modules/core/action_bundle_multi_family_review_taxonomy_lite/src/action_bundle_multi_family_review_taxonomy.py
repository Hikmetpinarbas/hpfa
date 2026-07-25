from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "action_bundle_multi_family_review_taxonomy_lite_v1"
INPUT_MODULE_ID = "semantic_role_action_bundle_candidates_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "MULTI_FAMILY_REVIEW_TAXONOMY_ONLY"

ALLOWED_SOURCE_ROLES = {
    "GOALKEEPER_SURFACE_CANDIDATE",
    "PLAYER_SURFACE_CANDIDATE",
    "TEAM_SURFACE_CANDIDATE",
}
CORE_FIELDS = (
    "match_surface_binding_id",
    "source_role",
    "team_identity_candidate_id",
    "actor_identity_candidate_id",
    "period_candidate",
    "start_candidate",
    "end_candidate",
    "pos_x_candidate",
    "pos_y_candidate",
)
EXPECTED_REVIEW_REASON = "same_surface_multiple_action_families"

# Exact-set registry only. No token inference and no permissive family promotion.
EXACT_FAMILY_SET_REGISTRY: dict[frozenset[str], dict[str, Any]] = {
    frozenset({"DUEL", "TACKLE"}): {
        "classification": "HIERARCHICAL_SUBTYPE_CANDIDATE",
        "parent_family_candidate": "DUEL",
        "subtype_family_candidates": ["TACKLE"],
        "review_required": False,
        "rule_id": "MFRT_EXACT_DUEL_TACKLE_V1",
    },
    frozenset({"PASS", "CROSS"}): {
        "classification": "HIERARCHICAL_SUBTYPE_CANDIDATE",
        "parent_family_candidate": "PASS",
        "subtype_family_candidates": ["CROSS"],
        "review_required": False,
        "rule_id": "MFRT_EXACT_PASS_CROSS_V1",
    },
    frozenset({"TURNOVER", "CONTROL_ERROR"}): {
        "classification": "HIERARCHICAL_SUBTYPE_CANDIDATE",
        "parent_family_candidate": "TURNOVER",
        "subtype_family_candidates": ["CONTROL_ERROR"],
        "review_required": False,
        "rule_id": "MFRT_EXACT_TURNOVER_CONTROL_ERROR_V1",
    },
    frozenset({"PASS", "RESTART"}): {
        "classification": "RESTART_ACTION_COUPLING_CANDIDATE",
        "parent_family_candidate": None,
        "subtype_family_candidates": [],
        "review_required": False,
        "rule_id": "MFRT_EXACT_PASS_RESTART_V1",
    },
}

# Exact family sets that are useful for analyst routing but remain fail-closed.
COMPOUND_CO_OCCURRENCE_SETS = {
    frozenset({"DRIBBLE", "DUEL"}),
    frozenset({"DRIBBLE", "TURNOVER"}),
    frozenset({"CARRY", "DUEL"}),
}
SAME_TIME_RISK_SETS = {
    frozenset({"PASS", "RECOVERY"}),
    frozenset({"DUEL", "PASS"}),
    frozenset({"DUEL", "RECOVERY"}),
    frozenset({"CARRY", "RECOVERY"}),
    frozenset({"CLEARANCE", "RECOVERY"}),
}

OUTPUTS = {
    "json": "action_bundle_multi_family_review_taxonomy_lite_v1.json",
    "summary": "action_bundle_multi_family_review_taxonomy_lite_v1.txt",
    "analyst": "action_bundle_multi_family_review_taxonomy_analyst_audit_v1.txt",
}


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


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


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("action_bundle_input_unreadable_or_malformed") from exc
    if not isinstance(payload, dict):
        raise ValueError("action_bundle_input_not_object")
    return payload


def _core_key(bundle: dict[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    for field in CORE_FIELDS:
        value = bundle.get(field)
        if field in {"start_candidate", "end_candidate", "pos_x_candidate", "pos_y_candidate"}:
            values.append(_number_key(value))
        else:
            values.append(_clean(value))
    return tuple(values)


def _validate_bundle(bundle: dict[str, Any], index: int, expected_binding: str) -> list[str]:
    blocks: list[str] = []
    bundle_id = _clean(bundle.get("action_bundle_candidate_id"))
    if not bundle_id:
        blocks.append(f"action_bundle_candidate_id_missing:{index}")
    if bundle.get("match_surface_binding_id") != expected_binding:
        blocks.append(f"match_surface_binding_mismatch:{index}")
    if bundle.get("source_role") not in ALLOWED_SOURCE_ROLES:
        blocks.append(f"source_role_rejected:{index}")
    if not _clean(bundle.get("action_family_candidate")):
        blocks.append(f"action_family_candidate_missing:{index}")
    if bundle.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
        blocks.append(f"canonical_event_claimed:{index}")
    if bundle.get("validated_event_identity") is True:
        blocks.append(f"validated_event_identity_claimed:{index}")
    if bundle.get("event_instance_allowed") is True:
        blocks.append(f"event_instance_admission_claimed:{index}")
    if bundle.get("cross_role_fusion_allowed") is True:
        blocks.append(f"cross_role_fusion_claimed:{index}")
    evidence_ids = bundle.get("supporting_evidence_atom_ids") or []
    if not isinstance(evidence_ids, list) or not evidence_ids or not all(_clean(item) for item in evidence_ids):
        blocks.append(f"supporting_evidence_atom_ids_invalid:{index}")
    if bundle.get("same_role_exact_grouping") is not True:
        blocks.append(f"same_role_exact_grouping_not_true:{index}")
    return blocks


def _classification_for(family_set: frozenset[str]) -> dict[str, Any]:
    registered = EXACT_FAMILY_SET_REGISTRY.get(family_set)
    if registered:
        return dict(registered)
    if len(family_set) >= 3:
        return {
            "classification": "MULTI_FAMILY_COMPLEX_REVIEW_REQUIRED",
            "parent_family_candidate": None,
            "subtype_family_candidates": [],
            "review_required": True,
            "rule_id": "MFRT_COMPLEX_THREE_PLUS_V1",
        }
    if family_set in COMPOUND_CO_OCCURRENCE_SETS:
        return {
            "classification": "COMPOUND_ACTION_CO_OCCURRENCE_REVIEW_REQUIRED",
            "parent_family_candidate": None,
            "subtype_family_candidates": [],
            "review_required": True,
            "rule_id": "MFRT_EXACT_COMPOUND_COOCCURRENCE_V1",
        }
    if family_set in SAME_TIME_RISK_SETS:
        return {
            "classification": "SAME_TIME_GROUPING_RISK_REVIEW_REQUIRED",
            "parent_family_candidate": None,
            "subtype_family_candidates": [],
            "review_required": True,
            "rule_id": "MFRT_EXACT_SAME_TIME_RISK_V1",
        }
    return {
        "classification": "UNREGISTERED_FAMILY_SET_REVIEW_REQUIRED",
        "parent_family_candidate": None,
        "subtype_family_candidates": [],
        "review_required": True,
        "rule_id": "MFRT_UNREGISTERED_EXACT_SET_V1",
    }


def build_action_bundle_multi_family_review_taxonomy(payload: dict[str, Any]) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if payload.get("module_id") != INPUT_MODULE_ID:
        blocks.append("input_module_id_mismatch")
    if payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("input_canonical_event_count_claimed")
    if payload.get("production_release") is True:
        blocks.append("input_production_release_claimed")
    if payload.get("hard_block_hits"):
        blocks.append("input_hard_blocks_present")

    binding_id = _clean(payload.get("match_surface_binding_id"))
    if not binding_id:
        blocks.append("match_surface_binding_id_missing")

    bundles = payload.get("action_bundle_candidates") or []
    if not isinstance(bundles, list) or not bundles:
        blocks.append("action_bundle_candidates_empty_or_invalid")
        bundles = []
    if payload.get("action_bundle_candidate_count") != len(bundles):
        blocks.append("action_bundle_candidate_count_mismatch")

    seen_ids: set[str] = set()
    for index, bundle in enumerate(bundles):
        if not isinstance(bundle, dict):
            blocks.append(f"action_bundle_record_invalid:{index}")
            continue
        blocks.extend(_validate_bundle(bundle, index, binding_id))
        bundle_id = _clean(bundle.get("action_bundle_candidate_id"))
        if bundle_id in seen_ids:
            blocks.append(f"duplicate_action_bundle_candidate_id:{bundle_id}")
        seen_ids.add(bundle_id)

    review_bundles = [
        bundle
        for bundle in bundles
        if isinstance(bundle, dict) and bundle.get("bundle_status") == "REVIEW_REQUIRED"
    ]
    pass_bundles = [
        bundle
        for bundle in bundles
        if isinstance(bundle, dict) and bundle.get("bundle_status") == "PASS"
    ]
    unexpected_status_count = len(bundles) - len(review_bundles) - len(pass_bundles)
    if unexpected_status_count:
        blocks.append(f"unexpected_bundle_status_count:{unexpected_status_count}")
    if payload.get("action_bundle_review_required_count") != len(review_bundles):
        blocks.append("action_bundle_review_required_count_mismatch")
    if payload.get("action_bundle_pass_count") != len(pass_bundles):
        blocks.append("action_bundle_pass_count_mismatch")

    review_groups: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    if not blocks:
        for index, bundle in enumerate(review_bundles):
            reasons = sorted({_clean(item) for item in (bundle.get("review_hits") or []) if _clean(item)})
            if reasons != [EXPECTED_REVIEW_REASON]:
                blocks.append(f"review_reason_contract_mismatch:{index}")
                continue
            review_groups[_core_key(bundle)].append(bundle)

    records: list[dict[str, Any]] = []
    if not blocks:
        for core_key in sorted(review_groups):
            grouped = review_groups[core_key]
            family_set = frozenset(_clean(bundle.get("action_family_candidate")) for bundle in grouped)
            if "" in family_set or len(family_set) < 2:
                blocks.append("review_core_family_set_invalid")
                continue
            classification = _classification_for(family_set)
            source_roles = sorted({_clean(bundle.get("source_role")) for bundle in grouped})
            team_ids = sorted({_clean(bundle.get("team_identity_candidate_id")) for bundle in grouped})
            actor_ids = sorted({_clean(bundle.get("actor_identity_candidate_id")) for bundle in grouped})
            if len(source_roles) != 1 or len(team_ids) != 1 or len(actor_ids) != 1:
                blocks.append("review_core_identity_or_source_role_not_exact")
                continue
            coordinate_missing = any(
                bundle.get("coordinate_evidence_status") != "COORDINATE_PRESENT"
                for bundle in grouped
            )
            review_hits: list[str] = []
            if classification["review_required"]:
                review_hits.append(classification["classification"].casefold())
            if coordinate_missing:
                review_hits.append("coordinate_surface_missing_preserved")
            record_status = "REVIEW_REQUIRED" if review_hits else "PASS_CANDIDATE_CLASSIFICATION"
            supporting_bundle_ids = sorted(
                _clean(bundle.get("action_bundle_candidate_id")) for bundle in grouped
            )
            evidence_atom_ids = sorted(
                {
                    _clean(atom_id)
                    for bundle in grouped
                    for atom_id in (bundle.get("supporting_evidence_atom_ids") or [])
                    if _clean(atom_id)
                }
            )
            raw_labels = sorted(
                {
                    _clean(label)
                    for bundle in grouped
                    for label in (bundle.get("raw_labels") or [])
                    if _clean(label)
                }
            )
            normalized_labels = sorted(
                {
                    _clean(label)
                    for bundle in grouped
                    for label in (bundle.get("normalized_labels") or [])
                    if _clean(label)
                }
            )
            records.append(
                {
                    "multi_family_review_record_id": "mfr_"
                    + _digest(binding_id, core_key, sorted(family_set))[:24],
                    "match_surface_binding_id": binding_id,
                    "source_role": source_roles[0],
                    "team_identity_candidate_id": team_ids[0] or None,
                    "actor_identity_candidate_id": actor_ids[0] or None,
                    "period_candidate": core_key[4] or None,
                    "start_candidate": core_key[5] or None,
                    "end_candidate": core_key[6] or None,
                    "pos_x_candidate": core_key[7] or None,
                    "pos_y_candidate": core_key[8] or None,
                    "coordinate_evidence_status": (
                        "COORDINATE_MISSING" if coordinate_missing else "COORDINATE_PRESENT"
                    ),
                    "family_set": sorted(family_set),
                    "family_count": len(family_set),
                    "classification": classification["classification"],
                    "classification_rule_id": classification["rule_id"],
                    "parent_family_candidate": classification["parent_family_candidate"],
                    "subtype_family_candidates": classification["subtype_family_candidates"],
                    "supporting_action_bundle_candidate_ids": supporting_bundle_ids,
                    "supporting_evidence_atom_ids": evidence_atom_ids,
                    "raw_labels": raw_labels,
                    "normalized_labels": normalized_labels,
                    "record_status": record_status,
                    "review_hits": sorted(set(review_hits)),
                    "classification_is_event_truth": False,
                    "family_parent_is_validated_action": False,
                    "subtype_is_validated_action": False,
                    "restart_coupling_is_event_fusion": False,
                    "cross_role_fusion_allowed": False,
                    "event_instance_allowed": False,
                    "validated_event_identity": False,
                    "canonical_event_count": CANONICAL_EVENT_COUNT,
                    "claim_ceiling": CLAIM_CEILING,
                }
            )

    if (
        sum(len(record["supporting_action_bundle_candidate_ids"]) for record in records)
        != len(review_bundles)
        and not blocks
    ):
        blocks.append("review_bundle_coverage_mismatch")

    classification_counts = Counter(record["classification"] for record in records)
    source_role_counts = Counter(record["source_role"] for record in records)
    family_set_counts = Counter("+".join(record["family_set"]) for record in records)
    review_record_count = sum(record["record_status"] == "REVIEW_REQUIRED" for record in records)
    classified_candidate_count = len(records) - review_record_count
    missing_coordinate_count = sum(
        record["coordinate_evidence_status"] == "COORDINATE_MISSING" for record in records
    )

    input_status = str(payload.get("module_status") or payload.get("status") or "UNKNOWN")
    if input_status == "FAIL_CLOSED":
        blocks.append("input_module_fail_closed")
    elif input_status == "REVIEW_REQUIRED":
        reviews.append("action_bundle_upstream_review_required")
    elif input_status != "PASS":
        reviews.append(f"action_bundle_upstream_status_review:{input_status}")
    if review_record_count:
        reviews.append("unresolved_multi_family_review_records_present")
    if missing_coordinate_count:
        reviews.append("coordinate_surface_missing_preserved")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": binding_id or None,
        "multi_family_review_records": records,
        "source_action_bundle_candidate_count": len(bundles),
        "source_review_bundle_record_count": len(review_bundles),
        "source_pass_bundle_record_count": len(pass_bundles),
        "multi_family_review_core_count": len(records),
        "classified_candidate_core_count": classified_candidate_count,
        "review_required_core_count": review_record_count,
        "coordinate_missing_core_count": missing_coordinate_count,
        "classification_counts": dict(sorted(classification_counts.items())),
        "source_role_counts": dict(sorted(source_role_counts.items())),
        "family_set_counts": dict(
            sorted(family_set_counts.items(), key=lambda item: (-item[1], item[0]))
        ),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "classification_registry_version": (
            "action_bundle_multi_family_review_taxonomy_registry_v1"
        ),
        "classification_policy": (
            "EXACT_FAMILY_SET_ONLY_NO_TOKEN_INFERENCE_NO_EVENT_PROMOTION"
        ),
        "classification_is_event_truth": False,
        "family_parent_is_validated_action": False,
        "subtype_is_validated_action": False,
        "restart_coupling_is_event_fusion": False,
        "cross_role_fusion_allowed": False,
        "event_instance_count": 0,
        "claim_allowed": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
    }


def _summary(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA ACTION BUNDLE MULTI-FAMILY REVIEW TAXONOMY LITE V1",
        f"status={payload.get('status')}",
        f"match_surface_binding_id={payload.get('match_surface_binding_id')}",
        f"source_review_bundle_record_count={payload.get('source_review_bundle_record_count')}",
        f"multi_family_review_core_count={payload.get('multi_family_review_core_count')}",
        f"classified_candidate_core_count={payload.get('classified_candidate_core_count')}",
        f"review_required_core_count={payload.get('review_required_core_count')}",
        f"coordinate_missing_core_count={payload.get('coordinate_missing_core_count')}",
        f"classification_counts={payload.get('classification_counts')}",
        f"hard_block_hits={payload.get('hard_block_hits')}",
        f"review_hits={payload.get('review_hits')}",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def _analyst_audit(payload: dict[str, Any]) -> str:
    counts = payload.get("classification_counts") or {}
    lines = [
        "HPFA ANALYST AUDIT — MULTI-FAMILY REVIEW TAXONOMY",
        f"Visible multi-family core surface: {payload.get('multi_family_review_core_count', 0)}",
        f"Exact hierarchical subtype candidates: {counts.get('HIERARCHICAL_SUBTYPE_CANDIDATE', 0)}",
        f"Restart-action coupling candidates: {counts.get('RESTART_ACTION_COUPLING_CANDIDATE', 0)}",
        f"Compound co-occurrence review cores: {counts.get('COMPOUND_ACTION_CO_OCCURRENCE_REVIEW_REQUIRED', 0)}",
        f"Same-time grouping-risk cores: {counts.get('SAME_TIME_GROUPING_RISK_REVIEW_REQUIRED', 0)}",
        f"Complex three-plus-family review cores: {counts.get('MULTI_FAMILY_COMPLEX_REVIEW_REQUIRED', 0)}",
        f"Unregistered exact family-set review cores: {counts.get('UNREGISTERED_FAMILY_SET_REVIEW_REQUIRED', 0)}",
        (
            "Analyst-safe meaning: visible family overlaps are separated into exact "
            "candidate classes without treating any core as a canonical event or "
            "validated physical action."
        ),
        "Cross-role fusion, sequence truth, phase truth and tactical truth remain closed.",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], out: str | Path) -> dict[str, Path]:
    output = validate_out(out)
    output.mkdir(parents=True, exist_ok=True)
    paths = {name: output / filename for name, filename in OUTPUTS.items()}
    paths["json"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["summary"].write_text(_summary(payload), encoding="utf-8")
    paths["analyst"].write_text(_analyst_audit(payload), encoding="utf-8")
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action-bundle", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = build_action_bundle_multi_family_review_taxonomy(load_json(args.action_bundle))
    write_outputs(payload, args.out)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "source_review_bundle_record_count": payload[
                    "source_review_bundle_record_count"
                ],
                "multi_family_review_core_count": payload["multi_family_review_core_count"],
                "classified_candidate_core_count": payload[
                    "classified_candidate_core_count"
                ],
                "review_required_core_count": payload["review_required_core_count"],
                "canonical_event_count": payload["canonical_event_count"],
                "production_release": payload["production_release"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
