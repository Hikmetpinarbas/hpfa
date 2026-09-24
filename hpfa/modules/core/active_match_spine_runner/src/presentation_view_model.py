from __future__ import annotations

import html
from typing import Any

MODULE_ID = "hpfa_presentation_view_model_v1"
CLAIM_CEILING = "INHERITS_UPSTREAM_NO_STRENGTHENING"


def build_presentation_view_model(
    full_spine: dict[str, Any],
    *,
    analyst_report_tr: str,
    analyst_report_en: str,
    mechanism_graph_payload: dict[str, Any],
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
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "reports": {
            "tr": analyst_report_tr,
            "en": analyst_report_en,
        },
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
        ],
    }


def render_professional_html(view_model: dict[str, Any], *, language: str = "tr") -> str:
    lang = "tr" if language.casefold().startswith("tr") else "en"
    reports = view_model.get("reports") or {}
    report_text = str(reports.get(lang) or reports.get("tr") or reports.get("en") or "")
    status = html.escape(str(view_model.get("status") or "UNKNOWN"))
    authority = html.escape(str(view_model.get("active_match_authority") or "UNKNOWN"))
    cards = [card for card in view_model.get("mechanism_cards") or [] if isinstance(card, dict)]

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
        recommendations = [
            html.escape(str(value))
            for value in card.get("graph_recommendations") or []
        ]
        recommendations_html = "".join(f"<li>{item}</li>" for item in recommendations)
        card_html.append(
            "<article class=\"card\">"
            f"<h3>{title}</h3>"
            f"<div class=\"meta\">Graphability: {graphability}</div>"
            f"<div class=\"meta\">Claim ceiling: {ceiling}</div>"
            + (f"<ul>{recommendations_html}</ul>" if recommendations_html else "")
            + "</article>"
        )

    locks = "".join(
        f"<li>{html.escape(str(lock))}</li>"
        for lock in view_model.get("presentation_truth_locks") or []
    )
    escaped_report = html.escape(report_text)
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
.status {{ display: inline-block; padding: 5px 9px; border: 1px solid #a8a8a2; border-radius: 999px; font-size: 12px; }}
.meta {{ color: #61615c; font-size: 12px; margin: 5px 0; overflow-wrap: anywhere; }}
.report {{ white-space: pre-wrap; background: #fff; border: 1px solid #deded9; padding: 22px; line-height: 1.55; font-family: inherit; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
.card {{ background: #fff; border: 1px solid #deded9; padding: 16px; }}
.guard {{ background: #ecece8; border-left: 3px solid #777770; padding: 14px 18px; }}
ul {{ padding-left: 20px; }}
footer {{ margin-top: 38px; border-top: 1px solid #d7d7d2; padding-top: 16px; color: #686862; font-size: 12px; }}
@media print {{ body {{ background: #fff; }} main {{ max-width: none; padding: 12mm; }} .card,.report {{ break-inside: avoid; }} }}
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
<h2>Analyst report</h2>
<div class="report">{escaped_report}</div>
</section>
<section>
<h2>Mechanism review surface</h2>
<div class="grid">{''.join(card_html) if card_html else '<article class="card">No graph-ready mechanism card emitted.</article>'}</div>
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
