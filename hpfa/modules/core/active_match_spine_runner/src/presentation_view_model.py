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



def _team_name_map(identity_payload: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in identity_payload.get("team_identity_candidates") or []:
        if not isinstance(row, dict):
            continue
        ref = str(row.get("team_identity_candidate_id") or "").strip()
        if not ref:
            continue
        aliases = [str(v).strip() for v in (row.get("team_aliases_raw") or []) if str(v).strip()]
        name = aliases[0] if aliases else str(row.get("team_normalized_key") or ref)
        if " (" in name:
            name = name.split(" (", 1)[0]
        result[ref] = name.strip().title()
    return result


def _score_text(score_state: dict[str, Any]) -> str:
    parts: list[str] = []
    for name, value in score_state.items():
        label = str(name).split(" (", 1)[0].strip()
        parts.append(f"{label} {value}")
    return " – ".join(parts)


def _process_label(values: list[Any]) -> str:
    mapping = {
        "POSITIONAL_ATTACK_CANDIDATE": "yerleşik hücum adayı",
        "TRANSITION_ATTACK_CANDIDATE": "geçiş hücumu adayı",
        "SET_PIECE_ATTACK_CANDIDATE": "duran top hücumu adayı",
    }
    labels = [mapping.get(str(v), str(v).replace("_CANDIDATE", "").replace("_", " ").lower()) for v in values]
    return ", ".join(labels) if labels else "görünür sekans adayı"


def _match_local_descriptive_records(
    safe_payload: dict[str, Any],
    identity_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    team_names = _team_name_map(identity_payload)
    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for row in safe_payload.get("safe_finding_admission_decisions") or []:
        if not isinstance(row, dict) or row.get("match_local_descriptive_finding_admitted") is not True:
            continue
        context = row.get("branch_preoutcome_context_enrichment") or {}
        score_state = context.get("score_state_candidate") or {}
        key = (
            tuple(row.get("variant_feature_challenge_family_refs") or []),
            context.get("team_identity_candidate_id"),
            context.get("period_candidate"),
            tuple(sorted(score_state.items())),
            tuple(context.get("provider_process_family_candidates") or []),
            tuple(sorted((context.get("anchor_action_family_counts") or {}).items())),
        )
        grouped.setdefault(key, []).append(row)

    records: list[dict[str, Any]] = []
    for key, rows in grouped.items():
        family_refs, team_ref, period, score_items, process_values, anchor_items = key
        score_state = dict(score_items)
        team_name = team_names.get(str(team_ref), "Takım")
        period_label = f"{period}. devre" if str(period).isdigit() else str(period or "devre bilinmiyor")
        process_label = _process_label(list(process_values))
        anchor_map = {"PASS": "pas", "CARRY": "top taşıma", "SHOT": "şut", "CROSS": "orta"}
        anchor_actions = ", ".join(anchor_map.get(str(name), str(name).replace("_", " ").lower()) for name, count in anchor_items if int(count or 0) > 0) or "aksiyon"
        episode_spread = max(int(row.get("variant_support_episode_spread_max_visible_count") or 0) for row in rows)
        actor_spread = max(int(row.get("actor_spread_count") or 0) for row in rows)
        times = sorted({
            (row.get("branch_preoutcome_context_enrichment") or {}).get("shared_anchor_time_candidate")
            for row in rows
            if (row.get("branch_preoutcome_context_enrichment") or {}).get("shared_anchor_time_candidate") is not None
        })
        horizon_sensitive = any(
            "VARIANT_FEATURE_CHALLENGE_CONSEQUENCE_HORIZON_SENSITIVE"
            in (row.get("decision_reasons") or [])
            for row in rows
        )
        sentence_tr = (
            f"{team_name}, {period_label} ve {_score_text(score_state)} skor bağlamında, "
            f"sağlayıcının {process_label} olarak işaretlediği sekanslarda {anchor_actions} aksiyonu çevresinde "
            "hem başarılı hem başarısız etiketli görünür dallar gösterdi. "
            f"Aynı görünür varyant ailesi {episode_spread} farklı sekans adayında görüldü. "
            + ("Gözlem 5–8–12 saniyelik sonuç penceresine duyarlı. " if horizon_sensitive else "")
            + "Bu yalnız maç-içi görünür sekans bulgusudur; taktik gerçek, neden, bağımsız tekrar veya gerçek başarı olasılığı değildir."
        )
        records.append({
            "team_identity_candidate_id": team_ref,
            "team_name": team_name,
            "period_candidate": period,
            "score_state_candidate": score_state,
            "process_family_candidates": list(process_values),
            "anchor_action_family_counts": dict(anchor_items),
            "variant_family_refs": list(family_refs),
            "source_handoff_refs": sorted(str(row.get("source_safe_finding_handoff_ref") or "") for row in rows),
            "source_handoff_count": len(rows),
            "anchor_time_candidates": times,
            "episode_spread_max_visible_count": episode_spread,
            "actor_spread_max_visible_count": actor_spread,
            "horizon_sensitive": horizon_sensitive,
            "sentence_tr": sentence_tr,
            "scope": "MATCH_LOCAL_OBSERVED_MECHANISM_FINDING_ONLY",
            "professional_emit_allowed": False,
            "statistical_generalization_allowed": False,
            "causal_inference_allowed": False,
            "tactical_truth_allowed": False,
            "record_creates_new_evidence": False,
        })
    return records


_REASON_EXPLANATION_TR = {
    "FOLLOWUP_OBSERVATION_UNRESOLVED_BURDEN": (
        "Görünür sürecin takip eden sonucu yeterince çözülemediği için daha güçlü bir futbol sonucu söylenemiyor.",
        "Takip eden görünür aksiyon ve sonuç bağlantısının daha eksiksiz çözülmesi gerekiyor.",
        "Takip eden sekansları ve sonuç bağlantısını yeniden incele.",
    ),
    "RIGHT_CENSORED_OBSERVATION_BURDEN": (
        "Gözlem penceresi sürecin devamını tam göstermediği için sonuç hakkında güçlü hüküm kurulamıyor.",
        "Sekansın devamını kapsayan daha tam bir takip gözlemi gerekiyor.",
        "Kesilmiş sekansların devamını ayrı incele.",
    ),
    "CONSEQUENCE_OBSERVATION_COVERAGE_UNRESOLVED": (
        "Sürecin sonrasındaki görünür sonuç kapsaması yeterince çözülemediği için sonuç iddiası sınırlandırılıyor.",
        "Sonuç penceresinin yeterli kapsama sahip olduğunun gösterilmesi gerekiyor.",
        "Sonuç penceresi eksik olan sekansları ayırarak incele.",
    ),
    "DEPENDENCY_INDEPENDENCE_NOT_PROVEN": (
        "Görülen örneklerin birbirinden bağımsız olduğu kanıtlanmadığı için tekrar gücü yükseltilemiyor.",
        "Örnekler arasındaki bağımlılığı ve aynı olayın tekrar temsilini ayıran kimlik bilgisi gerekiyor.",
        "Aynı gözlemin veya bağımlı örneklerin birden fazla destek gibi sayılmadığını kontrol et.",
    ),
    "VARIANT_FEATURE_CHALLENGE_DEPENDENCY_INDEPENDENCE_UNPROVEN": (
        "Görülen örneklerin birbirinden bağımsız olduğu kanıtlanmadığı için tekrar gücü yükseltilemiyor.",
        "Örnekler arasındaki bağımlılığı ayıran kimlik ve kaynak ilişkisi gerekiyor.",
        "Bağımlı örnekleri tek destek olarak ele al ve bağımsızlık kanıtını kontrol et.",
    ),
    "VARIANT_FEATURE_CHALLENGE_STATISTICAL_INDEPENDENCE_UNPROVEN": (
        "Örneklerin istatistiksel olarak bağımsız olduğu gösterilmediği için tekrar veya genelleme iddiası yapılamıyor.",
        "Bağımsız observation unit tanımı ve bağımlılık kontrolü gerekiyor.",
        "Bağımsızlık kanıtlanana kadar sonucu maç-içi betimleme düzeyinde tut.",
    ),
    "ELIGIBLE_DENOMINATOR_MEMBERSHIP_UNRESOLVED": (
        "Hangi vakaların karşılaştırmaya gerçekten dahil olduğu çözülemediği için oran güvenle yorumlanamıyor.",
        "Uygun vakaların paydasını açık ve izlenebilir biçimde belirlemek gerekiyor.",
        "Paydayı oluşturan vakaları tek tek doğrula.",
    ),
    "VARIANT_FEATURE_CHALLENGE_CONSEQUENCE_HORIZON_SENSITIVE": (
        "Gözlenen sonuç, kullanılan takip penceresine duyarlı olduğu için tek bir güçlü sonuç cümlesine indirgenemiyor.",
        "Farklı makul takip pencerelerinde sonucun nasıl değiştiğini birlikte görmek gerekiyor.",
        "5–8–12 saniyelik sonuç pencerelerini birlikte değerlendir.",
    ),
}

_SAFE_MEANING_TR = {
    "MATCH_LOCAL_OBSERVED_VISIBLE_VARIATION_ONLY": (
        "Bu maçta yalnız görünür varyasyon güvenle söylenebilir; bunun taktik gerçek, neden veya bağımsız tekrar olduğu söylenemez."
    ),
    "MATCH_LOCAL_SHARED_ANCHOR_VISIBLE_OUTCOME_VARIATION_ONLY": (
        "Bu maçta aynı görünür başlangıç bağlamından çıkan farklı sonuçlar betimlenebilir; neden veya gerçek başarı olasılığı çıkarılamaz."
    ),
}


def _unanswered_question_explanations(
    claim_payload: dict[str, Any],
    safe_payload: dict[str, Any],
    full_spine: dict[str, Any],
) -> list[dict[str, Any]]:
    admission_by_ref = {
        str(row.get("source_safe_finding_handoff_ref") or ""): row
        for row in safe_payload.get("safe_finding_admission_decisions") or []
        if isinstance(row, dict)
    }
    records: list[dict[str, Any]] = []
    for contract in claim_payload.get("analyst_output_contracts") or []:
        if not isinstance(contract, dict):
            continue
        if contract.get("professional_emit_allowed") is True:
            continue
        contract_id = str(contract.get("analyst_output_contract_id") or "").strip()
        source_ref = str(contract.get("source_safe_finding_handoff_ref") or "").strip()
        admission = admission_by_ref.get(source_ref, {})
        reasons = [
            str(value).strip()
            for value in (
                admission.get("decision_reasons")
                or contract.get("blocking_dimensions")
                or []
            )
            if str(value).strip()
        ]
        mapped = next((_REASON_EXPLANATION_TR[r] for r in reasons if r in _REASON_EXPLANATION_TR), None)
        if mapped:
            why_tr, required_tr, action_tr = mapped
        else:
            why_tr = "Neden daha güçlü bir sonuca gidilemediği mevcut kanıttan güvenle çözülemiyor."
            required_tr = "Gerekli ek gözlem mevcut kanıttan güvenle belirlenemiyor."
            action_tr = "Ek analist aksiyonu mevcut kanıttan güvenle belirlenemiyor."

        safe_key = str(
            contract.get("render_safe_meaning")
            or contract.get("safe_output_meaning")
            or ""
        ).strip()
        weaker_tr = _SAFE_MEANING_TR.get(
            safe_key,
            "Daha zayıf güvenli ifade mevcut kanıttan üretilemiyor.",
        )
        source_action = str(contract.get("render_analyst_action") or "").strip()
        if source_action:
            action_tr = source_action

        records.append({
            "question_id": contract_id or source_ref or "UNKNOWN",
            "question_tr": "Bu görünür örüntü profesyonel bir futbol bulgusu olarak söylenebilir mi?",
            "epistemic_state": str(
                contract.get("safe_finding_admission_decision")
                or admission.get("decision")
                or contract.get("evidence_sufficiency_state")
                or "UNKNOWN"
            ),
            "why_tr": why_tr,
            "source_reason_refs": reasons,
            "required_observation_tr": required_tr,
            "weaker_safe_statement_tr": weaker_tr,
            "analyst_action_tr": action_tr,
            "claim_ceiling": contract.get("claim_scope") or "INHERITS_UPSTREAM_NO_STRENGTHENING",
            "creates_new_evidence": False,
            "can_authorize_emit": False,
        })
    if records:
        return records

    hard_blocks = [
        str(value).strip()
        for value in (safe_payload.get("hard_block_hits") or [])
        if str(value).strip()
    ]
    review_hits = [
        str(value).strip()
        for value in (full_spine.get("review_hits") or [])
        if str(value).strip()
    ]
    if (
        str(full_spine.get("status") or "").upper() == "REVIEW_REQUIRED"
        or str(claim_payload.get("status") or "").upper() == "REVIEW_REQUIRED"
    ) and not hard_blocks:
        return [{
            "question_id": "report_level_zero_output",
            "question_tr": "Bu raporda neden profesyonel bulgu üretilemedi?",
            "epistemic_state": "REVIEW_REQUIRED",
            "why_tr": "Profesyonel bulgu üretilememesinin daha özel nedeni mevcut kanıttan güvenle çözülemiyor.",
            "source_reason_refs": review_hits,
            "required_observation_tr": "Gerekli ek gözlem mevcut kanıttan güvenle belirlenemiyor.",
            "weaker_safe_statement_tr": "Bu rapor mevcut haliyle yalnız inceleme yüzeyi olarak güvenle kullanılabilir.",
            "analyst_action_tr": "Daha özel neden çözülene kadar profesyonel bulgu üretme ve mevcut kanıtı yeniden incele.",
            "claim_ceiling": "NO_PROFESSIONAL_FINDING_OUTPUT",
            "creates_new_evidence": False,
            "can_authorize_emit": False,
        }]

    if safe_payload.get("status") == "FAIL_CLOSED" or hard_blocks:
        reasons = hard_blocks or review_hits
        first = reasons[0] if reasons else ""
        if first == "process_context_counterevidence_recompute_fail_closed":
            why_tr = (
                "Süreç bağlamı ile karşı-kanıt bağlantısı güvenle yeniden kurulamadığı için "
                "HPFA profesyonel bulgu üretimini kapattı."
            )
            required_tr = (
                "Süreç bağlamı, karşı-kanıt ve sonuç bağlantısının aynı uygun vakalar üzerinde "
                "yeniden çözülebilmesi gerekiyor."
            )
            action_tr = (
                "Bağlam ve karşı-kanıt bağlantısı çözülene kadar bu maçı profesyonel bulgu yerine "
                "inceleme yüzeyi olarak kullan."
            )
        else:
            why_tr = (
                "HPFA'nın güvenli bulgu zinciri mevcut kanıtta kapalı kaldığı için "
                "daha güçlü bir futbol cümlesi üretilmedi."
            )
            required_tr = (
                "Kapanan aşamadaki eksik veya uyuşmayan gözlem/bağlantının çözülmesi gerekiyor."
            )
            action_tr = (
                "İlk kapanan aşamayı ve ilgili gözlem bağlantısını yeniden incele; sonuç çözülmeden "
                "profesyonel bulgu üretme."
            )
        return [{
            "question_id": "PACKAGE_LEVEL_SAFE_FINDING_ADMISSION",
            "question_tr": "Bu maç paketi profesyonel bir futbol bulgusu üretmeye yeterli mi?",
            "epistemic_state": "FAIL_CLOSED",
            "why_tr": why_tr,
            "source_reason_refs": reasons,
            "required_observation_tr": required_tr,
            "weaker_safe_statement_tr": (
                "Bu paket mevcut haliyle yalnız inceleme ve eksikliği teşhis etme amacıyla güvenle kullanılabilir."
            ),
            "analyst_action_tr": action_tr,
            "claim_ceiling": "NO_PROFESSIONAL_FINDING_OUTPUT",
            "creates_new_evidence": False,
            "can_authorize_emit": False,
        }]

    if str(full_spine.get("status") or claim_payload.get("status") or "").upper() == "REVIEW_REQUIRED":
        return [{
            "question_id": "report_level_zero_output",
            "question_tr": "Bu maç paketinden neden profesyonel bir futbol bulgusu üretilemedi?",
            "epistemic_state": "REVIEW_REQUIRED",
            "why_tr": "Profesyonel bulgu üretilememesinin daha özel nedeni mevcut kanıttan güvenle çözülemiyor.",
            "source_reason_refs": review_hits,
            "required_observation_tr": "Gerekli ek gözlem mevcut kanıttan güvenle belirlenemiyor.",
            "weaker_safe_statement_tr": "Daha zayıf güvenli ifade mevcut kanıttan üretilemiyor.",
            "analyst_action_tr": "Eksik veya çözülemeyen gözlem yüzeylerini incele; eksikliği başarısızlık veya karşı-kanıt olarak yorumlama.",
            "claim_ceiling": "REVIEW_REQUIRED_NO_STRENGTHENING",
            "creates_new_evidence": False,
            "can_authorize_emit": False,
        }]

    return records


def build_presentation_view_model(
    full_spine: dict[str, Any],
    *,
    analyst_report_tr: str,
    analyst_report_en: str,
    mechanism_graph_payload: dict[str, Any],
    analyst_output_claim_payload: dict[str, Any] | None = None,
    safe_finding_payload: dict[str, Any] | None = None,
    identity_payload: dict[str, Any] | None = None,
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
    descriptive_findings = _match_local_descriptive_records(
        safe_finding_payload or {}, identity_payload or {}
    )
    unanswered_explanations = _unanswered_question_explanations(
        claim_payload,
        safe_finding_payload or {},
        full_spine,
    )

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
        "unanswered_question_explanations": unanswered_explanations,
        "unanswered_question_explanation_count": len(unanswered_explanations),
        "match_local_descriptive_findings": descriptive_findings,
        "match_local_descriptive_finding_count": len(descriptive_findings),
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
    descriptive_findings = [row for row in view_model.get("match_local_descriptive_findings") or [] if isinstance(row, dict)]
    unanswered_explanations = [
        row for row in view_model.get("unanswered_question_explanations") or []
        if isinstance(row, dict)
    ]

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

    explanation_html = "".join(
        "<article class=\"card\">"
        f"<h3>{html.escape(str(row.get('question_tr') or 'Soru'))}</h3>"
        f"<div class=\"meta\">Durum: {html.escape(str(row.get('epistemic_state') or 'UNKNOWN'))}</div>"
        f"<p><strong>Neden?</strong> {html.escape(str(row.get('why_tr') or ''))}</p>"
        f"<p><strong>Ne eksik?</strong> {html.escape(str(row.get('required_observation_tr') or ''))}</p>"
        f"<p><strong>Güvenli olarak ne söyleyebiliriz?</strong> {html.escape(str(row.get('weaker_safe_statement_tr') or ''))}</p>"
        f"<p><strong>Analist ne yapmalı?</strong> {html.escape(str(row.get('analyst_action_tr') or ''))}</p>"
        "<div class=\"boundary-note\">Bu açıklama yeni evidence üretmez ve profesyonel bulgu izni vermez.</div>"
        "</article>"
        for row in unanswered_explanations
    )

    descriptive_html = "".join(
        "<article class=\"card\">"
        f"<h3>{html.escape(str(row.get('team_name') or 'Takım'))}</h3>"
        f"<p>{html.escape(str(row.get('sentence_tr') or ''))}</p>"
        "<div class=\"boundary-note\">Maç-içi görünür mekanizma bulgusu · professional EMIT değildir · taktik gerçek veya nedensellik değildir.</div>"
        "</article>"
        for row in descriptive_findings
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
    if professional_claims:
        report_boundary = (
            "Analist anlatısı, yalnız yukarıda kabul edilmiş profesyonel claim'lerin sınırları içinde okunmalıdır."
            if lang == "tr"
            else "The analyst narrative must be read only within the boundaries of the professional claims admitted above."
        )
    else:
        report_boundary = (
            "Analist inceleme anlatısı: aşağıdaki metin profesyonel bulgu olarak kabul edilmemiştir; maç-okuma ve yeniden inceleme yüzeyidir."
            if lang == "tr"
            else "Analyst review narrative: the text below is not admitted as a professional finding; it is a match-reading and review surface."
        )
    escaped_report_boundary = html.escape(report_boundary)

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
<h2>HPFA neden daha fazlasını söylemiyor?</h2>
<div class="boundary-note">Bu bölüm, HPFA'nın daha güçlü bir futbol cümlesine neden geçmediğini ve hangi gözlemin eksik olduğunu açıklar. Eksik kanıt başarısızlık veya karşı-kanıt sayılmaz.</div>
<div class="grid">{explanation_html if explanation_html else '<article class="card">Bu raporda açıklanması gereken sınırlandırılmış soru yok.</article>'}</div>
</section>

<section>
<h2>Analyst report</h2>
<div class="boundary-note">{escaped_report_boundary}</div>
<div class="report">{escaped_report}</div>
</section>

<section>
<h2>Maç-içi görünür mekanizma bulguları</h2>
<div class="boundary-note">Bu bölüm yalnız maç içindeki görünür sekans varyasyonlarını özetler. Profesyonel claim, taktik gerçek, neden, bağımsız tekrar veya gerçek başarı olasılığı değildir.</div>
<div class="grid">{descriptive_html if descriptive_html else '<article class="card">Bu maçta sıkı eşikleri geçen maç-içi görünür mekanizma bulgusu yok.</article>'}</div>
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
