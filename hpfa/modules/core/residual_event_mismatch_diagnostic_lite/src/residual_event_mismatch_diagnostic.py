from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

MODULE_ID = "residual_event_mismatch_diagnostic_lite_v1"


def _clean(value: Any) -> str:
    return " ".join("" if value is None else str(value).split()).strip()


def _family(value: Any) -> str:
    return _clean(value).upper()


def diagnose_residual_event_mismatch(
    classifier_payload: dict[str, Any],
    aggregate_payload: dict[str, Any],
) -> dict[str, Any]:
    surface_counts = {
        _family(name): int(value)
        for name, value in (classifier_payload.get("base_event_family_counts") or {}).items()
    }
    aggregate_counts = {
        _family(name): int(value)
        for name, value in (aggregate_payload.get("aggregate_family_counts") or {}).items()
    }
    candidate_routes: dict[str, Counter[str]] = defaultdict(Counter)
    candidate_labels: dict[str, Counter[str]] = defaultdict(Counter)
    label_by_id = {
        item.get("event_label_candidate_id"): item
        for item in classifier_payload.get("event_label_candidates") or []
    }
    for candidate in classifier_payload.get("base_event_surface_candidates") or []:
        family = _family(candidate.get("base_event_family"))
        if not family:
            continue
        route = _clean(candidate.get("source_semantic_route")) or "UNKNOWN_ROUTE"
        candidate_routes[family][route] += 1
        for label_id in candidate.get("event_label_candidate_ids") or []:
            label = label_by_id.get(label_id) or {}
            normalized = _clean(label.get("normalized_label")) or "UNKNOWN_LABEL"
            candidate_labels[family][normalized] += 1
    reflection_counts: Counter[str] = Counter()
    for relation in classifier_payload.get("cross_role_reflection_relations") or []:
        route = _clean(relation.get("source_semantic_route")) or "UNKNOWN_ROUTE"
        reflection_counts[route] += 1
    rows: list[dict[str, Any]] = []
    blocked: list[str] = []
    for family in sorted(set(surface_counts) | set(aggregate_counts)):
        surface = surface_counts.get(family, 0)
        aggregate = aggregate_counts.get(family, 0)
        delta = surface - aggregate
        if delta:
            blocked.append(family)
        rows.append({
            "event_family": family,
            "provisional_surface_count": surface,
            "aggregate_count": aggregate,
            "signed_delta": delta,
            "candidate_source_route_counts": dict(sorted(candidate_routes[family].items())),
            "top_candidate_labels": [
                {"normalized_label": label, "candidate_attachment_count": count}
                for label, count in candidate_labels[family].most_common(20)
            ],
            "diagnostic_status": "EXACT_COUNT_PARITY" if delta == 0 else "RESIDUAL_MISMATCH_REQUIRES_ROW_AUDIT",
        })
    return {
        "module_id": MODULE_ID,
        "runtime_code_head_sha": classifier_payload.get("runtime_code_head_sha"),
        "decision_state": "PASS_NO_RESIDUAL_MISMATCH" if not blocked else "BLOCKED_RESIDUAL_EVENT_MISMATCH",
        "family_diagnostics": rows,
        "blocked_families": blocked,
        "cross_role_reflection_counts": dict(sorted(reflection_counts.items())),
        "diagnostic_scope": "SURFACE_COUNT_CAUSE_LOCALIZATION_ONLY",
        "identity_bound_event_count": 0,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
