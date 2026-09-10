from __future__ import annotations

from typing import Any

MODULE_ID = "process_variant_difference_report_projection_lite_v1"
SOURCE_MODULE_ID = "professional_finding_candidate_lite_v1"
CANONICAL_EVENT_COUNT = TRUE_ACTION_COUNT = "UNKNOWN"
CLAIM_CEILING = "MATCH_LOCAL_VISIBLE_PROCESS_VARIANT_DIFFERENCE_ANALYST_READING_ONLY"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _human_resolution(value: Any) -> str:
    mapping = {
        "CONTINUATION_OR_ADVANCE_VISIBLE_VARIANT": "görünür devam / ilerleme",
        "ADVERSE_HANDOVER_VISIBLE_VARIANT": "rakibe görünür geçiş",
        "RECOVERY_AFTER_BREAKDOWN_VISIBLE_VARIANT": "bozulma sonrası görünür geri kazanım",
        "RESET_OR_RESTART_VISIBLE_VARIANT": "reset / restart",
        "TERMINAL_VISIBLE_VARIANT": "terminal görünür sonuç",
        "OTHER_VISIBLE_CONSEQUENCE_VARIANT": "diğer görünür sonuç",
    }
    raw = _clean(value)
    return mapping.get(raw, raw or "belirsiz")


def _dimension_text(item: dict[str, Any]) -> str:
    dimension = _clean(item.get("observation_dimension"))
    modal = item.get("modal_candidate")
    deviant = item.get("deviant_candidate")
    labels = {
        "response_latency_median_candidate_seconds": "rakip görünür cevabının zamanlaması",
        "counter_response_visible_count": "anchor takımın sonraki görünür cevabı",
        "counter_response_action_family_presence_counts": "sonraki görünür aksiyon ailesi",
        "response_consequence_family_presence_counts": "rakip cevabının görünür consequence ailesi",
        "counter_response_consequence_family_presence_counts": "anchor takımın sonraki görünür consequence ailesi",
        "episode_scope_count_candidate": "göründüğü episode kapsamı",
    }
    label = labels.get(dimension, dimension or "gözlem boyutu")
    return f"{label}: normal={modal!r}, ayrışan={deviant!r}"


def compose_process_variant_difference_report(finding_payload: dict[str, Any]) -> dict[str, Any]:
    """Project already-bound process variant differences into analyst-readable Turkish blocks.

    This is a presentation layer over existing admitted match-local differences. It does
    not create a new football observation, independent evidence vote, causal explanation,
    tactical-plan truth, coach-intention truth or production release permission.
    """
    hard: list[str] = []
    if finding_payload.get("module_id") != SOURCE_MODULE_ID:
        hard.append("source_module_id_mismatch")
    if finding_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        hard.append("canonical_event_count_claimed")
    if finding_payload.get("true_action_count") not in {None, TRUE_ACTION_COUNT}:
        hard.append("true_action_count_claimed")
    if finding_payload.get("production_release") is True:
        hard.append("production_release_claimed")
    if finding_payload.get("hard_block_hits") or _clean(finding_payload.get("status")).upper() == "FAIL_CLOSED":
        hard.append("source_fail_closed")
    if hard:
        return {
            "module_id": MODULE_ID,
            "status": "FAIL_CLOSED",
            "report_blocks": [],
            "report_block_count": 0,
            "hard_block_hits": sorted(set(hard)),
            "canonical_event_count": CANONICAL_EVENT_COUNT,
            "true_action_count": TRUE_ACTION_COUNT,
            "production_release": False,
            "claim_ceiling": CLAIM_CEILING,
        }

    blocks: list[dict[str, Any]] = []
    for finding in finding_payload.get("professional_finding_candidates") or []:
        if not isinstance(finding, dict):
            continue
        finding_id = _clean(finding.get("professional_finding_candidate_id"))
        explanations = [
            row for row in (finding.get("visible_process_variant_difference_explanations") or [])
            if isinstance(row, dict)
        ]
        for index, explanation in enumerate(explanations):
            if explanation.get("difference_is_causal_explanation") is not False:
                continue
            if explanation.get("difference_is_tactical_adaptation_truth") is not False:
                continue
            if explanation.get("difference_is_coach_intention_truth") is not False:
                continue
            if explanation.get("right_censoring_used_as_counterevidence") is not False:
                continue

            modal = _human_resolution(explanation.get("modal_resolution_class_candidate"))
            deviant = _human_resolution(explanation.get("deviant_resolution_class_candidate"))
            differences = [
                item for item in (explanation.get("visible_difference_candidates") or [])
                if isinstance(item, dict) and _clean(item.get("observation_dimension"))
            ]
            difference_lines = [_dimension_text(item) for item in differences]
            normal_text = f"NORMAL VARYANT: Bu görünür process ailesinin maç içi modal çözülmesi {modal}."
            deviant_text = f"AYRIŞAN VARYANT: Karşılaştırılabilir ayrışan çözülme {deviant}."
            if difference_lines:
                visible_text = "GÖRÜNÜR FARK: " + "; ".join(difference_lines) + "."
            else:
                visible_text = "GÖRÜNÜR FARK: Mevcut admitted gözlemler ek bir ayrıştırıcı boyut göstermedi."
            action = _clean(finding.get("ANALYST_ACTION") or finding.get("analyst_action"))
            analyst_text = (
                "ANALİST AKSİYONU: " + action
                if action
                else "ANALİST AKSİYONU: Normal ve ayrışan örnekleri aynı görünür fark boyutları üzerinden birlikte incele."
            )
            safe_text = (
                f"{normal_text} {deviant_text} {visible_text} {analyst_text} "
                "Bu farklar aynı maçta birlikte gözlenmiştir; neden, taktik adaptasyon veya teknik direktör niyeti kanıtı değildir."
            )
            blocks.append({
                "report_block_id": f"pvd_report_{finding_id or 'UNKNOWN'}_{index}",
                "block_family": "process_variant_difference_analyst_reading_candidate",
                "block_language": "tr",
                "source_professional_finding_candidate_id": finding_id or None,
                "normal_variant_tr": normal_text,
                "deviant_variant_tr": deviant_text,
                "visible_difference_tr": visible_text,
                "analyst_action_tr": analyst_text,
                "report_block_candidate_tr": safe_text,
                "visible_difference_candidates": differences,
                "safe_meaning": _clean(explanation.get("safe_meaning")),
                "alternative_explanations": list(explanation.get("alternative_explanations") or []),
                "difference_is_causal_explanation": False,
                "difference_is_tactical_adaptation_truth": False,
                "difference_is_coach_intention_truth": False,
                "right_censoring_used_as_counterevidence": False,
                "independent_evidence_vote_created": False,
                "production_report_allowed": False,
                "final_report_allowed": False,
                "canonical_event_count": CANONICAL_EVENT_COUNT,
                "true_action_count": TRUE_ACTION_COUNT,
                "production_release": False,
                "claim_ceiling": CLAIM_CEILING,
            })

    return {
        "module_id": MODULE_ID,
        "source_module_id": SOURCE_MODULE_ID,
        "status": "PASS" if blocks else "NO_ELIGIBLE_PROCESS_VARIANT_DIFFERENCE_REPORT_BLOCK",
        "report_blocks": blocks,
        "report_block_count": len(blocks),
        "hard_block_hits": [],
        "difference_report_creates_independent_evidence": False,
        "difference_report_is_causal_explanation": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": TRUE_ACTION_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }
