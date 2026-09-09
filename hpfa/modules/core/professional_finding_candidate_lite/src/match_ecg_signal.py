from __future__ import annotations

from typing import Any

MODULE_ID = "match_ecg_signal_lite_v1"
CANONICAL_EVENT_COUNT = TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "DESCRIPTIVE_MATCH_ECG_SIGNAL_ONLY"
ALLOWED_TEMPORAL_RELATIONS = {
    "BEFORE_CONFIRMED",
    "AFTER_CONFIRMED",
    "SAME_TIME_UNORDERED",
    "ORDER_INDETERMINATE",
    "PROVENANCE_ORDER_ONLY",
}
DIRECTIONAL_RELATIONS = {"BEFORE_CONFIRMED", "AFTER_CONFIRMED"}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def build_match_ecg_signal(change_payload: dict[str, Any]) -> dict[str, Any]:
    """Project admitted change evidence into analyst-facing rise/fall/break signals.

    This module does not discover events, traces, phases, chronology or momentum.
    It only projects already admitted comparison evidence.
    """
    blocks: list[str] = []
    reviews: list[str] = []

    if change_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("upstream_canonical_event_count_claimed")
    if change_payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        blocks.append("upstream_true_action_count_claimed")
    if change_payload.get("production_release") is True:
        blocks.append("upstream_production_release_claimed")
    if change_payload.get("hard_block_hits") or _clean(change_payload.get("status")).upper() == "FAIL_CLOSED":
        blocks.append("upstream_fail_closed")
    elif _clean(change_payload.get("status")).upper() == "REVIEW_REQUIRED":
        reviews.append("upstream_review_required")

    comparisons = [x for x in (change_payload.get("change_comparisons") or []) if isinstance(x, dict)]
    if not comparisons:
        reviews.append("no_admitted_change_comparisons")

    signals: list[dict[str, Any]] = []
    for idx, row in enumerate(comparisons):
        ref = _clean(row.get("comparison_id")) or f"row_{idx}"
        relation = _clean(row.get("temporal_relation")).upper()
        if relation not in ALLOWED_TEMPORAL_RELATIONS:
            blocks.append(f"temporal_relation_not_admitted:{ref}")
            continue

        direction = _clean(row.get("direction")).upper()
        if direction and direction not in {"RISE", "FALL", "BREAK", "NO_VISIBLE_CHANGE", "UNCERTAIN"}:
            blocks.append(f"direction_invalid:{ref}")
            continue
        if direction in {"RISE", "FALL"} and relation not in DIRECTIONAL_RELATIONS:
            blocks.append(f"directional_change_without_before_after_admission:{ref}")
            continue

        coverage = _clean(row.get("coverage_state")).upper()
        if coverage not in {"ADEQUATE_FOR_COMPARISON", "PARTIAL", "UNKNOWN"}:
            blocks.append(f"coverage_state_invalid:{ref}")
            continue
        if coverage != "ADEQUATE_FOR_COMPARISON" and direction not in {"UNCERTAIN", ""}:
            reviews.append(f"direction_downgraded_for_coverage:{ref}")
            direction = "UNCERTAIN"

        outcome_changed = row.get("outcome_mix_changed") is True
        sequence_changed = row.get("sequence_mix_changed") is True
        counter = list(row.get("counterevidence") or [])
        alternatives = list(row.get("alternative_explanations") or [])

        if not direction:
            if outcome_changed or sequence_changed:
                direction = "BREAK"
            else:
                direction = "NO_VISIBLE_CHANGE"

        if direction == "NO_VISIBLE_CHANGE":
            safe_meaning = "Mevcut çözünürlükte karşılaştırılan görünür süreç dağılımlarında fark gözlenmedi."
        elif direction == "RISE":
            safe_meaning = "Admitted önce/sonra karşılaştırmasında tanımlı görünür süreç göstergesi sonraki pencerede yükseldi."
        elif direction == "FALL":
            safe_meaning = "Admitted önce/sonra karşılaştırmasında tanımlı görünür süreç göstergesi sonraki pencerede azaldı."
        elif direction == "BREAK":
            safe_meaning = "Karşılaştırılan admitted pencereler arasında görünür süreç dağılımında kırılma adayı var."
        else:
            safe_meaning = "Hareket adayı görünür; fakat coverage veya temporal admission yönlü değişim cümlesi için yeterli değil."

        signals.append({
            "comparison_id": ref,
            "entity_scope": row.get("entity_scope"),
            "process_ref": row.get("process_ref"),
            "baseline_window_ref": row.get("baseline_window_ref"),
            "comparison_window_ref": row.get("comparison_window_ref"),
            "temporal_relation": relation,
            "coverage_state": coverage,
            "signal_state": direction,
            "outcome_mix_changed": outcome_changed,
            "sequence_mix_changed": sequence_changed,
            "counterevidence": counter,
            "alternative_explanations": alternatives,
            "safe_meaning_tr": safe_meaning,
            "forbidden_inference": [
                "MOMENTUM_TRUTH",
                "DOMINANCE_TRUTH",
                "TACTICAL_ADAPTATION_TRUTH",
                "COACH_INTENTION_TRUTH",
                "CAUSALITY_TRUTH",
                "PHYSICAL_INTENSITY_TRUTH",
            ],
            "directional_language_admitted": relation in DIRECTIONAL_RELATIONS and coverage == "ADEQUATE_FOR_COMPARISON",
            "claim_ceiling": CLAIM_CEILING,
        })

    if blocks:
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "signals": [],
            "signal_count": 0,
            "hard_block_hits": sorted(set(blocks)),
            "review_hits": sorted(set(reviews)),
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED" if reviews else "PASS",
        "signals": signals,
        "signal_count": len(signals),
        "hard_block_hits": [],
        "review_hits": sorted(set(reviews)),
        "momentum_truth_claimed": False,
        "dominance_truth_claimed": False,
        "causality_claimed": False,
        "coach_intention_claimed": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
