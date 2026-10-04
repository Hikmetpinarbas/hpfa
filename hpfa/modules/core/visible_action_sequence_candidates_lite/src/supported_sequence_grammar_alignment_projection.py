from __future__ import annotations

import hashlib
import json
from collections import Counter
from typing import Any

CLAIM_CEILING = "OBSERVED_SEQUENCE_GRAMMAR_ALIGNMENT_CANDIDATE_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _layer_tokens(variant: dict[str, Any]) -> tuple[list[str], list[str]]:
    layer_refs = [_clean(v) for v in (variant.get("time_layer_refs") or []) if _clean(v)]
    nodes = [row for row in (variant.get("node_records") or []) if isinstance(row, dict)]
    families_by_layer: dict[str, list[str]] = {layer_ref: [] for layer_ref in layer_refs}

    for node in nodes:
        layer_ref = _clean(node.get("time_layer_ref"))
        if not layer_ref:
            continue
        families = sorted(
            _clean(value).upper()
            for value in (node.get("action_family_candidates") or [])
            if _clean(value)
        )
        families_by_layer.setdefault(layer_ref, []).extend(families)

    tokens: list[str] = []
    for layer_ref in layer_refs:
        families = sorted(families_by_layer.get(layer_ref) or [])
        token = "LAYER[" + "|".join(families) + "]"
        tokens.append(token)
    return layer_refs, tokens


def _all_inter_layer_order_confirmed(variant: dict[str, Any]) -> bool:
    edges = [row for row in (variant.get("edge_relations") or []) if isinstance(row, dict)]
    if not edges:
        return False
    return all(_clean(edge.get("relation")) == "BEFORE_CONFIRMED" for edge in edges)


def _lcs(left: list[str], right: list[str]) -> list[str]:
    m, n = len(left), len(right)
    dp: list[list[int]] = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            if left[i] == right[j]:
                dp[i][j] = 1 + dp[i + 1][j + 1]
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])

    out: list[str] = []
    i = j = 0
    while i < m and j < n:
        if left[i] == right[j]:
            out.append(left[i])
            i += 1
            j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return out


def _token_counter(token: str) -> Counter[str]:
    if not token.startswith("LAYER[") or not token.endswith("]"):
        return Counter()
    inner = token[6:-1]
    if not inner:
        return Counter()
    return Counter(part for part in inner.split("|") if part)


def _substitution_cost(left_token: str, right_token: str) -> float:
    if left_token == right_token:
        return 0.0
    left = _token_counter(left_token)
    right = _token_counter(right_token)
    keys = set(left) | set(right)
    if not keys:
        return 1.0
    denom = sum(max(left.get(key, 0), right.get(key, 0)) for key in keys)
    if denom <= 0:
        return 1.0
    overlap = sum(min(left.get(key, 0), right.get(key, 0)) for key in keys) / denom
    return round(1.0 - overlap, 6)


def _edit_alignment(left: list[str], right: list[str]) -> tuple[float, list[dict[str, Any]]]:
    m, n = len(left), len(right)
    dp: list[list[float]] = [[0.0] * (n + 1) for _ in range(m + 1)]
    back: list[list[str | None]] = [[None] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        dp[i][0] = float(i)
        back[i][0] = "DELETE"
    for j in range(1, n + 1):
        dp[0][j] = float(j)
        back[0][j] = "INSERT"

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            sub_cost = _substitution_cost(left[i - 1], right[j - 1])
            candidates = [
                (dp[i - 1][j - 1] + sub_cost, "MATCH" if sub_cost == 0.0 else "SUBSTITUTE"),
                (dp[i - 1][j] + 1.0, "DELETE"),
                (dp[i][j - 1] + 1.0, "INSERT"),
            ]
            cost, op = min(candidates, key=lambda item: (
                round(item[0], 9),
                {"MATCH": 0, "SUBSTITUTE": 1, "DELETE": 2, "INSERT": 3}[item[1]],
            ))
            dp[i][j] = cost
            back[i][j] = op

    operations: list[dict[str, Any]] = []
    i, j = m, n
    while i > 0 or j > 0:
        op = back[i][j]
        if op in {"MATCH", "SUBSTITUTE"}:
            left_token = left[i - 1]
            right_token = right[j - 1]
            operations.append({
                "operation": op,
                "left_index": i - 1,
                "right_index": j - 1,
                "left_token": left_token,
                "right_token": right_token,
                "cost": 0.0 if op == "MATCH" else _substitution_cost(left_token, right_token),
            })
            i -= 1
            j -= 1
        elif op == "DELETE":
            operations.append({
                "operation": "DELETE",
                "left_index": i - 1,
                "right_index": None,
                "left_token": left[i - 1],
                "right_token": None,
                "cost": 1.0,
            })
            i -= 1
        elif op == "INSERT":
            operations.append({
                "operation": "INSERT",
                "left_index": None,
                "right_index": j - 1,
                "left_token": None,
                "right_token": right[j - 1],
                "cost": 1.0,
            })
            j -= 1
        else:
            raise RuntimeError("edit_alignment_backtrace_missing")
    operations.reverse()
    return round(dp[m][n], 6), operations


def build_supported_sequence_grammar_alignment(sequence_payload: dict[str, Any]) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []

    if sequence_payload.get("outcome_used_in_similarity_decision") is not False:
        blocks.append("outcome_similarity_leakage_policy_breached")
    if sequence_payload.get("same_timestamp_internal_ordering_allowed") is not False:
        blocks.append("same_timestamp_internal_ordering_policy_breached")
    if sequence_payload.get("source_row_order_is_temporal_truth") is not False:
        blocks.append("source_row_order_temporal_policy_breached")
    if sequence_payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append("canonical_event_count_claimed")
    if sequence_payload.get("true_action_count") != "UNKNOWN":
        blocks.append("true_action_count_claimed")
    if sequence_payload.get("production_release") is True:
        blocks.append("production_release_claimed")

    variants = {
        _clean(row.get("partial_order_occurrence_variant_id")): row
        for row in (sequence_payload.get("partial_order_occurrence_variants") or [])
        if isinstance(row, dict) and _clean(row.get("partial_order_occurrence_variant_id"))
    }
    pairs = [
        row for row in (sequence_payload.get("dependency_aware_partial_order_similarity_pairs") or [])
        if isinstance(row, dict)
    ]
    if len(variants) < 2 or not pairs:
        reviews.append("insufficient_comparison_surface_for_grammar_alignment")

    alignments: list[dict[str, Any]] = []
    for pair in pairs:
        pair_id = _clean(pair.get("partial_order_similarity_pair_id"))
        if pair.get("comparison_eligible") is not True:
            continue
        if pair.get("outcome_used_in_similarity_decision") is not False:
            blocks.append(f"pair_outcome_similarity_leakage:{pair_id or 'UNKNOWN'}")
            continue

        left_id = _clean(pair.get("left_variant_ref"))
        right_id = _clean(pair.get("right_variant_ref"))
        left_variant = variants.get(left_id)
        right_variant = variants.get(right_id)
        if not left_variant or not right_variant:
            reviews.append(f"grammar_alignment_variant_missing:{pair_id or 'UNKNOWN'}")
            continue
        if not _all_inter_layer_order_confirmed(left_variant) or not _all_inter_layer_order_confirmed(right_variant):
            reviews.append(f"grammar_alignment_order_indeterminate:{pair_id or 'UNKNOWN'}")
            continue

        _, left_tokens = _layer_tokens(left_variant)
        _, right_tokens = _layer_tokens(right_variant)
        if not left_tokens or not right_tokens:
            reviews.append(f"grammar_alignment_empty_token_path:{pair_id or 'UNKNOWN'}")
            continue

        common_core = _lcs(left_tokens, right_tokens)
        edit_distance, operations = _edit_alignment(left_tokens, right_tokens)
        first_divergence = next((op for op in operations if op["operation"] != "MATCH"), None)
        max_len = max(len(left_tokens), len(right_tokens))
        min_len = min(len(left_tokens), len(right_tokens))
        symmetric_denom = len(left_tokens) + len(right_tokens)

        alignments.append({
            "supported_sequence_grammar_alignment_id": "sga_" + _digest(
                pair_id, left_id, right_id, left_tokens, right_tokens
            )[:24],
            "source_similarity_pair_ref": pair_id or None,
            "left_variant_ref": left_id,
            "right_variant_ref": right_id,
            "comparison_eligibility_state": pair.get("comparison_eligibility_state"),
            "left_layer_tokens": left_tokens,
            "right_layer_tokens": right_tokens,
            "supported_common_core_tokens": common_core,
            "supported_common_core_layer_count": len(common_core),
            "common_core_min_route_coverage": round(len(common_core) / min_len, 6) if min_len else None,
            "common_core_symmetric_coverage": round(
                (2 * len(common_core)) / symmetric_denom, 6
            ) if symmetric_denom else None,
            "grammar_edit_distance": edit_distance,
            "grammar_edit_distance_normalized": round(edit_distance / max_len, 6) if max_len else None,
            "edit_operations": operations,
            "first_supported_grammar_divergence": first_divergence,
            "outcome_excluded_from_alignment": True,
            "same_time_layer_token_members_are_unordered": True,
            "same_timestamp_internal_ordering_allowed": False,
            "source_row_order_is_temporal_truth": False,
            "lcs_is_causal_backbone": False,
            "grammar_alignment_is_process_identity_truth": False,
            "grammar_alignment_is_route_family_truth": False,
            "grammar_alignment_is_tactical_equivalence_truth": False,
            "grammar_alignment_is_causal_truth": False,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    if blocks:
        status = "FAIL_CLOSED"
    elif reviews or str(
        sequence_payload.get("dependency_aware_partial_order_similarity_status") or ""
    ).upper() == "REVIEW_REQUIRED":
        status = "REVIEW_REQUIRED"
    else:
        status = "PASS"

    return {
        "status": status,
        "supported_sequence_grammar_alignments": alignments if not blocks else [],
        "supported_sequence_grammar_alignment_count": len(alignments) if not blocks else 0,
        "source_partial_order_variant_count": len(variants),
        "source_similarity_pair_count": len(pairs),
        "comparison_eligible_pair_count": sum(
            1 for row in pairs if row.get("comparison_eligible") is True
        ),
        "outcome_excluded_from_alignment": True,
        "same_time_layer_token_members_are_unordered": True,
        "same_timestamp_internal_ordering_allowed": False,
        "source_row_order_is_temporal_truth": False,
        "lcs_is_causal_backbone": False,
        "grammar_alignment_is_process_identity_truth": False,
        "grammar_alignment_is_tactical_equivalence_truth": False,
        "hard_block_hits": sorted(set(blocks)),
        "review_hits": sorted(set(reviews)),
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
