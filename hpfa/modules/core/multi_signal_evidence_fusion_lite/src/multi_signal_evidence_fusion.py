from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "multi_signal_evidence_fusion_lite_v1"
OUTPUT_JSON = "multi_signal_evidence_fusion_lite_v1.json"
OUTPUT_TXT = "multi_signal_evidence_fusion_lite_v1.txt"

CANDIDATE_ONLY_CLAIM_CEILING = "composite_candidate_only"
FUSION_CLAIM_CEILING = "fusion_relation_candidate_only"
MISSING_PACKET_ID = "MISSING_PACKET_ID"

RELATION_TYPES = {
    "SUPPORTS",
    "CONTRADICTS",
    "QUALIFIES",
    "COMPLEMENTS",
    "CONTEXTUALIZES",
    "ABSTAINS",
}

BLOCKED_LANGUAGE_FAMILIES = [
    "tactical_truth",
    "dominance_truth",
    "control_truth",
    "coach_intention",
    "off_ball_truth",
    "pitch_control_truth",
    "causal_truth",
]

FORBIDDEN_PACKET_FIELDS = {
    "claim_text",
    "safe_sentence",
    "safe_sentence_candidate_tr",
    "tactical_truth",
    "dominance_truth",
    "control_truth",
    "coach_intention",
    "off_ball_truth",
    "pitch_control_truth",
    "causal_truth",
}

EVIDENCE_GROUP_KEYS = {
    "input_features",
    "input_windows",
    "input_sequences",
    "input_metrics",
    "supporting_signals",
    "contradicting_signals",
}
SUPPORT_BEARING_GROUP_KEYS = {
    "input_features",
    "input_sequences",
    "input_metrics",
    "supporting_signals",
}
ALLOWED_DEPENDENCY_STATES = {
    "INDEPENDENT_SUPPORT_ADMITTED",
    "DEPENDENT_OR_PARTIAL_LINEAGE",
    "INDEPENDENCE_UNKNOWN",
}
ADMITTED_INDEPENDENCE_STATES = {"INDEPENDENCE_ADMITTED", "PARTIAL_INDEPENDENCE_ADMITTED"}
SIGNAL_RECORD_KEYS = {
    "supporting_signals": "supporting_signal_records",
    "contradicting_signals": "contradicting_signal_records",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _validate_output_root(out_dir: str | Path) -> Path:
    spine_src = _repo_root() / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    if str(spine_src) not in sys.path:
        sys.path.insert(0, str(spine_src))
    from spine_runner import validate_output_root  # type: ignore

    return validate_output_root(out_dir)


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _packet_id(packet: dict[str, Any]) -> str:
    return str(packet.get("packet_id") or "")


def _ref_from_item(item: Any, fallback_prefix: str, idx: int) -> str:
    if isinstance(item, dict):
        for key in ["signal_ref", "signal_id", "ref_id", "id", "feature_id", "window_id", "metric_id", "sequence_id"]:
            if item.get(key) not in [None, ""]:
                return str(item[key])
    if item not in [None, ""]:
        return str(item)
    return f"{fallback_prefix}_{idx}"


def _items(packet: dict[str, Any], key: str) -> list[Any]:
    return [item for item in _as_list(packet.get(key)) if item not in [None, ""]]


def _signal_ref_counter(items: list[Any], key: str) -> Counter[str]:
    return Counter(_ref_from_item(item, key, idx) for idx, item in enumerate(items))


def _validate_preserved_signal_bindings(packet: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for group_name, record_key in SIGNAL_RECORD_KEYS.items():
        preserved = _items(packet, record_key)
        if not preserved:
            continue
        canonical = _items(packet, group_name)
        if _signal_ref_counter(canonical, group_name) != _signal_ref_counter(preserved, group_name):
            errors.append(f"upstream_preserved_signal_ref_binding_mismatch:{group_name}")
    return sorted(set(errors))


def _signal_items(packet: dict[str, Any], key: str) -> list[Any]:
    canonical = _items(packet, key)
    record_key = SIGNAL_RECORD_KEYS.get(key)
    if not record_key:
        return canonical
    preserved = _items(packet, record_key)
    if not preserved:
        return canonical
    if _signal_ref_counter(canonical, key) != _signal_ref_counter(preserved, key):
        return canonical
    return preserved


def _refs(packet: dict[str, Any], key: str) -> list[str]:
    return [_ref_from_item(item, key, idx) for idx, item in enumerate(_items(packet, key))]


def _is_forbidden_value(value: Any) -> bool:
    return value not in [None, "", False, []]


def _collect_forbidden_hits(value: Any, path: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key in FORBIDDEN_PACKET_FIELDS and _is_forbidden_value(child):
                hits.append(child_path)
            hits.extend(_collect_forbidden_hits(child, child_path))
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            child_path = f"{path}[{idx}]" if path else f"[{idx}]"
            hits.extend(_collect_forbidden_hits(child, child_path))
    return hits


def _forbidden_packet_hits(packet: dict[str, Any]) -> list[str]:
    return sorted(set(_collect_forbidden_hits(packet)))


def _required_packet_missing(packet: dict[str, Any]) -> list[str]:
    required = [
        "packet_id",
        "packet_family",
        "input_features",
        "input_windows",
        "input_metrics",
        "supporting_signals",
        "contradicting_signals",
        "claim_ceiling",
    ]
    return [key for key in required if packet.get(key) in [None, ""]]


def _upstream_packet_failed(packet: dict[str, Any]) -> bool:
    if _as_list(packet.get("hard_block_hits")):
        return True
    if str(packet.get("decision") or "").upper().startswith("BLOCK"):
        return True
    if str(packet.get("status") or "").upper() in {"FAIL_CLOSED", "BLOCKED"}:
        return True
    return False


def _is_explicit_contradiction(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    relation_type = str(item.get("relation_type") or "").upper()
    if relation_type == "CONTRADICTS":
        return True
    if item.get("explicit_contradiction") is True:
        return True
    if item.get("contradiction_basis") not in [None, "", []]:
        return True
    return False


def _lineage_fields(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {}
    fields: dict[str, Any] = {}
    for key in ["provenance_root", "dependency_group", "independence_group"]:
        value = item.get(key)
        if value not in [None, ""]:
            fields[key] = str(value)
    if item.get("independent_support_vote") is True:
        fields["independent_support_vote"] = True
    return fields


def _record(
    packet_id: str,
    signal_ref: str,
    relation_type: str,
    evidence_role: str,
    relation_basis: str = "",
    lineage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "packet_id": packet_id,
        "signal_ref": signal_ref,
        "relation_type": relation_type,
        "evidence_role": evidence_role,
        "claim_ceiling": FUSION_CLAIM_CEILING,
    }
    if relation_basis:
        record["relation_basis"] = relation_basis
    if lineage:
        record.update(lineage)
    return record


def _signal_relation_records(packet: dict[str, Any]) -> list[dict[str, Any]]:
    packet_id = str(packet["packet_id"])
    records: list[dict[str, Any]] = []

    for idx, signal in enumerate(_signal_items(packet, "supporting_signals")):
        records.append(
            _record(
                packet_id,
                _ref_from_item(signal, "supporting_signals", idx),
                "SUPPORTS",
                "supporting_signal",
                lineage=_lineage_fields(signal),
            )
        )

    for idx, signal in enumerate(_signal_items(packet, "contradicting_signals")):
        signal_ref = _ref_from_item(signal, "contradicting_signals", idx)
        lineage = _lineage_fields(signal)
        if _is_explicit_contradiction(signal):
            basis = str(signal.get("contradiction_basis") or signal.get("relation_basis") or "") if isinstance(signal, dict) else ""
            records.append(_record(packet_id, signal_ref, "CONTRADICTS", "explicit_contradiction_signal", basis, lineage))
        else:
            records.append(_record(packet_id, signal_ref, "QUALIFIES", "qualifying_or_tension_signal", lineage=lineage))

    for feature in _refs(packet, "input_features"):
        records.append(_record(packet_id, feature, "COMPLEMENTS", "input_feature_ref"))

    for window in _refs(packet, "input_windows"):
        records.append(_record(packet_id, window, "CONTEXTUALIZES", "input_window_ref"))

    if not records:
        records.append(_record(packet_id, packet_id, "ABSTAINS", "insufficient_signal_surface"))

    return records


def _nonnegative_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _clean(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_dependency_ledger(value: Any) -> tuple[list[dict[str, Any]], list[str]]:
    if value is None:
        return [], []
    if not isinstance(value, list):
        return [], ["upstream_dependency_ledger_invalid"]

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    for idx, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"upstream_dependency_record_invalid:{idx}")
            continue

        ref_id = _clean(item.get("ref_id"))
        group_name = _clean(item.get("group_name"))
        provenance_root = _clean(item.get("provenance_root"))
        dependency_group = _clean(item.get("dependency_group"))
        independence_group = _clean(item.get("independence_group"))
        vote = item.get("independent_support_vote") is True
        dependency_state = str(item.get("dependency_state") or "INDEPENDENCE_UNKNOWN")

        if not ref_id:
            errors.append(f"upstream_dependency_ref_id_missing:{idx}")
        if group_name not in EVIDENCE_GROUP_KEYS:
            errors.append(f"upstream_dependency_group_name_invalid:{idx}:{group_name or 'UNKNOWN'}")
        if dependency_state not in ALLOWED_DEPENDENCY_STATES:
            errors.append(f"upstream_dependency_state_invalid:{idx}:{dependency_state}")

        lineage_present = any([provenance_root, dependency_group, independence_group])
        complete_lineage = all([provenance_root, dependency_group, independence_group])
        if vote and not complete_lineage:
            errors.append(f"upstream_independent_support_metadata_incomplete:{idx}")
        if dependency_state == "INDEPENDENT_SUPPORT_ADMITTED" and not (vote and complete_lineage):
            errors.append(f"upstream_independent_support_state_unproven:{idx}")
        if dependency_state == "INDEPENDENCE_UNKNOWN" and lineage_present:
            errors.append(f"upstream_dependency_state_lineage_mismatch:{idx}")
        if dependency_state == "DEPENDENT_OR_PARTIAL_LINEAGE" and not lineage_present:
            errors.append(f"upstream_dependency_state_lineage_missing:{idx}")

        records.append(
            {
                "ref_id": ref_id,
                "group_name": group_name,
                "provenance_root": provenance_root,
                "dependency_group": dependency_group,
                "independence_group": independence_group,
                "independent_support_vote": vote,
                "dependency_state": dependency_state,
            }
        )

    return records, sorted(set(errors))


def _packet_evidence_bindings(packet: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for group_name in EVIDENCE_GROUP_KEYS:
        items = _signal_items(packet, group_name) if group_name in SIGNAL_RECORD_KEYS else _items(packet, group_name)
        for idx, item in enumerate(items):
            record = {
                "ref_id": _ref_from_item(item, group_name, idx),
                "group_name": group_name,
                "provenance_root": None,
                "dependency_group": None,
                "independence_group": None,
                "independent_support_vote": False,
            }
            if isinstance(item, dict):
                record["provenance_root"] = _clean(item.get("provenance_root"))
                record["dependency_group"] = _clean(item.get("dependency_group"))
                record["independence_group"] = _clean(item.get("independence_group"))
                record["independent_support_vote"] = item.get("independent_support_vote") is True
            records.append(record)
    return records


def _binding_signature(record: dict[str, Any]) -> tuple[Any, ...]:
    return (
        record.get("provenance_root"),
        record.get("dependency_group"),
        record.get("independence_group"),
        bool(record.get("independent_support_vote")),
    )


def _validate_dependency_binding(packet: dict[str, Any], ledger: list[dict[str, Any]]) -> list[str]:
    actual = _packet_evidence_bindings(packet)
    actual_pairs = Counter((str(row.get("group_name")), str(row.get("ref_id"))) for row in actual)
    ledger_pairs = Counter((str(row.get("group_name")), str(row.get("ref_id"))) for row in ledger)
    errors: list[str] = []
    if actual_pairs != ledger_pairs:
        errors.append("upstream_dependency_ledger_evidence_ref_binding_mismatch")
        return errors

    actual_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    ledger_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in actual:
        key = (str(row.get("group_name")), str(row.get("ref_id")))
        actual_by_key.setdefault(key, []).append(row)
    for row in ledger:
        key = (str(row.get("group_name")), str(row.get("ref_id")))
        ledger_by_key.setdefault(key, []).append(row)

    for key, actual_rows in actual_by_key.items():
        if not any(any(_binding_signature(row)[:3]) or row.get("independent_support_vote") is True for row in actual_rows):
            continue
        actual_signatures = sorted(repr(_binding_signature(row)) for row in actual_rows)
        ledger_signatures = sorted(repr(_binding_signature(row)) for row in ledger_by_key.get(key, []))
        if actual_signatures != ledger_signatures:
            errors.append(f"upstream_dependency_ledger_lineage_binding_mismatch:{key[0]}:{key[1]}")
    return sorted(set(errors))


def _admitted_support_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        record
        for record in records
        if record.get("group_name") in SUPPORT_BEARING_GROUP_KEYS
        and record.get("dependency_state") == "INDEPENDENT_SUPPORT_ADMITTED"
        and record.get("independent_support_vote") is True
        and record.get("provenance_root")
        and record.get("dependency_group")
        and record.get("independence_group")
    ]


def _independent_component_count(records: list[dict[str, Any]]) -> int:
    admitted = _admitted_support_records(records)
    if not admitted:
        return 0

    parent = list(range(len(admitted)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        left_root = find(left)
        right_root = find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    root_owner: dict[str, int] = {}
    dependency_owner: dict[str, int] = {}
    independence_owner: dict[str, int] = {}
    for idx, record in enumerate(admitted):
        provenance_root = str(record["provenance_root"])
        dependency_group = str(record["dependency_group"])
        independence_group = str(record["independence_group"])
        if provenance_root in root_owner:
            union(idx, root_owner[provenance_root])
        else:
            root_owner[provenance_root] = idx
        if dependency_group in dependency_owner:
            union(idx, dependency_owner[dependency_group])
        else:
            dependency_owner[dependency_group] = idx
        if independence_group in independence_owner:
            union(idx, independence_owner[independence_group])
        else:
            independence_owner[independence_group] = idx

    return len({find(idx) for idx in range(len(admitted))})


def _dependency_summary(records: list[dict[str, Any]], declared: bool = True) -> dict[str, Any]:
    support_records = [record for record in records if record.get("group_name") in SUPPORT_BEARING_GROUP_KEYS]
    admitted = _admitted_support_records(records)
    independent_support_count = _independent_component_count(records)
    independent_roots = sorted({str(record["provenance_root"]) for record in admitted})
    independent_dependency_groups = sorted({str(record["dependency_group"]) for record in admitted})
    provenance_roots = sorted({str(record["provenance_root"]) for record in support_records if record.get("provenance_root")})
    dependency_groups = sorted({str(record["dependency_group"]) for record in support_records if record.get("dependency_group")})
    independence_groups = sorted({str(record["independence_group"]) for record in admitted})
    correlated_or_unknown = [record for record in support_records if record not in admitted]

    if not declared:
        state = "INDEPENDENCE_NOT_DECLARED"
    elif not support_records:
        state = "NO_SUPPORT_BEARING_REFS"
    elif independent_support_count and not correlated_or_unknown:
        state = "INDEPENDENCE_ADMITTED"
    elif independent_support_count:
        state = "PARTIAL_INDEPENDENCE_ADMITTED"
    else:
        state = "INDEPENDENCE_NOT_ADMITTED"

    return {
        "independence_state": state,
        "independent_support_count": independent_support_count,
        "correlated_or_unknown_support_count": len(correlated_or_unknown),
        "provenance_root_count": len(provenance_roots),
        "dependency_group_count": len(dependency_groups),
        "independence_group_count": len(independence_groups),
        "independent_support_provenance_roots": independent_roots,
        "independent_support_dependency_groups": independent_dependency_groups,
        "independent_support_count_basis": "connected_components_shared_provenance_root_or_dependency_group_or_independence_group",
    }


def _compare_declared_count(packet: dict[str, Any], key: str, derived: int, hard_block_hits: list[str]) -> None:
    if key not in packet:
        return
    declared = _nonnegative_int(packet.get(key))
    if declared is None:
        hard_block_hits.append(f"upstream_{key}_invalid")
    elif declared != derived:
        hard_block_hits.append(f"upstream_{key}_mismatch")


def fuse_packet(packet: dict[str, Any], idx: int = 0) -> dict[str, Any]:
    normalized_packet = dict(packet)
    original_packet_id = _packet_id(normalized_packet)

    missing_fields = _required_packet_missing(normalized_packet)
    packet_id = original_packet_id or MISSING_PACKET_ID
    if original_packet_id:
        normalized_packet["packet_id"] = original_packet_id
    else:
        normalized_packet["packet_id"] = packet_id

    forbidden_hits = _forbidden_packet_hits(normalized_packet)
    upstream_hard_block_hits = [str(item) for item in _as_list(normalized_packet.get("hard_block_hits")) if item not in [None, ""]]
    hard_block_hits: list[str] = []

    if missing_fields:
        hard_block_hits.append("composite_packet_required_fields_missing")
    if _upstream_packet_failed(normalized_packet):
        hard_block_hits.append("upstream_packet_failed_closed")
    if normalized_packet.get("claim_ceiling") != CANDIDATE_ONLY_CLAIM_CEILING:
        hard_block_hits.append("upstream_packet_claim_ceiling_not_candidate_only")
    if forbidden_hits:
        hard_block_hits.append("upstream_packet_forbidden_output_attempted")
    if normalized_packet.get("claim_output_allowed") not in [False, None]:
        hard_block_hits.append("upstream_packet_claim_output_allowed")
    if normalized_packet.get("report_language_allowed") not in [False, None]:
        hard_block_hits.append("upstream_packet_report_language_allowed")

    hard_block_hits.extend(_validate_preserved_signal_bindings(normalized_packet))
    dependency_declared = "dependency_ledger" in normalized_packet
    dependency_ledger, dependency_errors = _normalize_dependency_ledger(normalized_packet.get("dependency_ledger"))
    hard_block_hits.extend(dependency_errors)
    if dependency_declared:
        hard_block_hits.extend(_validate_dependency_binding(normalized_packet, dependency_ledger))
    derived_independence = _dependency_summary(dependency_ledger, declared=dependency_declared)

    _compare_declared_count(
        normalized_packet,
        "independent_support_count",
        int(derived_independence["independent_support_count"]),
        hard_block_hits,
    )
    _compare_declared_count(
        normalized_packet,
        "correlated_or_unknown_support_count",
        int(derived_independence["correlated_or_unknown_support_count"]),
        hard_block_hits,
    )
    _compare_declared_count(
        normalized_packet,
        "dependency_group_count",
        int(derived_independence["dependency_group_count"]),
        hard_block_hits,
    )
    _compare_declared_count(
        normalized_packet,
        "provenance_root_count",
        int(derived_independence["provenance_root_count"]),
        hard_block_hits,
    )
    _compare_declared_count(
        normalized_packet,
        "independence_group_count",
        int(derived_independence["independence_group_count"]),
        hard_block_hits,
    )

    declared_state = normalized_packet.get("independence_state")
    if declared_state is not None and str(declared_state) != derived_independence["independence_state"]:
        hard_block_hits.append("upstream_independence_state_mismatch")

    if "independent_support_provenance_roots" in normalized_packet:
        declared_roots = sorted({str(item) for item in _as_list(normalized_packet.get("independent_support_provenance_roots")) if item not in [None, ""]})
        if declared_roots != derived_independence["independent_support_provenance_roots"]:
            hard_block_hits.append("upstream_independent_support_provenance_roots_mismatch")

    if "independent_support_dependency_groups" in normalized_packet:
        declared_groups = sorted({str(item) for item in _as_list(normalized_packet.get("independent_support_dependency_groups")) if item not in [None, ""]})
        if declared_groups != derived_independence["independent_support_dependency_groups"]:
            hard_block_hits.append("upstream_independent_support_dependency_groups_mismatch")

    if normalized_packet.get("independent_support_count") not in [None, 0, "0"] and not dependency_declared:
        hard_block_hits.append("upstream_dependency_ledger_missing")
    if normalized_packet.get("nominal_ref_count_is_independent_support_count") is True:
        hard_block_hits.append("upstream_nominal_ref_promoted_to_independent_support")
    if normalized_packet.get("evidence_strength_is_probability") is True:
        hard_block_hits.append("upstream_evidence_strength_probability_claim_rejected")

    hard_block_hits = sorted(set(hard_block_hits))
    relation_records = _signal_relation_records(normalized_packet) if not missing_fields else []
    relation_counts = Counter(row["relation_type"] for row in relation_records)
    has_support = relation_counts.get("SUPPORTS", 0) > 0
    has_contradiction = relation_counts.get("CONTRADICTS", 0) > 0
    has_qualifier = relation_counts.get("QUALIFIES", 0) > 0

    if hard_block_hits:
        fusion_status = "BLOCKED"
        decision = "BLOCK_FUSION"
    elif has_support and has_contradiction:
        fusion_status = "MIXED_WITH_EXPLICIT_CONTRADICTION"
        decision = "READY_FOR_ARGUMENT_WITH_CONTRADICTION"
    elif has_support and has_qualifier:
        fusion_status = "SUPPORTED_WITH_QUALIFIER"
        decision = "READY_FOR_ARGUMENT_WITH_QUALIFIER"
    elif has_support:
        fusion_status = "SUPPORTED"
        decision = "READY_FOR_ARGUMENT_SUPPORT"
    elif has_contradiction:
        fusion_status = "EXPLICITLY_CONTRADICTED"
        decision = "REVIEW_REQUIRED"
    elif has_qualifier:
        fusion_status = "QUALIFIED_ONLY"
        decision = "REVIEW_REQUIRED"
    else:
        fusion_status = "ABSTAINS"
        decision = "INSUFFICIENT_FOR_ARGUMENT"

    return {
        "module_id": MODULE_ID,
        "fusion_id": f"fusion_{packet_id}",
        "packet_id": packet_id,
        "packet_family": normalized_packet.get("packet_family", "unknown"),
        "relation_records": relation_records,
        "relation_counts": dict(sorted(relation_counts.items())),
        "support_signal_count": relation_counts.get("SUPPORTS", 0),
        "contradiction_signal_count": relation_counts.get("CONTRADICTS", 0),
        "qualifier_signal_count": relation_counts.get("QUALIFIES", 0),
        "context_signal_count": relation_counts.get("CONTEXTUALIZES", 0),
        "complement_signal_count": relation_counts.get("COMPLEMENTS", 0),
        "dependency_ledger": dependency_ledger,
        "independence_state": derived_independence["independence_state"],
        "independent_support_count": derived_independence["independent_support_count"],
        "correlated_or_unknown_support_count": derived_independence["correlated_or_unknown_support_count"],
        "dependency_group_count": derived_independence["dependency_group_count"],
        "provenance_root_count": derived_independence["provenance_root_count"],
        "independence_group_count": derived_independence["independence_group_count"],
        "independent_support_provenance_roots": derived_independence["independent_support_provenance_roots"],
        "independent_support_dependency_groups": derived_independence["independent_support_dependency_groups"],
        "independent_support_count_basis": derived_independence["independent_support_count_basis"],
        "nominal_ref_count_is_independent_support_count": False,
        "evidence_strength_is_probability": False,
        "fusion_status": fusion_status,
        "decision": decision,
        "claim_ceiling": FUSION_CLAIM_CEILING,
        "upstream_claim_ceiling": normalized_packet.get("claim_ceiling"),
        "upstream_status": normalized_packet.get("status"),
        "upstream_decision": normalized_packet.get("decision"),
        "upstream_hard_block_hits": upstream_hard_block_hits,
        "hard_block_hits": hard_block_hits,
        "missing_fields": missing_fields,
        "forbidden_output_hits": forbidden_hits,
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "tactical_truth": False,
        "dominance_truth": False,
        "control_truth": False,
        "coach_intention_truth": False,
        "off_ball_truth": False,
        "pitch_control_truth": False,
        "causal_truth": False,
        "blocked_language_families": list(BLOCKED_LANGUAGE_FAMILIES),
        "canonical_event_count": "UNKNOWN",
    }


def build_fusion_report(packets: list[dict[str, Any]]) -> dict[str, Any]:
    fusion_records = [fuse_packet(packet, idx) for idx, packet in enumerate(packets)]
    blocked_count = sum(1 for record in fusion_records if record["hard_block_hits"])
    status = "FAIL_CLOSED" if blocked_count else "SMOKE_PASS"
    admitted_report_ledger = [
        row
        for record in fusion_records
        if not record["hard_block_hits"]
        for row in record["dependency_ledger"]
    ]
    report_independence = _dependency_summary(admitted_report_ledger, declared=True)
    return {
        "module_id": MODULE_ID,
        "status": status,
        "fusion_record_count": len(fusion_records),
        "blocked_fusion_count": blocked_count,
        "fusion_records": fusion_records,
        "independent_support_count_total": report_independence["independent_support_count"],
        "independent_support_provenance_roots_total": report_independence["independent_support_provenance_roots"],
        "independent_support_dependency_groups_total": report_independence["independent_support_dependency_groups"],
        "independent_support_count_total_is_deduplicated": True,
        "independent_support_count_basis": report_independence["independent_support_count_basis"],
        "nominal_ref_count_is_independent_support_count": False,
        "claim_output_allowed": False,
        "report_language_allowed": False,
        "claim_ceiling": FUSION_CLAIM_CEILING,
        "canonical_event_count": "UNKNOWN",
        "claim_boundary": "fusion_relation_candidate_only_no_claim_text",
    }


def write_outputs(packets: list[dict[str, Any]], out_dir: str | Path) -> dict[str, Any]:
    out = _validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_fusion_report(packets)
    (out / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    lines = [
        "HPFA MULTI SIGNAL EVIDENCE FUSION LITE V1",
        "===========================================",
        f"status={report['status']}",
        f"fusion_record_count={report['fusion_record_count']}",
        f"blocked_fusion_count={report['blocked_fusion_count']}",
        f"independent_support_count_total={report['independent_support_count_total']}",
        f"canonical_event_count={report['canonical_event_count']}",
        "",
        "[fusion_records]",
    ]
    for record in report["fusion_records"][:50]:
        lines.append(
            f"- {record['fusion_id']} packet={record['packet_id']} status={record['fusion_status']} "
            f"decision={record['decision']} supports={record['support_signal_count']} "
            f"independent_support={record['independent_support_count']} "
            f"qualifies={record['qualifier_signal_count']} contradicts={record['contradiction_signal_count']}"
        )
    (out / OUTPUT_TXT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
