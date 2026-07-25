from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "evidence_atom_inventory_lite_v1"
INPUT_MODULE_ID = "row_nucleus_inventory_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "EVIDENCE_ATOM_ONLY"
ALLOWED_SOURCE_ROLES = {
    "GOALKEEPER_SURFACE_CANDIDATE",
    "PLAYER_SURFACE_CANDIDATE",
    "TEAM_SURFACE_CANDIDATE",
}
ROW_ROLE_TO_CLASS = {
    "ACTION_ANCHOR": "ACTION_ANCHOR_ATOM",
    "CONTEXT_INTERVAL": "CONTEXT_INTERVAL_ATOM",
    "PARTICIPATION_INTERVAL": "PARTICIPATION_INTERVAL_ATOM",
    "DERIVED_CONSEQUENCE_CANDIDATE": "DERIVED_CONSEQUENCE_ATOM",
    "TERMINAL_OUTCOME_CANDIDATE": "TERMINAL_OUTCOME_ATOM",
    "OPPONENT_ACTION_REFERENCE": "REFERENCE_ATOM",
    "RECEIVED_ACTION_REFERENCE": "REFERENCE_ATOM",
    "PERIOD_OR_META": "ADMINISTRATIVE_ATOM",
    "ADMINISTRATIVE_MARKER": "ADMINISTRATIVE_ATOM",
}
ROLE_ELIGIBILITY = {
    "ACTION_ANCHOR": {"ACTION_CANDIDATE_ELIGIBLE", "ACTION_CANDIDATE_REVIEW_LIMITED"},
    "CONTEXT_INTERVAL": {"CONTEXT_ONLY"},
    "PARTICIPATION_INTERVAL": {"PARTICIPATION_ONLY"},
    "DERIVED_CONSEQUENCE_CANDIDATE": {"DERIVED_ONLY"},
    "TERMINAL_OUTCOME_CANDIDATE": {"TERMINAL_OUTCOME_ONLY"},
    "OPPONENT_ACTION_REFERENCE": {"REFERENCE_ONLY"},
    "RECEIVED_ACTION_REFERENCE": {"REFERENCE_ONLY"},
    "PERIOD_OR_META": {"ADMIN_ONLY"},
    "ADMINISTRATIVE_MARKER": {"ADMIN_ONLY"},
}
REVIEW_MAPPING_STATUSES = {
    "TOKEN_FALLBACK_REVIEW_REQUIRED",
    "CONFLICT_REVIEW_REQUIRED",
    "UNKNOWN_UNREVIEWED",
}
OUTPUTS = {
    "json": "evidence_atom_inventory_lite_v1.json",
    "summary": "evidence_atom_inventory_lite_v1.txt",
    "analyst": "evidence_atom_inventory_analyst_audit_v1.txt",
}


def _norm_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _norm_label(value: Any) -> str:
    text = _norm_text(value).casefold().replace("%", " percent ")
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text)).strip()


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


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("row_nucleus_output_unreadable_or_malformed") from exc
    if not isinstance(payload, dict):
        raise ValueError("row_nucleus_output_not_object")
    return payload


def _match_surface_binding_id(payload: dict[str, Any]) -> tuple[str | None, list[str]]:
    rows = payload.get("source_binding_audit") or []
    blocks: list[str] = []
    binding_parts: list[tuple[str, str, str]] = []
    if not isinstance(rows, list) or not rows:
        return None, ["source_binding_audit_missing"]
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            blocks.append(f"source_binding_record_invalid:{index}")
            continue
        role = str(row.get("source_role") or "")
        source_format = str(row.get("source_format") or "")
        runtime_sha = row.get("runtime_rehashed_sha256")
        if role not in ALLOWED_SOURCE_ROLES:
            blocks.append(f"source_binding_role_rejected:{role or 'UNKNOWN'}")
        if source_format not in {"csv", "xml"}:
            blocks.append(f"source_binding_format_rejected:{source_format or 'UNKNOWN'}")
        if row.get("audit_sha_match") is not True:
            blocks.append(f"source_binding_sha_not_matched:{index}")
        if not _valid_sha256(runtime_sha):
            blocks.append(f"source_binding_runtime_sha_missing:{index}")
        if role in ALLOWED_SOURCE_ROLES and source_format in {"csv", "xml"} and _valid_sha256(runtime_sha):
            binding_parts.append((role, source_format, str(runtime_sha).casefold()))
    if len(binding_parts) != 6:
        blocks.append(f"source_binding_record_count_invalid:{len(binding_parts)}")
    if blocks:
        return None, sorted(set(blocks))
    return "msb_" + _digest(sorted(binding_parts))[:24], []


def _row_surface_roles(nucleus: dict[str, Any]) -> list[str]:
    return sorted(
        {
            str(role)
            for role in (nucleus.get("semantic_role_candidates") or [])
            if role and str(role) != "AGGREGATE_METRIC_LABEL"
        }
    )


def _classify_nucleus(nucleus: dict[str, Any]) -> tuple[str, str | None, list[str]]:
    reasons: list[str] = []
    roles = _row_surface_roles(nucleus)
    mapping_statuses = {str(item) for item in (nucleus.get("mapping_statuses") or [])}
    eligibilities = {str(item) for item in (nucleus.get("downstream_eligibility_candidates") or [])}
    families = {str(item) for item in (nucleus.get("action_family_candidates") or []) if item}

    if any(status in REVIEW_MAPPING_STATUSES for status in mapping_statuses):
        reasons.append("mapping_status_review_required")
    if len(roles) != 1:
        reasons.append("row_surface_semantic_role_not_single")
        return "REVIEW_REQUIRED_ATOM", None, reasons

    role = roles[0]
    atom_class = ROW_ROLE_TO_CLASS.get(role)
    if atom_class is None:
        reasons.append("row_surface_semantic_role_unregistered")
        return "REVIEW_REQUIRED_ATOM", role, reasons

    allowed_eligibility = ROLE_ELIGIBILITY[role]
    if not (eligibilities & allowed_eligibility):
        reasons.append("role_eligibility_contract_mismatch")
    if role == "ACTION_ANCHOR" and len(families) != 1:
        reasons.append("action_anchor_family_not_single")
    if role != "ACTION_ANCHOR" and families:
        reasons.append("non_action_role_has_action_family")

    if reasons:
        return "REVIEW_REQUIRED_ATOM", role, sorted(set(reasons))
    return atom_class, role, []


def _validate_nucleus(nucleus: dict[str, Any], index: int) -> list[str]:
    blocks: list[str] = []
    nucleus_id = nucleus.get("nucleus_id")
    if not _norm_text(nucleus_id):
        blocks.append(f"nucleus_id_missing:{index}")
    if nucleus.get("source_role") not in ALLOWED_SOURCE_ROLES:
        blocks.append(f"nucleus_source_role_rejected:{index}")
    source_paths = nucleus.get("source_relative_paths") or []
    source_shas = nucleus.get("source_sha256_lineage") or []
    runtime_shas = nucleus.get("runtime_rehashed_sha256") or {}
    if not isinstance(source_paths, list) or len(source_paths) != 2 or not all(_norm_text(v) for v in source_paths):
        blocks.append(f"nucleus_source_paths_invalid:{index}")
    if not isinstance(source_shas, list) or len(source_shas) != 2 or not all(_valid_sha256(v) for v in source_shas):
        blocks.append(f"nucleus_source_sha_lineage_invalid:{index}")
    if not isinstance(runtime_shas, dict) or not _valid_sha256(runtime_shas.get("csv")) or not _valid_sha256(runtime_shas.get("xml")):
        blocks.append(f"nucleus_runtime_sha_lineage_invalid:{index}")
    if isinstance(source_shas, list) and len(source_shas) == 2 and isinstance(runtime_shas, dict):
        if str(source_shas[0]).casefold() != str(runtime_shas.get("csv") or "").casefold():
            blocks.append(f"nucleus_csv_sha_mismatch:{index}")
        if str(source_shas[1]).casefold() != str(runtime_shas.get("xml") or "").casefold():
            blocks.append(f"nucleus_xml_sha_mismatch:{index}")
    if nucleus.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
        blocks.append(f"nucleus_canonical_event_claimed:{index}")
    if nucleus.get("validated_event_identity") is True:
        blocks.append(f"nucleus_validated_event_identity_claimed:{index}")
    return blocks


def build_evidence_atom_inventory(row_nucleus_payload: dict[str, Any]) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if row_nucleus_payload.get("module_id") != INPUT_MODULE_ID:
        blocks.append("row_nucleus_module_id_mismatch")
    if row_nucleus_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("canonical_event_count_claimed_by_input")
    if row_nucleus_payload.get("production_release") is True:
        blocks.append("unexpected_production_claim_by_input")
    if row_nucleus_payload.get("hard_block_hits"):
        blocks.append("row_nucleus_hard_blocks_present")

    nuclei = row_nucleus_payload.get("row_nuclei") or []
    if not isinstance(nuclei, list) or not nuclei:
        blocks.append("row_nucleus_inventory_empty_or_invalid")
        nuclei = []
    expected_count = row_nucleus_payload.get("row_nucleus_candidate_count")
    if expected_count != len(nuclei):
        blocks.append("row_nucleus_count_mismatch")

    binding_id, binding_blocks = _match_surface_binding_id(row_nucleus_payload)
    blocks.extend(binding_blocks)

    seen_ids: set[str] = set()
    for index, nucleus in enumerate(nuclei):
        if not isinstance(nucleus, dict):
            blocks.append(f"row_nucleus_record_invalid:{index}")
            continue
        blocks.extend(_validate_nucleus(nucleus, index))
        nucleus_id = _norm_text(nucleus.get("nucleus_id"))
        if nucleus_id in seen_ids:
            blocks.append(f"duplicate_nucleus_id:{nucleus_id}")
        seen_ids.add(nucleus_id)

    evidence_atoms: list[dict[str, Any]] = []
    if not blocks and binding_id:
        for nucleus in nuclei:
            atom_class, semantic_role, atom_reviews = _classify_nucleus(nucleus)
            aggregate_overlay = "AGGREGATE_METRIC_LABEL" in (nucleus.get("semantic_role_candidates") or [])
            coordinate_status = (
                "COORDINATE_PRESENT"
                if nucleus.get("pos_x_candidate") is not None and nucleus.get("pos_y_candidate") is not None
                else "COORDINATE_MISSING"
            )
            atom_status = "REVIEW_REQUIRED" if atom_reviews or nucleus.get("nucleus_status") != "PASS" else "PASS"
            atom_id = "ea_" + _digest(binding_id, nucleus.get("nucleus_id"))[:24]
            evidence_atoms.append(
                {
                    "evidence_atom_id": atom_id,
                    "match_surface_binding_id": binding_id,
                    "row_nucleus_id": nucleus.get("nucleus_id"),
                    "source_role": nucleus.get("source_role"),
                    "provider_row_id_candidate": nucleus.get("provider_row_id_candidate"),
                    "source_relative_paths": nucleus.get("source_relative_paths"),
                    "source_sha256_lineage": nucleus.get("source_sha256_lineage"),
                    "runtime_rehashed_sha256": nucleus.get("runtime_rehashed_sha256"),
                    "atom_class": atom_class,
                    "raw_label": nucleus.get("action_raw"),
                    "normalized_label": _norm_label(nucleus.get("action_raw")),
                    "semantic_role_candidate": semantic_role,
                    "semantic_role_candidates": nucleus.get("semantic_role_candidates") or [],
                    "action_family_candidates": nucleus.get("action_family_candidates") or [],
                    "outcome_candidates": nucleus.get("outcome_candidates") or [],
                    "downstream_eligibility_candidates": nucleus.get("downstream_eligibility_candidates") or [],
                    "aggregate_overlay_present": aggregate_overlay,
                    "period_candidate": nucleus.get("period_candidate"),
                    "start_candidate": nucleus.get("start_candidate"),
                    "end_candidate": nucleus.get("end_candidate"),
                    "pos_x_candidate": nucleus.get("pos_x_candidate"),
                    "pos_y_candidate": nucleus.get("pos_y_candidate"),
                    "coordinate_evidence_status": coordinate_status,
                    "team_raw_candidate": nucleus.get("team_raw_candidate"),
                    "code_raw": nucleus.get("code_raw"),
                    "cross_format_support_status": nucleus.get("cross_format_support_status"),
                    "mapping_statuses": nucleus.get("mapping_statuses") or [],
                    "mapping_rule_ids": nucleus.get("mapping_rule_ids") or [],
                    "aggregate_definition_dependency": nucleus.get("aggregate_definition_dependency"),
                    "atom_status": atom_status,
                    "review_hits": sorted(set((nucleus.get("review_hits") or []) + atom_reviews)),
                    "event_instance_allowed": False,
                    "identity_binding_allowed": False,
                    "validated_event_identity": False,
                    "canonical_event_count": CANONICAL_EVENT_COUNT,
                    "claim_ceiling": CLAIM_CEILING,
                }
            )

    if len(evidence_atoms) != len(nuclei) and not blocks:
        blocks.append("evidence_atom_count_mismatch")

    atom_review_count = sum(atom.get("atom_status") == "REVIEW_REQUIRED" for atom in evidence_atoms)
    coordinate_missing_count = sum(atom.get("coordinate_evidence_status") == "COORDINATE_MISSING" for atom in evidence_atoms)
    class_counts = Counter(atom.get("atom_class") for atom in evidence_atoms)
    role_counts = Counter(atom.get("semantic_role_candidate") for atom in evidence_atoms)

    input_status = str(row_nucleus_payload.get("module_status") or row_nucleus_payload.get("status") or "UNKNOWN")
    if input_status == "FAIL_CLOSED":
        blocks.append("row_nucleus_input_fail_closed")
    elif input_status == "REVIEW_REQUIRED":
        reviews.append("row_nucleus_upstream_review_required")
    elif input_status != "PASS":
        reviews.append(f"row_nucleus_upstream_status_review:{input_status}")
    if atom_review_count:
        reviews.append("evidence_atom_semantic_review_required")
    if coordinate_missing_count:
        reviews.append("coordinate_surface_missing_preserved")
    if (row_nucleus_payload.get("g01_g18_rollup") or {}).get("status") == "REVIEW_REQUIRED":
        reviews.append("g01_g18_upstream_review_required")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": binding_id,
        "evidence_atoms": evidence_atoms,
        "evidence_atom_count": len(evidence_atoms),
        "evidence_atom_pass_count": len(evidence_atoms) - atom_review_count,
        "evidence_atom_review_required_count": atom_review_count,
        "atom_class_counts": dict(sorted(class_counts.items())),
        "semantic_role_counts": dict(sorted(role_counts.items())),
        "coordinate_missing_atom_count": coordinate_missing_count,
        "row_nucleus_candidate_count": len(nuclei),
        "row_nucleus_count_matches_atom_count": len(nuclei) == len(evidence_atoms),
        "identity_bound_atom_count": 0,
        "identity_unresolved_atom_count": len(evidence_atoms),
        "action_bundle_candidate_count": 0,
        "event_instance_count": 0,
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "active_match_evidence_pass": False,
        "evidence_atom_is_canonical_event": False,
        "validated_event_identity": False,
        "validated_team_identity": False,
        "validated_player_identity": False,
        "identity_binding_allowed": False,
        "base_event_admission_allowed": False,
        "metric_value_output_allowed": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
        "analyst_evidence": {
            "safe_statement": (
                "Visible same-role row nuclei were converted one-to-one into source-bound evidence atom candidates. "
                "These atoms preserve semantic class, coordinate availability and provenance, but they are not canonical events or validated identities."
            )
        },
    }


def render_summary(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "HPFA EVIDENCE ATOM INVENTORY LITE V1",
            f"status={payload.get('status')}",
            f"evidence_atom_count={payload.get('evidence_atom_count')}",
            f"evidence_atom_pass_count={payload.get('evidence_atom_pass_count')}",
            f"evidence_atom_review_required_count={payload.get('evidence_atom_review_required_count')}",
            f"coordinate_missing_atom_count={payload.get('coordinate_missing_atom_count')}",
            f"hard_block_hits={payload.get('hard_block_hits')}",
            "canonical_event_count=UNKNOWN",
            "production_release=false",
            "",
        ]
    )


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> None:
    out = validate_out(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / OUTPUTS["json"]).write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    (out / OUTPUTS["summary"]).write_text(render_summary(payload), encoding="utf-8")
    analyst = (payload.get("analyst_evidence") or {}).get("safe_statement", "")
    (out / OUTPUTS["analyst"]).write_text(
        analyst + "\ncanonical_event_count=UNKNOWN\nproduction_release=false\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--row-nucleus", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = build_evidence_atom_inventory(load_json(args.row_nucleus))
    write_outputs(payload, args.out)
    print(
        json.dumps(
            {
                key: payload.get(key)
                for key in (
                    "status",
                    "evidence_atom_count",
                    "evidence_atom_pass_count",
                    "evidence_atom_review_required_count",
                    "coordinate_missing_atom_count",
                    "canonical_event_count",
                    "production_release",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
