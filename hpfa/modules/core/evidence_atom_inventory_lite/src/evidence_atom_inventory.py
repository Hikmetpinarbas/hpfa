from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from hpfa.modules.core.provider_label_value_semantics_lite.src import (
    provider_label_value_semantics as semantics,
)

MODULE_ID = "evidence_atom_inventory_lite_v1"
INPUT_MODULE_ID = "row_nucleus_inventory_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "EVIDENCE_ATOM_CANDIDATE_ONLY"
OUTPUT_JSON = "evidence_atom_inventory_lite_v1.json"
OUTPUT_TXT = "evidence_atom_inventory_lite_v1.txt"
ANALYST_TXT = "evidence_atom_inventory_analyst_audit_v1.txt"

SHORT_TO_SOURCE_ROLE = {
    "PLAYER": "PLAYER_SURFACE_CANDIDATE",
    "GOALKEEPER": "GOALKEEPER_SURFACE_CANDIDATE",
    "TEAM": "TEAM_SURFACE_CANDIDATE",
}

ROLE_TO_ATOM_CLASS = {
    "ACTION_ANCHOR": "ACTION_ANCHOR_ATOM",
    "CONTEXT_INTERVAL": "CONTEXT_INTERVAL_ATOM",
    "PARTICIPATION_INTERVAL": "PARTICIPATION_INTERVAL_ATOM",
    "DERIVED_CONSEQUENCE_CANDIDATE": "DERIVED_CONSEQUENCE_ATOM",
    "TERMINAL_OUTCOME_CANDIDATE": "TERMINAL_OUTCOME_ATOM",
    "OPPONENT_ACTION_REFERENCE": "REFERENCE_ATOM",
    "RECEIVED_ACTION_REFERENCE": "REFERENCE_ATOM",
    "ATTRIBUTE_REFERENCE": "REFERENCE_ATOM",
    "PERIOD_OR_META": "ADMINISTRATIVE_ATOM",
    "ADMINISTRATIVE_MARKER": "ADMINISTRATIVE_ATOM",
    "MATCH_BOUNDARY": "ADMINISTRATIVE_ATOM",
}

ADMIN_ROLES = {"PERIOD_OR_META", "ADMINISTRATIVE_MARKER", "MATCH_BOUNDARY"}
SEMANTIC_REVIEW_STATES = {
    "TOKEN_FALLBACK_REVIEW_REQUIRED",
    "CONFLICT_REVIEW_REQUIRED",
    "UNKNOWN_UNREVIEWED",
}


def stable_id(*parts: Any) -> str:
    raw = json.dumps(parts, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_output_root(path: str | Path) -> Path:
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


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _resolved(nucleus: dict[str, Any], field: str) -> str | None:
    value = (nucleus.get("resolved_visible_fields") or {}).get(field)
    return _clean(value) or None


def _semantic_record(nucleus: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    short_role = _clean(nucleus.get("source_role"))
    source_role = SHORT_TO_SOURCE_ROLE.get(short_role, "UNKNOWN")
    raw_label = _resolved(nucleus, "action") or ""
    return semantics.classify_label(
        raw_label,
        source_format="csv",
        registry=registry,
        source_role=source_role,
    )


def _source_lineage(
    nucleus: dict[str, Any],
    input_root: Path,
    hash_cache: dict[str, str],
) -> tuple[list[dict[str, Any]], list[str]]:
    blocks: list[str] = []
    records: list[dict[str, Any]] = []
    refs = nucleus.get("source_refs") or []
    if not isinstance(refs, list) or not refs:
        return [], ["source_refs_missing"]

    expected_role = _clean(nucleus.get("source_role"))
    seen: set[tuple[str, str]] = set()
    for index, ref in enumerate(refs):
        if not isinstance(ref, dict):
            blocks.append(f"source_ref_invalid:{index}")
            continue
        source_file = _clean(ref.get("source_file"))
        source_format = _clean(ref.get("source_format")).casefold()
        source_role = _clean(ref.get("source_role"))
        if not source_file:
            blocks.append(f"source_file_missing:{index}")
            continue
        if source_format not in {"csv", "tsv", "xml"}:
            blocks.append(f"source_format_rejected:{source_format or 'UNKNOWN'}")
            continue
        if source_role != expected_role:
            blocks.append(f"source_role_mismatch:{source_role or 'UNKNOWN'}:{expected_role or 'UNKNOWN'}")
            continue
        key = (source_file, source_format)
        if key in seen:
            blocks.append(f"duplicate_source_ref:{source_file}:{source_format}")
            continue
        seen.add(key)
        path = input_root / source_file
        if not path.is_file():
            blocks.append(f"runtime_source_file_missing:{source_file}")
            continue
        if source_file not in hash_cache:
            hash_cache[source_file] = file_sha256(path)
        records.append(
            {
                "source_file": source_file,
                "source_format": source_format,
                "source_role": source_role,
                "source_row_index": ref.get("source_row_index"),
                "source_sha256": hash_cache[source_file],
                "source_row_index_is_order_truth": False,
            }
        )
    return sorted(records, key=lambda item: (item["source_format"], item["source_file"])), sorted(set(blocks))


def _binding_from_lineage(records: list[dict[str, Any]]) -> tuple[str | None, list[str]]:
    blocks: list[str] = []
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in records:
        key = (
            _clean(record.get("source_role")),
            _clean(record.get("source_format")).casefold(),
            _clean(record.get("source_sha256")).casefold(),
        )
        unique[key] = record

    expected_pairs = {
        (role, fmt)
        for role in ("PLAYER", "GOALKEEPER", "TEAM")
        for fmt in ("csv", "xml")
    }
    observed_pairs = {(role, fmt) for role, fmt, _sha in unique}
    if observed_pairs != expected_pairs:
        blocks.append(
            "match_surface_binding_role_format_set_mismatch:"
            + json.dumps(sorted(observed_pairs), separators=(",", ":"))
        )
    if len(unique) != 6:
        blocks.append(f"match_surface_binding_unique_source_count_invalid:{len(unique)}")
    if blocks:
        return None, sorted(set(blocks))
    binding_seed = sorted((role, fmt, sha) for role, fmt, sha in unique)
    return "msb_" + stable_id("current_row_nucleus_binding_v1", binding_seed)[:24], []


def _atom_class(
    nucleus: dict[str, Any],
    semantic: dict[str, Any],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    semantic_role = _clean(semantic.get("semantic_role_candidate"))
    mapping_status = _clean(semantic.get("mapping_status"))
    atom_class = ROLE_TO_ATOM_CLASS.get(semantic_role)
    if atom_class is None:
        reasons.append("semantic_role_not_admitted_to_atom_class")
        atom_class = "REVIEW_REQUIRED_ATOM"
    if mapping_status in SEMANTIC_REVIEW_STATES:
        reasons.append("semantic_mapping_review_required")
    if atom_class == "ACTION_ANCHOR_ATOM" and not _clean(semantic.get("action_family_candidate")):
        reasons.append("action_anchor_family_missing")
    if nucleus.get("status") == "REVIEW_REQUIRED":
        reasons.extend(str(item) for item in (nucleus.get("review_reasons") or []))
    elif nucleus.get("status") != "PASS":
        reasons.append(f"row_nucleus_status_not_admitted:{nucleus.get('status')}")
    if nucleus.get("lineage_admission_status") == "LINEAGE_REVIEW_REQUIRED":
        reasons.extend(str(item) for item in (nucleus.get("lineage_review_reasons") or []))
    return atom_class, sorted(set(reasons))


def build_evidence_atom_inventory(
    row_payload: dict[str, Any],
    input_dir: str | Path,
    registry: dict[str, Any],
) -> dict[str, Any]:
    input_root = Path(input_dir).expanduser().resolve(strict=False)
    blocks: list[str] = []
    reviews: list[str] = []

    if row_payload.get("module_id") != INPUT_MODULE_ID:
        blocks.append("row_nucleus_module_id_mismatch")
    if row_payload.get("content_source_role_bridge_status") != "PASS":
        blocks.append("content_source_role_bridge_not_pass")
    if row_payload.get("filename_support_used_for_role_admission") is True:
        blocks.append("filename_role_admission_reintroduced")
    if row_payload.get("filename_role_used_for_nucleus_grouping") is True:
        blocks.append("filename_role_grouping_reintroduced")
    if row_payload.get("xlsx_used_for_row_nucleus_identity") is True:
        blocks.append("xlsx_row_identity_reintroduced")
    if row_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("canonical_event_count_claimed_by_input")
    if row_payload.get("physical_action_identity_truth") is True:
        blocks.append("physical_action_identity_claimed_by_input")
    if row_payload.get("independent_source_vote_allowed") is True:
        blocks.append("independent_source_vote_claimed_by_input")
    if row_payload.get("production_release") is True:
        blocks.append("unexpected_production_claim_by_input")
    if not input_root.is_dir():
        blocks.append("runtime_input_root_missing")

    nuclei = row_payload.get("row_nuclei") or []
    if not isinstance(nuclei, list) or not nuclei:
        blocks.append("row_nucleus_inventory_empty_or_invalid")
        nuclei = []
    if row_payload.get("row_nucleus_candidate_count") != len(nuclei):
        blocks.append("row_nucleus_count_mismatch")

    seen_ids: set[str] = set()
    hash_cache: dict[str, str] = {}
    atom_inputs: list[tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]] = []
    all_lineage_records: list[dict[str, Any]] = []

    for index, nucleus in enumerate(nuclei):
        if not isinstance(nucleus, dict):
            blocks.append(f"row_nucleus_record_invalid:{index}")
            continue
        nucleus_id = _clean(nucleus.get("row_nucleus_candidate_id"))
        if not nucleus_id:
            blocks.append(f"row_nucleus_candidate_id_missing:{index}")
        elif nucleus_id in seen_ids:
            blocks.append(f"duplicate_row_nucleus_candidate_id:{nucleus_id}")
        seen_ids.add(nucleus_id)
        if nucleus.get("source_role") not in SHORT_TO_SOURCE_ROLE:
            blocks.append(f"row_nucleus_source_role_rejected:{index}")
        if nucleus.get("provider_row_id_is_validated_identity") is True:
            blocks.append(f"provider_row_id_promoted_to_identity:{index}")
        if nucleus.get("row_nucleus_is_canonical_event") is True:
            blocks.append(f"row_nucleus_promoted_to_canonical_event:{index}")
        if nucleus.get("physical_action_identity_truth") is True:
            blocks.append(f"row_nucleus_promoted_to_physical_action:{index}")
        if nucleus.get("validated_event_identity") is True:
            blocks.append(f"row_nucleus_validated_event_identity_claimed:{index}")
        if nucleus.get("independent_source_vote_allowed") is True:
            blocks.append(f"row_nucleus_independent_vote_claimed:{index}")

        lineage, lineage_blocks = _source_lineage(nucleus, input_root, hash_cache)
        blocks.extend(f"{reason}:{index}" for reason in lineage_blocks)
        all_lineage_records.extend(lineage)
        semantic = _semantic_record(nucleus, registry)
        atom_inputs.append((nucleus, lineage, semantic))

    binding_id, binding_blocks = _binding_from_lineage(all_lineage_records)
    blocks.extend(binding_blocks)
    blocks = sorted(set(blocks))

    atoms: list[dict[str, Any]] = []
    if not blocks and binding_id:
        for nucleus, lineage, semantic in atom_inputs:
            atom_class, atom_reviews = _atom_class(nucleus, semantic)
            semantic_role = _clean(semantic.get("semantic_role_candidate")) or None
            action_family = _clean(semantic.get("action_family_candidate")) or None
            outcome = _clean(semantic.get("outcome_candidate")) or None
            downstream = _clean(semantic.get("downstream_eligibility")) or None
            is_admin = semantic_role in ADMIN_ROLES or downstream == "ADMIN_ONLY"
            relation = _clean(nucleus.get("serialization_relation_candidate"))
            if relation in {"REFLECTION_CANDIDATE_EXACT", "REFLECTION_CANDIDATE_DISCREPANCY"}:
                independence_state = "DEPENDENT_SERIALIZATION_REFLECTION"
            else:
                independence_state = "INDEPENDENCE_UNKNOWN_REVIEW_REQUIRED"
                atom_reviews.append("source_independence_unknown_review_required")

            if is_admin:
                atom_class = "ADMINISTRATIVE_ATOM"
                action_eligible = False
                downstream = "ADMIN_ONLY"
            else:
                action_eligible = (
                    atom_class == "ACTION_ANCHOR_ATOM"
                    and not atom_reviews
                    and nucleus.get("status") == "PASS"
                )

            source_paths = [item["source_file"] for item in lineage]
            source_shas = [item["source_sha256"] for item in lineage]
            runtime_shas = {
                item["source_format"]: item["source_sha256"]
                for item in lineage
                if item["source_format"] in {"csv", "xml"}
            }
            resolved = nucleus.get("resolved_visible_fields") or {}
            atom_status = "REVIEW_REQUIRED" if atom_reviews else "PASS"
            atom_id = "ea_" + stable_id(
                "current_evidence_atom_v1",
                binding_id,
                nucleus.get("row_nucleus_candidate_id"),
            )[:24]
            atoms.append(
                {
                    "evidence_atom_id": atom_id,
                    "match_surface_binding_id": binding_id,
                    "row_nucleus_candidate_id": nucleus.get("row_nucleus_candidate_id"),
                    "source_role": SHORT_TO_SOURCE_ROLE[str(nucleus.get("source_role"))],
                    "source_role_short": nucleus.get("source_role"),
                    "role_projection_candidate": nucleus.get("role_projection_candidate"),
                    "provider_row_id_candidate": nucleus.get("provider_row_id_candidate"),
                    "provider_row_id_representation_preserved": True,
                    "source_refs": nucleus.get("source_refs") or [],
                    "source_lineage_records": lineage,
                    "source_relative_paths": source_paths,
                    "source_sha256_lineage": source_shas,
                    "runtime_rehashed_sha256": runtime_shas,
                    "serialization_relation_candidate": nucleus.get("serialization_relation_candidate"),
                    "reflection_dependency_state": independence_state,
                    "independent_support_vote_count": 0,
                    "independent_source_vote_allowed": False,
                    "atom_class": atom_class,
                    "atom_status": atom_status,
                    "semantic_role_candidate": semantic_role,
                    "semantic_mapping_status": semantic.get("mapping_status"),
                    "semantic_rule_id": semantic.get("rule_id"),
                    "action_family_candidates": [action_family] if action_family else [],
                    "outcome_candidates": [outcome] if outcome else [],
                    "direction_candidate": semantic.get("direction_candidate"),
                    "distance_candidate": semantic.get("distance_candidate"),
                    "zone_candidate": semantic.get("zone_candidate"),
                    "context_candidate": semantic.get("context_candidate"),
                    "relation_candidate": semantic.get("relation_candidate"),
                    "downstream_eligibility": downstream,
                    "raw_label": _resolved(nucleus, "action"),
                    "normalized_label": semantics.normalize_label(_resolved(nucleus, "action") or ""),
                    "period_candidate": _resolved(nucleus, "half"),
                    "start_candidate": _resolved(nucleus, "start"),
                    "end_candidate": _resolved(nucleus, "end"),
                    "pos_x_candidate": _resolved(nucleus, "pos_x"),
                    "pos_y_candidate": _resolved(nucleus, "pos_y"),
                    "team_raw_candidate": _resolved(nucleus, "team"),
                    "code_raw": _resolved(nucleus, "code"),
                    "visible_field_candidates": nucleus.get("visible_field_candidates") or {},
                    "resolved_visible_fields": resolved,
                    "review_hits": sorted(set(atom_reviews)),
                    "reflection_discrepancy_preserved": bool(
                        relation == "REFLECTION_CANDIDATE_DISCREPANCY"
                        or nucleus.get("mismatch_fields")
                    ),
                    "action_eligible": action_eligible,
                    "sequence_eligible": False,
                    "spatial_eligible": False,
                    "metric_event_denominator_eligible": False,
                    "identity_binding_allowed": False,
                    "identity_not_applicable": is_admin,
                    "event_instance_allowed": False,
                    "cross_role_fusion_allowed": False,
                    "same_time_link_allowed": False,
                    "negative_time_link_allowed": False,
                    "cross_period_link_allowed": False,
                    "source_timeline_evidence_only": True,
                    "physical_action_identity_truth": False,
                    "validated_event_identity": False,
                    "canonical_event_count": CANONICAL_EVENT_COUNT,
                    "claim_ceiling": CLAIM_CEILING,
                }
            )

    if not blocks and len(atoms) != len(nuclei):
        blocks.append("evidence_atom_count_mismatch")

    pass_count = sum(item.get("atom_status") == "PASS" for item in atoms)
    review_count = sum(item.get("atom_status") == "REVIEW_REQUIRED" for item in atoms)
    class_counts = Counter(str(item.get("atom_class")) for item in atoms)
    role_counts = Counter(str(item.get("semantic_role_candidate")) for item in atoms)
    if row_payload.get("status") == "REVIEW_REQUIRED":
        reviews.append("row_nucleus_upstream_review_required")
    elif row_payload.get("status") == "FAIL_CLOSED":
        blocks.append("row_nucleus_input_fail_closed")
    if review_count:
        reviews.append("evidence_atom_review_required_records_present")

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
        "source_row_nucleus_candidate_count": len(nuclei),
        "evidence_atom_count": len(atoms),
        "evidence_atom_pass_count": pass_count,
        "evidence_atom_review_required_count": review_count,
        "atom_class_counts": dict(sorted(class_counts.items())),
        "semantic_role_counts": dict(sorted(role_counts.items())),
        "evidence_atoms": atoms,
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "one_row_nucleus_one_evidence_atom_candidate": True,
        "dependent_reflection_adds_support_vote": False,
        "xlsx_row_identity_allowed": False,
        "source_row_index_is_temporal_order_truth": False,
        "same_time_artificial_order_allowed": False,
        "event_instance_count": 0,
        "event_instance_allowed": False,
        "cross_role_fusion_allowed": False,
        "validated_team_identity": False,
        "validated_player_identity": False,
        "validated_event_identity": False,
        "physical_action_identity_truth": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def summary(payload: dict[str, Any]) -> str:
    lines = [
        "HPFA EVIDENCE ATOM INVENTORY LITE V1 — CURRENT ROW NUCLEUS MIGRATION",
        f"status={payload.get('status')}",
        f"source_row_nucleus_candidate_count={payload.get('source_row_nucleus_candidate_count')}",
        f"evidence_atom_count={payload.get('evidence_atom_count')}",
        f"evidence_atom_pass_count={payload.get('evidence_atom_pass_count')}",
        f"evidence_atom_review_required_count={payload.get('evidence_atom_review_required_count')}",
        f"atom_class_counts={json.dumps(payload.get('atom_class_counts') or {}, sort_keys=True)}",
        f"hard_block_hits={payload.get('hard_block_hits')}",
        f"review_hits={payload.get('review_hits')}",
        "canonical_event_count=UNKNOWN",
        "physical_action_identity_truth=false",
        "production_release=false",
        "",
    ]
    return "\n".join(lines)


def analyst_audit(payload: dict[str, Any]) -> str:
    classes = payload.get("atom_class_counts") or {}
    return "\n".join(
        [
            "HPFA ANALYST AUDIT — EVIDENCE ATOM CURRENT MIGRATION",
            f"Evidence atom candidates: {payload.get('evidence_atom_count', 0)}",
            f"Action-anchor atom candidates: {classes.get('ACTION_ANCHOR_ATOM', 0)}",
            f"Administrative atom candidates: {classes.get('ADMINISTRATIVE_ATOM', 0)}",
            f"Review-required atom candidates: {payload.get('evidence_atom_review_required_count', 0)}",
            "Safe meaning: each current Row Nucleus is preserved as one source-bound evidence candidate; CSV/XML reflections do not multiply the atom count.",
            "Administrative and match-boundary surfaces may receive an administrative role while their serialization review state remains visible.",
            "No evidence atom is a canonical event or physical action truth. TEAM/PLAYER/GOALKEEPER cross-role fusion remains closed.",
            "Same-time records are not ordered here. XLSX creates no row or action identity.",
            "canonical_event_count=UNKNOWN",
            "production_release=false",
            "",
        ]
    )


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    output = validate_output_root(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": output / OUTPUT_JSON,
        "summary": output / OUTPUT_TXT,
        "analyst": output / ANALYST_TXT,
    }
    paths["json"].write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths["summary"].write_text(summary(payload), encoding="utf-8")
    paths["analyst"].write_text(analyst_audit(payload), encoding="utf-8")
    return paths
