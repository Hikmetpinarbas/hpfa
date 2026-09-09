from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from hpfa.modules.core.metric_definition_policy_lite.src.construct_context_guard import (
    assess_construct_comparison,
)
from hpfa.modules.core.provider_label_value_semantics_lite.src import (
    provider_label_value_semantics as provider_semantics,
)

MODULE_ID = "progression_effectiveness_construct_v1"
TRACE_MODULE_ID = "trackable_action_trace_candidates_lite_v1"
CONSEQUENCE_MODULE_ID = "trackable_action_consequence_candidates_lite_v1"
OBSERVATION_MODEL = "ENRICHED_FOOTBALL_OBSERVATION_DATA_V1"
CLAIM_CEILING = "PROGRESSION_EFFECTIVENESS_PROFILE_CANDIDATE_ONLY"
PROGRESSION_FAMILIES = {"PASS", "CARRY"}
POSITIVE_CONSEQUENCES = {
    "SAME_TEAM_CONTINUATION_CANDIDATE",
    "SHOT_FOLLOW_UP_CANDIDATE",
    "TERMINAL_OUTCOME_SUPPORT_CANDIDATE",
    "RESTART_OR_RESET_CANDIDATE",
}
ADVERSE_CONSEQUENCES = {"OPPONENT_HANDOVER_CANDIDATE"}
REVIEW_OR_UNKNOWN_CONSEQUENCES = {
    "NO_VISIBLE_FOLLOW_UP_CANDIDATE",
    "VISIBLE_FOLLOW_UP_UNCERTAIN_CANDIDATE",
    "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE",
    "PROVENANCE_WINDOW_ONLY_REVIEW_REQUIRED_CANDIDATE",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 6)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _registry(repo_root: str | Path | None = None):
    root = Path(repo_root).resolve() if repo_root is not None else _repo_root()
    path = root / "hpfa/modules/core/provider_label_value_semantics_lite/registry/sportsbase_label_semantics_seed_v1.json"
    return provider_semantics.load_registry(path)


def _is_progression_trace(trace: dict[str, Any], registry: dict[str, Any]) -> bool:
    families = {_clean(item) for item in (trace.get("action_family_candidates") or []) if _clean(item)}
    if not families:
        single = _clean(trace.get("action_family_candidate"))
        families = {single} if single else set()
    if not (families & PROGRESSION_FAMILIES):
        return False
    explicit = _clean(trace.get("progression_candidate"))
    if explicit == "PROGRESSIVE_CANDIDATE":
        return True
    for label in trace.get("raw_labels") or []:
        classified = provider_semantics.classify_label(
            _clean(label), source_format="trace", source_role=_clean(trace.get("source_role")), registry=registry
        )
        if (
            _clean(classified.get("progression_candidate")) == "PROGRESSIVE_CANDIDATE"
            and _clean(classified.get("action_family_candidate")) in PROGRESSION_FAMILIES
            and _clean(classified.get("review_status")) == "REVIEWED_CANDIDATE"
        ):
            return True
    return False


def _validate_input(payload: dict[str, Any], module_id: str, prefix: str, blocks: list[str]) -> None:
    if payload.get("module_id") != module_id:
        blocks.append(f"{prefix}_module_id_mismatch")
    if payload.get("canonical_event_count") != "UNKNOWN":
        blocks.append(f"{prefix}_canonical_event_count_claimed")
    if payload.get("true_action_count") not in {None, "UNKNOWN"}:
        blocks.append(f"{prefix}_true_action_count_claimed")
    if payload.get("production_release") is True:
        blocks.append(f"{prefix}_production_release_claimed")
    if payload.get("hard_block_hits"):
        blocks.append(f"{prefix}_hard_blocks_present")


def build_progression_effectiveness_construct(
    trace_payload: dict[str, Any],
    consequence_payload: dict[str, Any],
    guard: dict[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    _validate_input(trace_payload, TRACE_MODULE_ID, "trace", blocks)
    _validate_input(consequence_payload, CONSEQUENCE_MODULE_ID, "consequence", blocks)

    trace_binding = _clean(trace_payload.get("match_surface_binding_id"))
    consequence_binding = _clean(consequence_payload.get("match_surface_binding_id"))
    if not trace_binding or trace_binding != consequence_binding:
        blocks.append("match_surface_binding_mismatch")

    traces = trace_payload.get("trackable_action_trace_candidates") or []
    consequences = consequence_payload.get("trackable_action_consequence_candidates") or []
    if not isinstance(traces, list):
        blocks.append("trace_inventory_invalid")
        traces = []
    if not isinstance(consequences, list):
        blocks.append("consequence_inventory_invalid")
        consequences = []
    if trace_payload.get("trackable_action_trace_candidate_count") != len(traces):
        blocks.append("trace_count_mismatch")
    if consequence_payload.get("trackable_action_consequence_candidate_count") != len(consequences):
        blocks.append("consequence_count_mismatch")

    try:
        registry = _registry(repo_root)
    except (OSError, ValueError) as exc:
        blocks.append(f"provider_semantic_authority_unavailable:{type(exc).__name__}")
        registry = {}

    trace_by_id: dict[str, dict[str, Any]] = {}
    progression_ids: list[str] = []
    for position, trace in enumerate(traces):
        if not isinstance(trace, dict):
            blocks.append(f"trace_record_invalid:{position}")
            continue
        trace_id = _clean(trace.get("trackable_action_trace_candidate_id"))
        if not trace_id or trace_id in trace_by_id:
            blocks.append(f"trace_id_invalid_or_duplicate:{position}")
            continue
        trace_by_id[trace_id] = trace
        if registry and _is_progression_trace(trace, registry):
            progression_ids.append(trace_id)

    consequence_by_anchor: dict[str, dict[str, Any]] = {}
    for position, row in enumerate(consequences):
        if not isinstance(row, dict):
            blocks.append(f"consequence_record_invalid:{position}")
            continue
        anchor = _clean(row.get("anchor_trackable_action_trace_candidate_id"))
        if not anchor or anchor in consequence_by_anchor:
            blocks.append(f"consequence_anchor_invalid_or_duplicate:{position}")
            continue
        if anchor not in trace_by_id:
            blocks.append(f"consequence_anchor_trace_missing:{anchor}")
            continue
        consequence_by_anchor[anchor] = row

    context = {
        "denominator_set_id": f"progression_trace_candidates:{trace_binding}",
        "observation_window": "MATCH_LOCAL_VISIBLE_TRACE_SCOPE",
        "entity_scope": "PLAYER_OR_GOALKEEPER_ACTOR_BEARING_TRACE",
        "team_scope": "MATCH_LOCAL_TEAM_IDENTITY_CANDIDATES",
        "period_scope": "TRACE_DECLARED_PERIOD_SCOPE",
        "context_policy_id": "ZFGV_PROGRESSION_EFFECTIVENESS_V1",
        "source_surface_roles": sorted({
            _clean(trace.get("source_role")) for trace in traces if isinstance(trace, dict) and _clean(trace.get("source_role"))
        }) or ["NO_VISIBLE_SOURCE_ROLE"],
        "required_event_families": sorted(PROGRESSION_FAMILIES),
        "construct_target": "PROGRESSION_EFFECTIVENESS",
        "dependency_group": f"progression_effectiveness:{trace_binding}",
        "provenance_root": trace_binding,
    }
    guard_result = assess_construct_comparison(context, context, guard)
    if not guard_result.get("comparison_admitted"):
        blocks.append("construct_context_guard_not_admitted")

    denominator = len(progression_ids)
    outcome_counts: Counter[str] = Counter()
    support_refs: list[str] = []
    counterevidence_refs: list[str] = []
    unresolved_refs: list[str] = []
    evaluable = 0
    for trace_id in progression_ids:
        row = consequence_by_anchor.get(trace_id)
        if row is None:
            unresolved_refs.append(trace_id)
            continue
        primary = _clean(row.get("primary_consequence_candidate"))
        record_status = _clean(row.get("record_status"))
        consequence_id = _clean(row.get("trackable_action_consequence_candidate_id")) or trace_id
        outcome_counts[primary or "UNKNOWN"] += 1
        if record_status == "REVIEW_REQUIRED" or primary in REVIEW_OR_UNKNOWN_CONSEQUENCES or not primary:
            unresolved_refs.append(consequence_id)
            continue
        evaluable += 1
        if primary in POSITIVE_CONSEQUENCES:
            support_refs.append(consequence_id)
        elif primary in ADVERSE_CONSEQUENCES:
            counterevidence_refs.append(consequence_id)
        else:
            unresolved_refs.append(consequence_id)
            evaluable -= 1

    positive = len(support_refs)
    adverse = len(counterevidence_refs)
    missing_or_uncertain = denominator - evaluable
    if denominator == 0:
        reviews.append("no_progression_eligible_trace_candidate_visible")
    if missing_or_uncertain > 0:
        reviews.append("progression_consequence_coverage_incomplete")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS_CANDIDATE")
    construct = None
    if not blocks:
        construct = {
            "construct_candidate_id": f"pec_{trace_binding[-16:] or 'unbound'}",
            **context,
            "eligible_progression_trace_candidate_count": denominator,
            "evaluable_progression_consequence_candidate_count": evaluable,
            "progression_consequence_coverage_rate_candidate": _ratio(evaluable, denominator),
            "visible_positive_follow_up_candidate_count": positive,
            "visible_adverse_handover_candidate_count": adverse,
            "positive_follow_up_rate_among_evaluable_candidate": _ratio(positive, evaluable),
            "adverse_handover_rate_among_evaluable_candidate": _ratio(adverse, evaluable),
            "unresolved_or_missing_consequence_candidate_count": missing_or_uncertain,
            "consequence_classification_counts": dict(sorted(outcome_counts.items())),
            "support_consequence_candidate_refs": sorted(support_refs),
            "counterevidence_consequence_candidate_refs": sorted(counterevidence_refs),
            "unresolved_consequence_candidate_refs": sorted(unresolved_refs),
            "alternative_explanations": [
                "visible consequence may reflect teammate/opponent response rather than anchor quality alone",
                "provider progression annotation coverage may be selective",
                "match-local role and game-state mix may change the opportunity set",
            ],
            "uncertainty": "MATCH_LOCAL_VISIBLE_CONSEQUENCE_COVERAGE_ONLY_NO_CALIBRATED_EFFECTIVENESS_TRUTH",
            "withdrawal_condition": "withdraw comparison or finding if denominator/context alignment, progression semantic authority, temporal admission, consequence coverage, or dependency controls fail",
            "analyst_action": "inspect support and counterevidence trace/consequence refs before describing progression effectiveness",
            "same_provider_reflection_adds_independent_vote": False,
            "independent_support_vote_count": 0,
            "missing_consequence_is_counterevidence": False,
            "effectiveness_score_emitted": False,
            "construct_validity_truth": False,
            "professional_finding_emitted": False,
            "claim_output_allowed": False,
        }

    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "observation_model": OBSERVATION_MODEL,
        "construct_candidate": construct,
        "construct_candidate_count": 1 if construct is not None else 0,
        "construct_context_guard": guard_result,
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "progression_effectiveness_truth": False,
        "metric_validity_truth": False,
        "possession_truth": False,
        "sequence_truth": False,
        "causal_truth": False,
        "tactical_truth": False,
        "professional_finding_emitted": False,
        "claim_output_allowed": False,
        "event_only_is_product_ceiling": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
