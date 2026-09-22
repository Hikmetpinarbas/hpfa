from __future__ import annotations

from collections import Counter, defaultdict
from math import log2
from statistics import median
from typing import Any


def _state_token(layer: dict[str, Any]) -> str:
    families = sorted({str(v) for v in (layer.get("action_family_candidates") or []) if v})
    return "+".join(families) if families else "UNRESOLVED_LAYER"


def _entropy_from_counts(counts: Counter[str]) -> float | None:
    total = sum(int(v) for v in counts.values())
    if total <= 0:
        return None
    value = 0.0
    for count in counts.values():
        if count <= 0:
            continue
        p = count / total
        value -= p * log2(p)
    return value


def _normalized_entropy(counts: Counter[str]) -> float | None:
    raw = _entropy_from_counts(counts)
    k = sum(1 for v in counts.values() if v > 0)
    if raw is None:
        return None
    if k <= 1:
        return 0.0
    return raw / log2(k)


def _js_divergence(left: Counter[str], right: Counter[str]) -> float | None:
    keys = sorted(set(left) | set(right))
    l_total = sum(left.values())
    r_total = sum(right.values())
    if l_total <= 0 or r_total <= 0:
        return None
    p = {k: left[k] / l_total for k in keys}
    q = {k: right[k] / r_total for k in keys}
    m = {k: 0.5 * (p[k] + q[k]) for k in keys}

    def kl(a: dict[str, float], b: dict[str, float]) -> float:
        return sum(v * log2(v / b[k]) for k, v in a.items() if v > 0 and b[k] > 0)

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def build_process_sequence_information(signatures: list[dict[str, Any]], _include_groups: bool = True) -> dict[str, Any]:
    eligible = [row for row in signatures if isinstance(row, dict)]
    trace_counts: Counter[str] = Counter()
    transition_counts: Counter[str] = Counter()
    outgoing: dict[str, Counter[str]] = defaultdict(Counter)
    durations: list[float] = []
    by_period_trace: dict[str, Counter[str]] = defaultdict(Counter)
    transition_duration_values: dict[str, list[float]] = defaultdict(list)

    for row in eligible:
        tokens = [_state_token(layer) for layer in (row.get("layers") or []) if isinstance(layer, dict)]
        if tokens:
            trace_key = " -> ".join(tokens)
            trace_counts[trace_key] += 1
            period = str(row.get("period_candidate") or "UNKNOWN")
            by_period_trace[period][trace_key] += 1

        for left, right in zip(row.get("layers") or [], (row.get("layers") or [])[1:]):
            if not isinstance(left, dict) or not isinstance(right, dict):
                continue
            a, b = _state_token(left), _state_token(right)
            key = f"{a} -> {b}"
            transition_counts[key] += 1
            outgoing[a][b] += 1
            lt = left.get("timestamp_candidate")
            rt = right.get("timestamp_candidate")
            if isinstance(lt, (int, float)) and isinstance(rt, (int, float)) and rt > lt:
                transition_duration_values[key].append(float(rt - lt))

        duration = row.get("process_interval_duration_candidate")
        if isinstance(duration, (int, float)) and duration >= 0:
            durations.append(float(duration))

    transition_rows = []
    for source in sorted(outgoing):
        total = sum(outgoing[source].values())
        for target, count in sorted(outgoing[source].items()):
            key = f"{source} -> {target}"
            dt = transition_duration_values.get(key) or []
            transition_rows.append({
                "from_state": source,
                "to_state": target,
                "transition_n": count,
                "eligible_outgoing_transition_n": total,
                "conditional_transition_share_candidate": count / total if total else None,
                "median_inter_layer_seconds_candidate": median(dt) if dt else None,
                "duration_observation_n": len(dt),
            })

    downstream_entropy = []
    for source in sorted(outgoing):
        counts = outgoing[source]
        downstream_entropy.append({
            "from_state": source,
            "eligible_outgoing_transition_n": sum(counts.values()),
            "distinct_downstream_state_n": sum(1 for v in counts.values() if v > 0),
            "shannon_entropy_bits_candidate": _entropy_from_counts(counts),
            "normalized_transition_entropy_candidate": _normalized_entropy(counts),
        })

    period_keys = sorted(by_period_trace)
    evolution = []
    for i, left_period in enumerate(period_keys):
        for right_period in period_keys[i + 1:]:
            value = _js_divergence(by_period_trace[left_period], by_period_trace[right_period])
            evolution.append({
                "left_period": left_period,
                "right_period": right_period,
                "jensen_shannon_divergence_bits_candidate": value,
                "left_trace_n": sum(by_period_trace[left_period].values()),
                "right_trace_n": sum(by_period_trace[right_period].values()),
            })

    group_profiles = []
    if _include_groups:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for row in eligible:
            team = str(row.get("team_identity_candidate_id") or "UNKNOWN_TEAM")
            family = str(row.get("process_family_candidate") or "UNKNOWN_PROCESS_FAMILY")
            grouped[(team, family)].append(row)
        for (team, family), rows in sorted(grouped.items()):
            profile = build_process_sequence_information(rows, _include_groups=False)
            group_profiles.append({
                "team_identity_candidate_id": team,
                "process_family_candidate": family,
                "eligible_process_signature_n": profile.get("eligible_process_signature_n"),
                "distinct_trace_variant_n": profile.get("distinct_trace_variant_n"),
                "trace_variant_counts": profile.get("trace_variant_counts"),
                "transition_count": profile.get("transition_count"),
                "distinct_transition_n": profile.get("distinct_transition_n"),
                "transition_profile": profile.get("transition_profile"),
                "downstream_transition_entropy": profile.get("downstream_transition_entropy"),
                "process_duration_profile": profile.get("process_duration_profile"),
                "period_trace_distribution_comparisons": profile.get("period_trace_distribution_comparisons"),
                "claim_ceiling": profile.get("claim_ceiling"),
            })

    return {
        "status": "REVIEW_REQUIRED" if eligible else "NOT_APPLICABLE",
        "eligible_process_signature_n": len(eligible),
        "distinct_trace_variant_n": len(trace_counts),
        "trace_variant_counts": [
            {"trace_variant": key, "process_n": count}
            for key, count in sorted(trace_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "transition_count": sum(transition_counts.values()),
        "distinct_transition_n": len(transition_counts),
        "transition_profile": transition_rows,
        "downstream_transition_entropy": downstream_entropy,
        "process_duration_profile": {
            "observed_duration_n": len(durations),
            "median_process_interval_seconds_candidate": median(durations) if durations else None,
            "min_process_interval_seconds_candidate": min(durations) if durations else None,
            "max_process_interval_seconds_candidate": max(durations) if durations else None,
        },
        "period_trace_distribution_comparisons": evolution,
        "team_process_family_profiles": group_profiles,
        "state_token_basis": "SORTED_ACTION_FAMILY_SET_WITHIN_ADMITTED_TEMPORAL_LAYER",
        "transition_basis": "STRICTLY_ORDERED_TEMPORAL_LAYERS_ONLY",
        "same_timestamp_internal_ordering_allowed": False,
        "trace_variant_is_tactical_pattern_truth": False,
        "transition_probability_is_causal_truth": False,
        "entropy_is_quality_or_creativity_truth": False,
        "period_divergence_is_tactical_change_truth": False,
        "duration_is_physical_action_duration_truth": False,
        "independent_support_created": False,
        "claim_ceiling": "MATCH_LOCAL_VISIBLE_PROCESS_SEQUENCE_INFORMATION_CANDIDATE_ONLY",
    }
