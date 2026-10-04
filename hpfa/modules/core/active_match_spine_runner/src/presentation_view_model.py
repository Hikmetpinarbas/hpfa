from __future__ import annotations

import html
from typing import Any

MODULE_ID = "hpfa_presentation_view_model_v2"
CLAIM_CEILING = "INHERITS_UPSTREAM_NO_STRENGTHENING"
FACT_ONLY_RENDER = "FACT_ONLY_RENDER"


def _fact_review_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    source_by_ref = {
        str(row.get("analyst_output_contract_id")): row
        for row in payload.get("analyst_output_contracts") or []
        if isinstance(row, dict) and row.get("analyst_output_contract_id")
    }
    records: list[dict[str, Any]] = []
    for rendered in payload.get("source_bound_render_contracts") or []:
        if not isinstance(rendered, dict):
            continue
        validation = rendered.get("render_validation")
        sentence_contract = rendered.get("rendered_sentence_contract")
        if not isinstance(validation, dict) or not isinstance(sentence_contract, dict):
            continue
        if validation.get("render_allowed") is not True:
            continue
        if str(validation.get("render_completeness_state") or "") != FACT_ONLY_RENDER:
            continue
        if sentence_contract.get("professional_emit_allowed") is True:
            continue
        source_ref = str(
            sentence_contract.get("source_analyst_output_contract_ref")
            or rendered.get("source_analyst_output_contract_ref")
            or ""
        ).strip()
        source = source_by_ref.get(source_ref, {})
        records.append({
            "source_analyst_output_contract_ref": source_ref,
            "render_state": FACT_ONLY_RENDER,
            "professional_emit_allowed": False,
            "claim_scope": sentence_contract.get("claim_scope") or validation.get("rendered_claim_scope"),
            "safe_finding_admission_decision": source.get("safe_finding_admission_decision"),
            "sentence_tr": (
                rendered.get("final_human_sentence_tr")
                or sentence_contract.get("rendered_sentence_tr")
                or validation.get("rendered_sentence_tr")
            ),
            "what_visible": sentence_contract.get("what_visible") or validation.get("what_visible"),
            "safe_meaning": sentence_contract.get("safe_meaning") or validation.get("safe_meaning"),
            "analyst_action": sentence_contract.get("analyst_action") or validation.get("analyst_action"),
            "evidence_refs": list(sentence_contract.get("evidence_refs") or validation.get("rendered_evidence_refs") or []),
            "counterevidence_refs": list(
                sentence_contract.get("counterevidence_refs")
                or validation.get("rendered_counterevidence_refs")
                or []
            ),
            "counter_scenarios": list(
                sentence_contract.get("counter_scenarios")
                or validation.get("counter_scenarios")
                or []
            ),
            "withdrawal_conditions": list(
                sentence_contract.get("withdrawal_conditions")
                or validation.get("withdrawal_conditions")
                or []
            ),
            "required_qualifiers": list(
                sentence_contract.get("required_qualifiers")
                or validation.get("rendered_required_qualifiers")
                or []
            ),
            "forbidden_claim_families": list(
                sentence_contract.get("forbidden_claim_families")
                or validation.get("rendered_forbidden_claim_families")
                or []
            ),
            "rendered_observation_counts": {
                "status": "UNAVAILABLE_AS_STRUCTURED_FIELDS",
                "note": "Do not substitute rate-bound denominator fields for counts embedded in the rendered observation sentence.",
            },
            "rate_bound_context": {
                "estimand_id": source.get("rate_bound_estimand_id"),
                "denominator_basis": source.get("rate_bound_denominator_basis"),
                "eligible_total_n": source.get("rate_bound_eligible_total_n"),
                "resolved_success_n": source.get("rate_bound_resolved_success_n"),
                "resolved_failure_n": source.get("rate_bound_resolved_failure_n"),
                "unresolved_eligible_n": source.get("rate_bound_unresolved_eligible_n"),
                "state": source.get("rate_bound_state"),
                "lower": source.get("rate_bound_lower"),
                "upper": source.get("rate_bound_upper"),
                "is_confidence_interval": source.get("rate_bound_is_confidence_interval") is True,
                "is_true_probability": source.get("rate_bound_is_true_probability") is True,
                "is_population_rate": source.get("rate_bound_is_population_rate") is True,
                "is_denominator_for_rendered_sentence": False,
            },
            "observed_sample_description_only": True,
            "record_creates_new_evidence": False,
            "record_can_authorize_emit": False,
        })
    return records


def _professional_claim_records(payload: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in payload.get("analyst_output_contracts") or []:
        if not isinstance(row, dict) or row.get("professional_emit_allowed") is not True:
            continue
        records.append({
            "analyst_output_contract_id": row.get("analyst_output_contract_id"),
            "claim_scope": row.get("claim_scope"),
            "safe_output_meaning": row.get("safe_output_meaning"),
            "render_what_visible_text_tr": row.get("render_what_visible_text_tr"),
            "render_safe_meaning": row.get("render_safe_meaning"),
            "render_analyst_action": row.get("render_analyst_action"),
            "render_counterevidence_refs": list(row.get("render_counterevidence_refs") or []),
            "withdrawal_condition_candidates": list(row.get("withdrawal_condition_candidates") or []),
            "required_qualifiers": list(row.get("required_qualifiers") or []),
            "claim_record_creates_new_evidence": False,
        })
    return records


def build_presentation_view_model(
    full_spine: dict[str, Any],
    *,
    analyst_report_tr: str,
    analyst_report_en: str,
    mechanism_graph_payload: dict[str, Any],
    analyst_output_claim_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cards = [
        dict(card)
        for card in mechanism_graph_payload.get("cards") or []
        if isinstance(card, dict)
    ]
    graphability_counts: dict[str, int] = {}
    for card in cards:
        state = str(card.get("graphability_state") or "UNKNOWN")
        graphability_counts[state] = graphability_counts.get(state, 0) + 1

    claim_payload = analyst_output_claim_payload or {}
    fact_records = _fact_review_records(claim_payload)
    professional_claims = _professional_claim_records(claim_payload)

    return {
        "module_id": MODULE_ID,
        "status": full_spine.get("status"),
        "active_match_authority": full_spine.get("active_match_authority"),
        "presentation_scope": "CURRENT_USER_OUTPUT_BUNDLE_VIEW_ONLY",
        "claim_ceiling": CLAIM_CEILING,
        "view_model_creates_new_evidence": False,
        "view_model_can_strengthen_claim_ceiling": False,
        "view_model_can_authorize_emit": False,
        "visual_prominence_is_confidence": False,
        "presentation_order_is_evidence_rank": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "reports": {
            "tr": analyst_report_tr,
            "en": analyst_report_en,
        },
        "claim_admission_summary": {
            "source_status": claim_payload.get("status"),
            "source_contract_count": claim_payload.get("analyst_output_contract_count"),
            "professional_emit_allowed_count": len(professional_claims),
            "fact_only_render_count": len(fact_records),
            "zero_professional_emit_is_valid": True,
            "fact_only_render_is_professional_finding": False,
        },
        "professional_claim_records": professional_claims,
        "fact_review_records": fact_records,
        "mechanism_cards": cards,
        "mechanism_card_count": len(cards),
        "graphability_state_counts": graphability_counts,
        "presentation_truth_locks": [
            "coordinate != tracking",
            "provider label != physical/tactical truth",
            "same timestamp != total order",
            "aggregate != action identity",
            "model output != fact",
            "absence != counterevidence",
            "visual prominence != confidence",
            "fact-only render != professional finding",
            "raw rate != true probability",
        ],
    }


def _list_html(values: list[Any]) -> str:
    return "".join(f"<li>{html.escape(str(value))}</li>" for value in values)


def render_professional_html(view_model: dict[str, Any], *, language: str = "tr") -> str:
    lang = "tr" if language.casefold().startswith("tr") else "en"
    reports = view_model.get("reports") or {}
    report_text = str(reports.get(lang) or reports.get("tr") or reports.get("en") or "")
    status = html.escape(str(view_model.get("status") or "UNKNOWN"))
    authority = html.escape(str(view_model.get("active_match_authority") or "UNKNOWN"))
    cards = [card for card in view_model.get("mechanism_cards") or [] if isinstance(card, dict)]
    fact_records = [row for row in view_model.get("fact_review_records") or [] if isinstance(row, dict)]
    professional_claims = [
        row for row in view_model.get("professional_claim_records") or []
        if isinstance(row, dict)
    ]
    claim_summary = view_model.get("claim_admission_summary") or {}

    card_html: list[str] = []
    for card in cards:
        title = html.escape(str(
            card.get("title")
            or card.get("process_family_candidate")
            or card.get("mechanism_family_candidate")
            or card.get("card_id")
            or "Mechanism candidate"
        ))
        graphability = html.escape(str(card.get("graphability_state") or "UNKNOWN"))
        ceiling = html.escape(str(card.get("claim_ceiling") or CLAIM_CEILING))
        recommendations_html = _list_html(list(card.get("graph_recommendations") or []))
        card_html.append(
            "<article class=\"card\">"
            f"<h3>{title}</h3>"
            f"<div class=\"meta\">Graphability: {graphability}</div>"
            f"<div class=\"meta\">Claim ceiling: {ceiling}</div>"
            + (f"<ul>{recommendations_html}</ul>" if recommendations_html else "")
            + "</article>"
        )

    fact_html: list[str] = []
    for idx, record in enumerate(fact_records, 1):
        rate_bound = record.get("rate_bound_context") or {}
        counter = list(record.get("counter_scenarios") or [])
        withdrawals = list(record.get("withdrawal_conditions") or [])
        qualifiers = list(record.get("required_qualifiers") or [])
        sentence = html.escape(str(record.get("sentence_tr") or record.get("what_visible") or ""))
        ref = html.escape(str(record.get("source_analyst_output_contract_ref") or "UNKNOWN"))
        rate_bound_estimand = rate_bound.get("estimand_id")
        if rate_bound_estimand:
            rate_bound_line = (
                "Separate rate-bound context — "
                f"estimand={html.escape(str(rate_bound_estimand))} · "
                f"denominator basis={html.escape(str(rate_bound.get('denominator_basis') or 'UNKNOWN'))} · "
                f"eligible={html.escape(str(rate_bound.get('eligible_total_n')))} · "
                f"success={html.escape(str(rate_bound.get('resolved_success_n')))} · "
                f"failure={html.escape(str(rate_bound.get('resolved_failure_n')))} · "
                f"unresolved={html.escape(str(rate_bound.get('unresolved_eligible_n')))}"
            )
        else:
            rate_bound_line = "Separate rate-bound context: UNAVAILABLE"
        fact_html.append(
            "<details class=\"fact\">"
            f"<summary>Fact-only review {idx}: {sentence}</summary>"
            f"<div class=\"meta\">Source contract: {ref}</div>"
            "<div class=\"meta\">Rendered observation denominator: UNAVAILABLE_AS_STRUCTURED_FIELDS</div>"
            f"<div class=\"meta\">{rate_bound_line}</div>"
            "<div class=\"boundary-note\">Observed sample description only; not a professional finding, probability, causal effect, or independent recurrence claim. Any rate-bound context shown below is a separate estimand and is not the denominator of the rendered sentence.</div>"
            + (f"<h4>Counter-scenarios</h4><ul>{_list_html(counter)}</ul>" if counter else "")
            + (f"<h4>Withdrawal / qualification conditions</h4><ul>{_list_html(withdrawals)}</ul>" if withdrawals else "")
            + (f"<h4>Required qualifiers</h4><ul>{_list_html(qualifiers)}</ul>" if qualifiers else "")
            + "</details>"
        )

    professional_claim_html = ""
    if professional_claims:
        professional_claim_html = "".join(
            "<article class=\"claim\">"
            f"<h3>{html.escape(str(row.get('render_what_visible_text_tr') or row.get('analyst_output_contract_id') or 'Admitted claim'))}</h3>"
            f"<p>{html.escape(str(row.get('render_safe_meaning') or row.get('safe_output_meaning') or ''))}</p>"
            "</article>"
            for row in professional_claims
        )
    else:
        professional_claim_html = (
            "<article class=\"empty-claim\"><strong>0 professional claim admitted.</strong> "
            "Current upstream contract permits fact-only rendering, not professional finding emission.</article>"
        )

    locks = _list_html(list(view_model.get("presentation_truth_locks") or []))
    escaped_report = html.escape(report_text)
    professional_n = html.escape(str(claim_summary.get("professional_emit_allowed_count", 0)))
    fact_n = html.escape(str(claim_summary.get("fact_only_render_count", 0)))

    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HPFA Professional Match Report</title>
<style>
:root {{ font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #171717; background: #f5f5f3; }}
body {{ margin: 0; }}
main {{ max-width: 1120px; margin: 0 auto; padding: 36px 24px 64px; }}
header {{ border-bottom: 1px solid #d7d7d2; padding-bottom: 22px; margin-bottom: 28px; }}
h1 {{ font-size: 28px; margin: 0 0 8px; letter-spacing: -0.02em; }}
h2 {{ margin-top: 34px; font-size: 19px; }}
h3 {{ margin: 0 0 10px; font-size: 16px; }}
h4 {{ margin-bottom: 6px; }}
.status {{ display: inline-block; padding: 5px 9px; border: 1px solid #a8a8a2; border-radius: 999px; font-size: 12px; }}
.meta {{ color: #61615c; font-size: 12px; margin: 5px 0; overflow-wrap: anywhere; }}
.report {{ white-space: pre-wrap; background: #fff; border: 1px solid #deded9; padding: 22px; line-height: 1.55; font-family: inherit; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
.card,.claim,.empty-claim {{ background: #fff; border: 1px solid #deded9; padding: 16px; }}
.guard {{ background: #ecece8; border-left: 3px solid #777770; padding: 14px 18px; }}
.fact {{ background: #fff; border: 1px solid #deded9; padding: 12px 16px; margin: 8px 0; }}
.fact summary {{ cursor: pointer; line-height: 1.45; }}
.boundary-note {{ margin: 10px 0; padding: 9px 11px; background: #f2f2ef; font-size: 12px; }}
.kpis {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 12px 0 18px; }}
.kpi {{ background: #fff; border: 1px solid #deded9; padding: 12px 16px; min-width: 160px; }}
.kpi strong {{ display: block; font-size: 24px; }}
ul {{ padding-left: 20px; }}
footer {{ margin-top: 38px; border-top: 1px solid #d7d7d2; padding-top: 16px; color: #686862; font-size: 12px; }}
@media print {{ body {{ background: #fff; }} main {{ max-width: none; padding: 12mm; }} .card,.report,.fact {{ break-inside: avoid; }} }}
</style>
</head>
<body>
<main>
<header>
<h1>HPFA — Professional Match Report</h1>
<span class="status">{status}</span>
<div class="meta">Active match authority: {authority}</div>
<div class="meta">Presentation layer · evidence/claim authority remains upstream</div>
</header>

<section>
<h2>Claim admission</h2>
<div class="kpis">
<div class="kpi"><strong>{professional_n}</strong>Professional claims admitted</div>
<div class="kpi"><strong>{fact_n}</strong>Fact-only review records</div>
</div>
{professional_claim_html}
</section>

<section>
<h2>Analyst report</h2>
<div class="report">{escaped_report}</div>
</section>

<section>
<h2>Mechanism review surface</h2>
<div class="grid">{''.join(card_html) if card_html else '<article class="card">No graph-ready mechanism card emitted.</article>'}</div>
</section>

<section>
<h2>Fact-only evidence review</h2>
<div class="boundary-note">These records are source-bound visible sample descriptions. Presentation order is not evidence rank. They do not authorize professional finding emission.</div>
{''.join(fact_html) if fact_html else '<article class="card">No fact-only render record admitted.</article>'}
</section>

<section class="guard">
<h2>Interpretation boundary</h2>
<ul>{locks}</ul>
</section>

<footer>
canonical_event_count=UNKNOWN · true_action_count=UNKNOWN · production_release=false · presentation cannot strengthen claim ceiling
</footer>
</main>
</body>
</html>
"""
