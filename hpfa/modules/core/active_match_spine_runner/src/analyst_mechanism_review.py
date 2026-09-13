from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FEATURE_DELTA_JSON = "grammar_stable_variant_feature_delta_projection_v1.json"
IDENTITY_JSON = "match_local_identity_candidates_lite_v1.json"
OCCURRENCE_CONSEQUENCE_JSON = "occurrence_consequence_projection_v1.json"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _declared_current(full_spine: dict[str, Any], filename: str) -> bool:
    for value in full_spine.get("current_invocation_artifacts") or []:
        if Path(str(value)).name == filename:
            return True
    return False


def _pretty_key(value: Any) -> str:
    return str(value or "").strip().replace("_", " ").title()


def _team_names(identity_payload: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in identity_payload.get("team_identity_candidates") or []:
        if not isinstance(row, dict):
            continue
        ref = str(row.get("team_identity_candidate_id") or "").strip()
        name = str(row.get("team_normalized_key") or "").strip()
        if ref and name:
            result[ref] = _pretty_key(name)
    return result


def _actor_names(identity_payload: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in identity_payload.get("actor_identity_candidates") or []:
        if not isinstance(row, dict):
            continue
        ref = str(row.get("actor_identity_candidate_id") or "").strip()
        name = str(row.get("actor_normalized_key") or "").strip()
        if ref and name:
            result[ref] = _pretty_key(name)
    return result


def _grammar_label(tokens: list[Any]) -> str:
    rendered: list[str] = []
    for raw in tokens:
        token = str(raw or "").strip()
        if token.startswith("LAYER[") and token.endswith("]"):
            body = token[6:-1]
            if "|" in body:
                body = " + ".join(part for part in body.split("|") if part)
                body += " (same-time unordered)"
            rendered.append(body)
        elif token:
            rendered.append(token)
    return " -> ".join(rendered) if rendered else "UNRESOLVED_GRAMMAR"


def _feature_row(record: dict[str, Any], token: str) -> dict[str, Any] | None:
    for row in record.get("consequence_feature_difference_candidates") or []:
        if isinstance(row, dict) and str(row.get("feature_token") or "") == token:
            return row
    return None


def _fmt_counts(row: dict[str, Any] | None) -> str | None:
    if not row:
        return None
    return (
        f"success={int(row.get('success_visible_numerator') or 0)}/"
        f"{int(row.get('success_eligible_denominator') or 0)} "
        f"failure={int(row.get('failure_visible_numerator') or 0)}/"
        f"{int(row.get('failure_eligible_denominator') or 0)}"
    )


def _occurrence_spine_lines(root: Path, full_spine: dict[str, Any]) -> list[str]:
    if not _declared_current(full_spine, OCCURRENCE_CONSEQUENCE_JSON):
        return [
            "primary_occurrence_spine=UNAVAILABLE_CURRENT_INVOCATION",
            "surface_role_note=Episode/action-volume adaylari primary action identity sayimi degildir.",
        ]
    payload = _load_json(root / OCCURRENCE_CONSEQUENCE_JSON)
    if not payload or str(payload.get("status") or "").upper() == "FAIL_CLOSED":
        return [
            "primary_occurrence_spine=FAIL_CLOSED_OR_UNREADABLE",
            "surface_role_note=Episode/action-volume adaylari primary action identity sayimi degildir.",
        ]
    return [
        "primary_occurrence_spine: "
        f"occurrence_candidates={int(payload.get('occurrence_consequence_projection_count') or 0)} "
        f"visible_consequence_support={int(payload.get('occurrence_with_visible_consequence_support_count') or 0)} "
        f"fully_observed_no_followup={int(payload.get('complete_to_declared_horizon_no_admitted_followup_count') or 0)} "
        f"right_censored={int(payload.get('right_censored_occurrence_count') or 0)} "
        f"unresolved_censoring={int(payload.get('right_censoring_unresolved_occurrence_count') or 0)}",
        "surface_role_note=Primary occurrence spine futbol aksiyon-uyesi aday yuzeyidir; "
        "episode/action-volume ve legacy trace yuzeyleri support/context'tir, canonical action count degildir.",
    ]


def _context_focus_candidates(record: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in record.get("context_feature_difference_candidates") or []:
        if not isinstance(row, dict):
            continue
        token = str(row.get("feature_token") or "")
        # Outcome-adjacent, navigation-only, provider-direction and generic participation
        # labels are not promoted as positive football mechanism review focus.
        if "process_shot_present_annotation_candidate" in token:
            continue
        if "process_episode_navigation_binding_visible" in token:
            continue
        if "provider_direction_candidates" in token:
            continue
        if "process_semantic_role" in token:
            continue
        if "actor_identity_candidate_ids:" in token or "process_family_candidate:" in token:
            result.append(row)
    return result


def _render_context_focus(record: dict[str, Any], actors: dict[str, str]) -> str:
    candidates = _context_focus_candidates(record)
    if not candidates:
        return "NO_NON_OUTCOME_CONTEXT_OR_ACTOR_CONTRAST_EXPOSED"
    row = max(
        candidates,
        key=lambda item: abs(float(item.get("descriptive_rate_delta_success_minus_failure") or 0.0)),
    )
    token = str(row.get("feature_token") or "")
    label = token
    if "actor_identity_candidate_ids:" in token:
        actor_ref = token.rsplit("actor_identity_candidate_ids:", 1)[-1]
        label = "actor=" + actors.get(actor_ref, actor_ref)
    elif "process_family_candidate:" in token:
        family = token.rsplit("process_family_candidate:", 1)[-1]
        label = "process_context=" + _pretty_key(family)
    success_n = int(row.get("success_visible_numerator") or 0)
    success_d = int(row.get("success_eligible_denominator") or 0)
    failure_n = int(row.get("failure_visible_numerator") or 0)
    failure_d = int(row.get("failure_eligible_denominator") or 0)
    delta = float(row.get("descriptive_rate_delta_success_minus_failure") or 0.0)
    return (
        f"{label} success={success_n}/{success_d} failure={failure_n}/{failure_d} "
        f"descriptive_rate_delta={delta:+.3f}"
    )


def build_mechanism_review_lines(
    output_root: str | Path,
    full_spine: dict[str, Any],
) -> list[str]:
    """Render current grammar-stable process differences for analyst review only.

    This function creates no evidence, no causal/tactical claim and no EMIT authority.
    Continuation/handover contrasts are explicitly treated as outcome-adjacent; the
    positive review focus is the largest currently exposed non-outcome actor/process
    context contrast, when one exists.
    """
    root = Path(output_root)
    if not _declared_current(full_spine, FEATURE_DELTA_JSON):
        return ["- Current invocation process-difference surface mevcut degil; eski artifact kullanilmadi."]

    payload = _load_json(root / FEATURE_DELTA_JSON)
    if not payload or str(payload.get("status") or "").upper() == "FAIL_CLOSED":
        return ["- Process-difference surface fail-closed veya okunamadi; mekanizma adayi uretilmedi."]

    identity = _load_json(root / IDENTITY_JSON) if _declared_current(full_spine, IDENTITY_JSON) else {}
    teams = _team_names(identity)
    actors = _actor_names(identity)
    records = [
        row for row in (payload.get("grammar_stable_variant_feature_delta_records") or [])
        if isinstance(row, dict)
    ]
    if not records:
        return ["- Bu run'da grammar-stable visible-outcome variation ailesi gorunmedi."]

    lines = [
        "Bu bolum YAYINLANABILIR BULGU degildir; analyst-review mekanizma adayidir.",
        "Adaylar siralanmamistir. Oranlar gercek basari olasiligi degildir ve causality/tactical-plan kaniti sayilmaz.",
        *_occurrence_spine_lines(root, full_spine),
        "information_value_guard=SUCCESS/FAILURE ile same-team continuation/opponent handover farki outcome'a yakindir; tek basina mac mekanizmasi sayilmaz.",
    ]
    for index, record in enumerate(records, start=1):
        team_ids = [str(value) for value in (record.get("team_identity_candidate_ids") or []) if str(value)]
        team = ", ".join(teams.get(value, value) for value in team_ids) or "UNRESOLVED_TEAM"
        periods = ",".join(str(value) for value in (record.get("period_candidates") or [])) or "UNKNOWN"
        grammar = _grammar_label(list(record.get("grammar_signature_tokens") or []))
        resolved = int(record.get("resolved_variant_count") or 0)
        success = int(record.get("success_resolved_variant_count") or 0)
        failure = int(record.get("failure_resolved_variant_count") or 0)
        first_consequence_layer = record.get("first_supported_consequence_difference_layer_candidate")
        first_context_layer = record.get("first_supported_context_difference_layer_candidate")
        process_context_missing = int(record.get("process_context_coverage_incomplete_variant_count") or 0)
        right_censored = int(record.get("right_censored_variant_count") or 0)

        lines.append(
            f"- M{index} | {team} | period={periods} | grammar={grammar} | "
            f"resolved={resolved} (SUCCESS={success}, FAILURE={failure})"
        )
        lines.append(
            f"  first_visible_difference: context_layer={first_context_layer} consequence_layer={first_consequence_layer}"
        )

        facts = [
            ("same_team_continuation", "LAYER[1]::primary_consequence_candidates:SAME_TEAM_CONTINUATION_CANDIDATE"),
            ("opponent_handover", "LAYER[1]::primary_consequence_candidates:OPPONENT_HANDOVER_CANDIDATE"),
            ("no_visible_followup", "LAYER[1]::followup_observation_status:NO_VISIBLE_FOLLOWUP"),
            ("process_state_unresolved", "LAYER[1]::process_continuation_status:PROCESS_STATE_UNRESOLVED"),
        ]
        rendered_facts = []
        for label, token in facts:
            counts = _fmt_counts(_feature_row(record, token))
            if counts:
                rendered_facts.append(f"{label} {counts}")
        if rendered_facts:
            lines.append("  outcome_adjacent_consequence_contrast: " + " | ".join(rendered_facts))

        focus = _render_context_focus(record, actors)
        lines.append("  positive_review_focus: " + focus)
        lines.append(
            f"  uncertainty: process_context_missing={process_context_missing}/{resolved} "
            f"right_censored={right_censored}/{resolved} dependency_independence_proven="
            f"{str(record.get('dependency_independence_proven') is True).lower()}"
        )
        lines.append(
            "  analyst_meaning: Once actor/process-context farkini videoda kontrol et; "
            "continuation/handover farkini tek basina mekanizma, neden, taktik plan, oyuncu kalitesi "
            "veya gercek basari olasiligi olarak yorumlama."
        )

    lines.extend([
        "analyst_action=VIDEO_OR_MATCH_REVIEW_OF_CONTEXT_ENRICHED_VISIBLE_DIFFERENCE_CANDIDATES",
        "claim_ceiling=ANALYST_REVIEW_MECHANISM_CANDIDATE_ONLY",
        "professional_emit_allowed=false",
    ])
    return lines
