from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "active_match_metric_anatomy_bridge_v1"
OUTPUT_JSON = "active_match_metric_anatomy_bridge_v1.json"
OUTPUT_TXT = "active_match_metric_anatomy_bridge_v1.txt"


def _clean(value: Any) -> str:
    return " ".join(("" if value is None else str(value)).split()).strip()


def _fold(value: Any) -> str:
    return _clean(value).casefold()


def _load(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _xlsx_cells(projection: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for file_row in projection.get("files") or []:
        if not isinstance(file_row, dict):
            continue
        for sheet in file_row.get("sheets") or []:
            if not isinstance(sheet, dict):
                continue
            for row in sheet.get("rows") or []:
                if not isinstance(row, dict):
                    continue
                identity = row.get("identity_candidates") or {}
                entity_candidate = (
                    identity.get("player_raw_candidate")
                    or identity.get("team_raw_candidate")
                    or identity.get("position_raw_candidate")
                )
                for key, metric in (row.get("metric_values") or {}).items():
                    if not isinstance(metric, dict) or metric.get("value_status") != "OBSERVED":
                        continue
                    raw_label = _clean(metric.get("raw_metric_label"))
                    if not raw_label:
                        continue
                    index[_fold(raw_label)].append(
                        {
                            "row_projection_id": row.get("row_projection_id"),
                            "source_role": row.get("source_role"),
                            "source_sha256": row.get("source_sha256"),
                            "normalized_metric_key": key,
                            "raw_metric_label": raw_label,
                            "raw_value": metric.get("raw_value"),
                            "entity_candidate": entity_candidate,
                            "validated_identity": False,
                            "metric_truth": False,
                        }
                    )
    return index


def _occurrence_components(occurrence: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in occurrence.get("action_occurrence_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        if _clean(candidate.get("occurrence_topology")) != "SINGLE_ACTOR_ACTION":
            continue
        for component in candidate.get("semantic_components") or []:
            if not isinstance(component, dict):
                continue
            label = _clean(component.get("label"))
            if not label:
                continue
            index[_fold(label)].append(
                {
                    "action_occurrence_candidate_id": candidate.get("action_occurrence_candidate_id"),
                    "primary_family_candidate": candidate.get("primary_family_candidate"),
                    "team_identity_candidate_id": candidate.get("team_identity_candidate_id"),
                    "actor_identity_candidate_id": candidate.get("actor_identity_candidate_id"),
                    "semantic_rule_id": component.get("semantic_rule_id"),
                    "outcome": component.get("outcome"),
                    "direction": component.get("direction"),
                    "distance": component.get("distance"),
                    "zone_context": component.get("zone_context"),
                    "progression": component.get("progression"),
                    "key_action": component.get("key_action"),
                    "canonical_event_count": "UNKNOWN",
                    "true_action_count": "UNKNOWN",
                }
            )
    return index


def _matches_requirement(candidate: dict[str, Any], requirement: dict[str, Any]) -> bool:
    family = _clean(requirement.get("action_family_candidate")).upper()
    outcome = _clean(requirement.get("outcome_candidate")).upper()
    if family and _clean(candidate.get("primary_family_candidate")).upper() != family:
        return False
    attributes = candidate.get("attributes") or {}
    if outcome and _clean(attributes.get("outcome_candidate")).upper() != outcome:
        return False
    return True


def build_metric_anatomy(
    occurrence_payload: dict[str, Any],
    xlsx_projection_payload: dict[str, Any],
    metric_dictionary_payload: dict[str, Any],
    aggregate_alignment_payload: dict[str, Any],
) -> dict[str, Any]:
    review_hits: list[str] = []
    hard_blocks: list[str] = []

    if occurrence_payload.get("module_id") != "action_occurrence_admission_lite_v1":
        review_hits.append("occurrence_output_missing_or_unresolved")
    if xlsx_projection_payload.get("module_id") != "xlsx_entity_metric_row_projection_lite_v1":
        review_hits.append("xlsx_projection_missing_or_unresolved")
    if not isinstance(metric_dictionary_payload.get("metrics"), list):
        hard_blocks.append("metric_dictionary_metrics_missing")

    xlsx_index = _xlsx_cells(xlsx_projection_payload)
    occurrence_index = _occurrence_components(occurrence_payload)

    label_anatomy: list[dict[str, Any]] = []
    for metric in metric_dictionary_payload.get("metrics") or []:
        if not isinstance(metric, dict) or _clean(metric.get("provider_id")) == "hpfa":
            continue
        raw_labels = [_clean(value) for value in metric.get("raw_labels") or [] if _clean(value)]
        for raw_label in raw_labels:
            aggregate_refs = xlsx_index.get(_fold(raw_label), [])
            micro_refs = occurrence_index.get(_fold(raw_label), [])
            if not aggregate_refs and not micro_refs:
                continue
            if aggregate_refs and micro_refs:
                anatomy_status = (
                    "SURFACE_ANATOMY_CANDIDATE_DEFINITION_BOUND"
                    if metric.get("definition_evidence_status") == "REVIEWED_PROVIDER_DEFINITION"
                    else "SURFACE_ANATOMY_CANDIDATE_PROVIDER_DEFINITION_REQUIRED"
                )
            elif aggregate_refs:
                anatomy_status = "MICRO_OCCURRENCE_COVERAGE_GAP_REVIEW_REQUIRED"
            else:
                anatomy_status = "AGGREGATE_SURFACE_COVERAGE_GAP_REVIEW_REQUIRED"
            if "REVIEW_REQUIRED" in anatomy_status or anatomy_status.endswith("PROVIDER_DEFINITION_REQUIRED"):
                review_hits.append("metric_anatomy_provider_definition_or_coverage_review_required")

            label_anatomy.append(
                {
                    "metric_id": metric.get("metric_id"),
                    "provider_id": metric.get("provider_id"),
                    "provider_version": metric.get("provider_version"),
                    "raw_label": raw_label,
                    "metric_family": metric.get("metric_family"),
                    "construct": metric.get("construct"),
                    "semantic_type": metric.get("semantic_type"),
                    "unit": metric.get("unit"),
                    "definition_evidence_status": metric.get("definition_evidence_status"),
                    "anatomy_status": anatomy_status,
                    "micro_occurrence_candidate_count": len(micro_refs),
                    "micro_occurrence_candidates": micro_refs[:100],
                    "aggregate_cell_candidate_count": len(aggregate_refs),
                    "aggregate_cell_candidates": aggregate_refs[:100],
                    "micro_to_aggregate_identity_binding_admitted": False,
                    "same_provider_cross_surface_dependency": "NON_INDEPENDENT",
                    "same_label_is_same_definition": False,
                    "numeric_reconciliation_performed": False,
                    "count_parity_is_definition_equivalence": False,
                    "metric_value_output_allowed": False,
                    "claim_allowed": False,
                    "claim_ceiling": "MICRO_AGGREGATE_SURFACE_ANATOMY_CANDIDATE_ONLY",
                }
            )

    occurrence_candidates = [
        row
        for row in occurrence_payload.get("action_occurrence_candidates") or []
        if isinstance(row, dict)
    ]
    definition_anatomy: list[dict[str, Any]] = []
    for alignment in aggregate_alignment_payload.get("alignment_rows") or []:
        if not isinstance(alignment, dict):
            continue
        coverage: list[dict[str, Any]] = []
        for support in alignment.get("semantic_support") or []:
            if not isinstance(support, dict):
                continue
            requirement = support.get("requirement") or {}
            matches = [
                row for row in occurrence_candidates
                if isinstance(requirement, dict) and _matches_requirement(row, requirement)
            ]
            coverage.append(
                {
                    "requirement": requirement,
                    "grammar_occurrence_candidate_count": len(matches),
                    "grammar_occurrence_candidate_ids": [
                        row.get("action_occurrence_candidate_id") for row in matches[:100]
                    ],
                    "provider_label_semantic_match_count": support.get("match_count"),
                    "provider_bound_semantic_match_count": support.get("provider_bound_match_count"),
                }
            )
        definition_anatomy.append(
            {
                "definition_id": alignment.get("definition_id"),
                "metric_id": alignment.get("metric_id"),
                "aggregate_label": alignment.get("aggregate_label"),
                "alignment_decision": alignment.get("alignment_decision"),
                "definition_evidence_status": alignment.get("definition_evidence_status"),
                "required_semantic_coverage": coverage,
                "denominator_coverage_complete": False,
                "rate_calculation_admitted": False,
                "numeric_reconciliation_performed": False,
                "aggregate_mismatch_action": "AUDIT_DEFINITION_SCOPE_DENOMINATOR_NOT_ROW_DELETION",
                "claim_allowed": False,
                "claim_ceiling": "AGGREGATE_DEFINITION_ANATOMY_CANDIDATE_ONLY",
            }
        )

    linked = sum(
        1
        for row in label_anatomy
        if row.get("micro_occurrence_candidate_count") and row.get("aggregate_cell_candidate_count")
    )
    status = "FAIL_CLOSED" if hard_blocks else ("REVIEW_REQUIRED" if review_hits else "SMOKE_PASS")
    return {
        "module_id": MODULE_ID,
        "status": status,
        "label_surface_anatomy_candidate_count": len(label_anatomy),
        "micro_aggregate_linked_label_candidate_count": linked,
        "definition_anatomy_candidate_count": len(definition_anatomy),
        "label_surface_anatomy_candidates": label_anatomy,
        "definition_anatomy_candidates": definition_anatomy,
        "hard_block_hits": sorted(set(hard_blocks)),
        "review_hits": sorted(set(review_hits)),
        "xlsx_creates_action_identity": False,
        "csv_xml_xlsx_are_independent_evidence_votes": False,
        "aggregate_mismatch_means_bad_rows": False,
        "aggregate_mismatch_requires_definition_scope_denominator_audit": True,
        "metric_value_output_allowed": False,
        "numeric_reconciliation_allowed": False,
        "construct_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def write_metric_anatomy(
    out_dir: str | Path,
    product_root: str | Path,
    aggregate_alignment_payload: dict[str, Any],
) -> dict[str, Any]:
    output = Path(out_dir).expanduser().resolve(strict=False)
    root = Path(product_root).expanduser().resolve(strict=False)
    occurrence = _load(output / "action_occurrence_admission_lite_v1.json")
    xlsx_projection = _load(output / "xlsx_entity_metric_row_projection_lite_v1.json")
    dictionary = _load(root / "configs" / "metrics" / "provider_metric_dictionary_v1.json")
    report = build_metric_anatomy(occurrence, xlsx_projection, dictionary, aggregate_alignment_payload)

    json_path = output / OUTPUT_JSON
    txt_path = output / OUTPUT_TXT
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    txt_path.write_text(
        "\n".join(
            [
                "HPFA ACTIVE_MATCH METRIC ANATOMY BRIDGE V1",
                "===========================================",
                f"status={report['status']}",
                f"label_surface_anatomy_candidate_count={report['label_surface_anatomy_candidate_count']}",
                f"micro_aggregate_linked_label_candidate_count={report['micro_aggregate_linked_label_candidate_count']}",
                f"definition_anatomy_candidate_count={report['definition_anatomy_candidate_count']}",
                f"review_hits={report['review_hits']}",
                "xlsx_creates_action_identity=false",
                "csv_xml_xlsx_are_independent_evidence_votes=false",
                "numeric_reconciliation_allowed=false",
                "canonical_event_count=UNKNOWN",
                "true_action_count=UNKNOWN",
                "production_release=false",
                "",
            ]
        ),
        encoding="utf-8",
    )
    report["current_invocation_artifacts"] = [str(json_path), str(txt_path)]
    return report
