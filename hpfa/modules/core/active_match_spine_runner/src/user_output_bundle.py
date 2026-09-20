from __future__ import annotations

import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from analyst_mechanism_review import build_mechanism_review_lines
from mechanism_story_review_selector import build_mechanism_story_review_shortlist
from hpfa.modules.core.visible_action_sequence_candidates_lite.src.safe_sentence_render_completeness import (
    FACT_ONLY_RENDER,
    validate_safe_sentence_render,
)

ANALYST_REPORT = "HPFA_ANALYST_REPORT.txt"
ANALYST_REPORT_TR = "HPFA_ANALYST_REPORT_TR.txt"
ANALYST_REPORT_EN = "HPFA_ANALYST_REPORT_EN.txt"
BUNDLE_MANIFEST = "HPFA_ACTIVE_MATCH_BUNDLE_MANIFEST.json"
BUNDLE_ZIP = "HPFA_ACTIVE_MATCH_BUNDLE.zip"
EPISODE_FEATURE_JSON = "episode_feature_vector_lite_v1.json"
ANALYST_OUTPUT_CLAIM_JSON = "analyst_output_claim_contract_projection_v1.json"
FULL_SPINE_JSON = "active_match_full_spine_v1.json"
FULL_SPINE_TXT = "active_match_full_spine_v1.txt"
IDENTITY_JSON = "match_local_identity_candidates_lite_v1.json"
FEATURE_DELTA_JSON = "grammar_stable_variant_feature_delta_projection_v1.json"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def snapshot_output_state(output_root: str | Path) -> dict[str, dict[str, Any]]:
    """Compatibility snapshot only. Bundle admission is producer-ledger based."""
    root = Path(output_root).expanduser().resolve(strict=False)
    if not root.is_dir():
        return {}
    state: dict[str, dict[str, Any]] = {}
    for path in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        if not path.is_file() or path.name in {BUNDLE_ZIP, BUNDLE_MANIFEST}:
            continue
        try:
            state[path.name] = {"size_bytes": path.stat().st_size, "sha256": _sha256(path)}
        except OSError:
            state[path.name] = {"unreadable": True}
    return state


def _fmt_time(value: Any) -> str:
    try:
        seconds = float(value)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if seconds < 0:
        return "UNKNOWN"
    minutes = int(seconds // 60)
    secs = int(round(seconds - minutes * 60))
    if secs == 60:
        minutes += 1
        secs = 0
    return f"{minutes:02d}:{secs:02d}"


def _episode_window(card: dict[str, Any]) -> str:
    return f"{_fmt_time(card.get('start_second_candidate'))}-{_fmt_time(card.get('end_second_candidate'))}"


def _top(cards: list[dict[str, Any]], key, limit: int = 5) -> list[dict[str, Any]]:
    return sorted(cards, key=key, reverse=True)[:limit]


def _counter_sum(cards: list[dict[str, Any]], field: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for card in cards:
        values = card.get(field)
        if not isinstance(values, dict):
            continue
        for key, value in values.items():
            try:
                counter[str(key)] += int(value)
            except (TypeError, ValueError):
                continue
    return dict(sorted(counter.items()))


def _post_sequence_current_artifacts(full_spine: dict[str, Any]) -> list[str]:
    binding = full_spine.get("variant_feature_challenge_runtime_binding")
    if not isinstance(binding, dict) or binding.get("post_sequence_admission_finalized") is not True:
        return []
    return [
        str(value)
        for value in (binding.get("post_sequence_current_invocation_artifacts") or [])
        if str(value or "").strip()
    ]


def _declared_current(full_spine: dict[str, Any], filename: str) -> bool:
    values = [
        *(full_spine.get("current_invocation_artifacts") or []),
        *_post_sequence_current_artifacts(full_spine),
    ]
    return any(Path(str(value)).name == filename for value in values)


def _source_analyst_output_contracts(root: Path, full_spine: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not _declared_current(full_spine, ANALYST_OUTPUT_CLAIM_JSON):
        return {}
    payload = _load_json(root / ANALYST_OUTPUT_CLAIM_JSON)
    if str(payload.get("status") or "").upper() == "FAIL_CLOSED":
        return {}
    result: dict[str, dict[str, Any]] = {}
    for row in payload.get("analyst_output_contracts") or []:
        if not isinstance(row, dict):
            continue
        ref = str(row.get("analyst_output_contract_id") or "").strip()
        if ref:
            result[ref] = row
    return result


def _safe_sentence_render_result(
    safe: dict[str, Any],
    source_contracts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    rendered = safe.get("rendered_sentence_contract")
    if not isinstance(rendered, dict):
        rendered = {
            "source_analyst_output_contract_ref": safe.get("source_analyst_output_contract_ref"),
            "sentence_type": safe.get("sentence_type") or "INTERPRETIVE",
            "what_visible": safe.get("what_visible"),
            "safe_meaning": safe.get("safe_meaning"),
            "claim_limiter": safe.get("claim_limiter"),
            "counter_scenarios": safe.get("counter_scenarios") or [],
            "withdrawal_conditions": safe.get("withdrawal_conditions") or [],
            "analyst_action": safe.get("analyst_action"),
            "claim_scope": safe.get("claim_scope"),
            "required_qualifiers": safe.get("required_qualifiers") or [],
            "forbidden_claim_families": safe.get("forbidden_claim_families") or [],
            "evidence_refs": safe.get("evidence_refs") or [],
            "counterevidence_refs": safe.get("counterevidence_refs") or [],
            "render_creates_new_evidence": False,
            "render_authorizes_emit": False,
            "analyst_or_llm_text_is_evidence": False,
            "absence_is_counterevidence": False,
        }
    source_ref = str(rendered.get("source_analyst_output_contract_ref") or "").strip()
    source = source_contracts.get(source_ref)
    return validate_safe_sentence_render(source, rendered)


def _safe_sentences(root: Path, full_spine: dict[str, Any], limit: int = 12) -> tuple[list[str], dict[str, int]]:
    """Legacy generic C4 sentence surface, still guarded and never promoted to Safe Finding truth."""
    seen: set[str] = set()
    result: list[str] = []
    state_counts: Counter[str] = Counter()
    chains = full_spine.get("intelligence_chains")
    if not isinstance(chains, list):
        return result, {}
    source_contracts = _source_analyst_output_contracts(root, full_spine)
    for chain in chains:
        if not isinstance(chain, dict):
            continue
        safe = chain.get("safe_sentence")
        if not isinstance(safe, dict):
            continue
        validation = _safe_sentence_render_result(safe, source_contracts)
        state = str(validation.get("render_completeness_state") or "UNKNOWN")
        state_counts[state] += 1
        if validation.get("render_allowed") is True:
            text = str(safe.get("safe_sentence_candidate_tr") or "").strip()
        elif validation.get("fallback_allowed") is True and validation.get("fallback_mode") == FACT_ONLY_RENDER:
            text = str(validation.get("what_visible") or "").strip()
        else:
            text = ""
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= limit:
            break
    return result, dict(sorted(state_counts.items()))


def _source_bound_safe_sentences(
    root: Path,
    full_spine: dict[str, Any],
    limit: int = 12,
) -> tuple[list[str], dict[str, int], int]:
    """Render only current-invocation Safe Finding lineage declared by Analyst Output contracts."""
    if not _declared_current(full_spine, ANALYST_OUTPUT_CLAIM_JSON):
        return [], {}, 0
    payload = _load_json(root / ANALYST_OUTPUT_CLAIM_JSON)
    if not payload or str(payload.get("status") or "").upper() == "FAIL_CLOSED":
        return [], {}, 0

    rows = [
        row for row in (payload.get("source_bound_render_contracts") or [])
        if isinstance(row, dict)
    ]
    seen: set[str] = set()
    sentences: list[str] = []
    states: Counter[str] = Counter()
    for row in rows:
        validation = row.get("render_validation")
        if not isinstance(validation, dict):
            states["REVIEW_REQUIRED_SOURCE_CONTRACT_UNRESOLVED"] += 1
            continue
        state = str(validation.get("render_completeness_state") or "UNKNOWN")
        states[state] += 1
        allowed = validation.get("render_allowed") is True or (
            validation.get("fallback_allowed") is True
            and validation.get("fallback_mode") == FACT_ONLY_RENDER
        )
        if not allowed:
            continue
        text = str(row.get("final_human_sentence_tr") or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        sentences.append(text)
        if len(sentences) >= limit:
            break
    return sentences, dict(sorted(states.items())), len(rows)


def _feature_surface_current(full_spine: dict[str, Any]) -> bool:
    engineering = full_spine.get("engineering_evidence")
    return isinstance(engineering, dict) and engineering.get("current_context_episode_feature_lane_completed") is True


def _c4_surface_current(full_spine: dict[str, Any]) -> bool:
    engineering = full_spine.get("engineering_evidence")
    return isinstance(engineering, dict) and engineering.get("current_c4_producers_reused") is True


def _rich_surface_current(full_spine: dict[str, Any]) -> bool:
    engineering = full_spine.get("engineering_evidence")
    rich = full_spine.get("rich_multiformat_analysis_lattice")
    return (
        isinstance(engineering, dict)
        and engineering.get("rich_multiformat_lane_executed") is True
        and isinstance(rich, dict)
        and str(rich.get("status") or "").upper() != "FAIL_CLOSED"
    )


def _phase_label_counts(rich: dict[str, Any]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for item in rich.get("phase_state_candidates") or []:
        if not isinstance(item, dict):
            continue
        for label in item.get("labels") or []:
            counter[str(label)] += 1
    return dict(counter.most_common())


def _entity_summary(rich: dict[str, Any]) -> dict[str, int]:
    entity = rich.get("entity_views") or {}
    return {
        "player": len(entity.get("player_view_candidates") or []),
        "team": len(entity.get("team_view_candidates") or []),
        "goalkeeper": len(entity.get("goalkeeper_view_candidates") or []),
        "observed_metric_cells": int(entity.get("observed_metric_cell_count") or 0),
    }


def _representative_entities(rich: dict[str, Any], limit: int = 8) -> list[str]:
    entity = rich.get("entity_views") or {}
    rows = [
        *(entity.get("player_view_candidates") or []),
        *(entity.get("goalkeeper_view_candidates") or []),
        *(entity.get("team_view_candidates") or []),
    ]
    result: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = row.get("player_raw_candidate") or row.get("team_raw_candidate") or "UNRESOLVED_ENTITY"
        metrics = row.get("metric_values") or {}
        result.append(f"{name}: observed_metric_cells={len(metrics)} source_role={row.get('source_role')}")
        if len(result) >= limit:
            break
    return result


def _human_pct(value: Any, language: str = "tr") -> str:
    if not isinstance(value, (int, float)):
        return "N/A"
    number = f"{100 * float(value):.1f}"
    return f"%{number}" if language == "tr" else f"{number}%"


def _display_label(value: Any) -> str:
    import re

    text = str(value or "").strip()
    text = re.sub(r"\s*\(\d+\)\s*$", "", text).strip()
    if text and text == text.lower():
        text = " ".join(part[:1].upper() + part[1:] for part in text.split())
    return text or "UNKNOWN"


def _human_ratio(numerator: Any, denominator: Any) -> str:
    try:
        return f"{int(numerator)}/{int(denominator)}"
    except (TypeError, ValueError):
        return "N/A"


def _football_family_label(value: Any, language: str) -> str:
    key = str(value or "").strip().replace("_CANDIDATE", "")
    labels_tr = {
        "POSITIONAL_ATTACK": "yerleşik hücum",
        "TRANSITION_ATTACK": "geçiş hücumu",
        "CIRCULATION": "top dolaşımı",
        "LOSS_TRANSITION": "top kaybı sonrası geçiş",
        "RECOVERY_TRANSITION": "top kazanımı sonrası geçiş",
        "TERMINAL": "hücumun son aksiyon bölümü",
        "RESTART": "duran top / yeniden başlatma",
    }
    labels_en = {
        "POSITIONAL_ATTACK": "positional attack",
        "TRANSITION_ATTACK": "attacking transition",
        "CIRCULATION": "circulation",
        "LOSS_TRANSITION": "post-loss transition",
        "RECOVERY_TRANSITION": "post-recovery transition",
        "TERMINAL": "terminal attacking phase",
        "RESTART": "restart",
    }
    table = labels_tr if language == "tr" else labels_en
    return table.get(key, key.replace("_", " ").lower() or ("süreç" if language == "tr" else "process"))


def _human_team_labels(identity: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in identity.get("team_identity_candidates") or []:
        if not isinstance(row, dict):
            continue
        ref = str(row.get("team_identity_candidate_id") or "").strip()
        raw = (
            row.get("team_aliases_raw", [None])[0]
            if isinstance(row.get("team_aliases_raw"), list) and row.get("team_aliases_raw")
            else None
        )
        label = _display_label(raw or row.get("team_normalized_key") or ref or "UNKNOWN_TEAM")
        if ref:
            result[ref] = label
    return result


def _action_human(value: str, language: str) -> str:
    key = value.strip().upper()
    tr = {
        "PASS": "pas",
        "CARRY": "topla taşıma",
        "DUEL": "ikili mücadele",
        "RECOVERY": "top kazanımı",
        "RESTART": "oyunu yeniden başlatma",
        "DRIBBLE": "adam geçme",
        "SHOT": "şut",
        "TURNOVER": "top kaybı",
        "TACKLE": "müdahale",
        "INTERCEPTION": "pas arası",
        "CROSS": "orta",
        "FOUL": "faul",
        "CLEARANCE": "uzaklaştırma",
        "GOALKEEPER_ACTION": "kaleci aksiyonu",
    }
    en = {
        "PASS": "pass",
        "CARRY": "carry",
        "DUEL": "duel",
        "RECOVERY": "recovery",
        "RESTART": "restart",
        "DRIBBLE": "dribble",
        "SHOT": "shot",
        "TURNOVER": "turnover",
        "TACKLE": "tackle",
        "INTERCEPTION": "interception",
        "CROSS": "cross",
        "FOUL": "foul",
        "CLEARANCE": "clearance",
        "GOALKEEPER_ACTION": "goalkeeper action",
    }
    table = tr if language == "tr" else en
    return table.get(key, key.replace("_", " ").lower())


def _period_human(value: Any, language: str) -> str:
    text = str(value or "").strip()
    if language == "tr":
        return {"1": "1. devre", "2": "2. devre"}.get(text, f"dönem {text}" if text else "dönem çözümlenmedi")
    return {"1": "first half", "2": "second half"}.get(text, f"period {text}" if text else "period unresolved")


def _grammar_human(tokens: list[Any], language: str) -> str:
    parts: list[str] = []
    for raw in tokens:
        token = str(raw or "").strip()
        if not token:
            continue
        if token.startswith("LAYER[") and token.endswith("]"):
            body = token[6:-1]
            actions = [_action_human(part, language) for part in body.split("|") if part]
            if len(actions) > 1:
                joined = " + ".join(actions)
                parts.append(
                    f"{joined} (aynı zaman damgası; aralarındaki sıra bilinmiyor)"
                    if language == "tr"
                    else f"{joined} (same timestamp; internal order unresolved)"
                )
            elif actions:
                parts.append(actions[0])
        else:
            parts.append(_action_human(token, language))
    return " → ".join(parts) if parts else ("aksiyon zinciri çözümlenmedi" if language == "tr" else "action chain unresolved")


def _human_team_process_cards(rich: dict[str, Any], identity: dict[str, Any], language: str) -> list[str]:
    c03 = (rich.get("constructs") or {}).get("C03") or {}
    profiles = [row for row in (c03.get("team_process_profiles") or []) if isinstance(row, dict)]
    if not profiles:
        return []
    teams = _human_team_labels(identity)
    by_team: dict[str, dict[str, int]] = {}
    for row in profiles:
        team_id = str(row.get("team_identity_candidate_id") or "").strip()
        if not team_id:
            continue
        bucket = by_team.setdefault(team_id, {"eligible": 0, "shot": 0, "loss": 0, "recovery": 0})
        bucket["eligible"] += int(row.get("eligible_process_n") or 0)
        bucket["shot"] += int(row.get("shot_ending_process_n") or 0)
        bucket["loss"] += int(row.get("visible_loss_process_n") or 0)
        bucket["recovery"] += int(row.get("visible_recovery_process_n") or 0)
    cards: list[str] = []
    for team_id, values in sorted(by_team.items(), key=lambda item: teams.get(item[0], item[0])):
        name = teams.get(team_id, team_id)
        if language == "tr":
            football = (
                f"{name}: Sistem bu maçta {values['eligible']} görünür oyun sürecini takım bağlamına bağlayabildi. "
                f"Bunların {values['loss']} tanesinde top kaybı, {values['recovery']} tanesinde top kazanımı ve "
                f"{values['shot']} tanesinde şutla bağlantılı bir son bölüm görüldü."
            )
            evidence = (
                "Kanıt notu: Aynı süreç birden fazla görünür sonucu taşıyabilir; bu sayılar hücum/possession sayısı "
                "veya başarı oranı değildir. Takım kalitesi, taktik üstünlük ve nedensellik sonucu çıkarılamaz."
            )
        else:
            football = (
                f"{name}: The system linked {values['eligible']} visible match processes to this team. "
                f"A visible loss occurred in {values['loss']}, a recovery in {values['recovery']}, and "
                f"a shot-linked terminal state in {values['shot']}."
            )
            evidence = (
                "Evidence note: One process may carry more than one visible consequence. These are not possession counts "
                "or success rates, and they do not establish team quality, tactical superiority, or causality."
            )
        cards.extend([football, evidence])
    return cards


def _human_mechanism_cards(root: Path, full_spine: dict[str, Any], identity: dict[str, Any], language: str) -> list[str]:
    if not _declared_current(full_spine, FEATURE_DELTA_JSON):
        return []
    payload = _load_json(root / FEATURE_DELTA_JSON)
    if not payload or str(payload.get("status") or "").upper() == "FAIL_CLOSED":
        return []
    analyst_output = (
        _load_json(root / ANALYST_OUTPUT_CLAIM_JSON)
        if _declared_current(full_spine, ANALYST_OUTPUT_CLAIM_JSON)
        else {}
    )
    shortlist = build_mechanism_story_review_shortlist(
        payload,
        analyst_output_claim_payload=analyst_output or None,
        limit=5,
    )
    teams = _human_team_labels(identity)
    cards: list[str] = []
    for idx, row in enumerate(shortlist.get("shortlist") or [], start=1):
        if not isinstance(row, dict):
            continue
        team_ids = [str(v) for v in (row.get("team_identity_candidate_ids") or []) if str(v)]
        team = ", ".join(teams.get(ref, ref) for ref in team_ids) or ("Takım çözümlenmedi" if language == "tr" else "Team unresolved")
        periods = ", ".join(_period_human(v, language) for v in (row.get("period_candidates") or [])) or _period_human(None, language)
        grammar = _grammar_human(list(row.get("grammar_signature_tokens") or []), language)
        resolved = int(row.get("resolved_variant_count") or 0)
        success = int(row.get("success_resolved_variant_count") or 0)
        failure = int(row.get("failure_resolved_variant_count") or 0)
        spread = int(row.get("visible_episode_spread_count") or 0)
        clusters = int(row.get("occurrence_disjoint_support_cluster_count") or 0)
        if language == "tr":
            football = (
                f"İnceleme noktası {idx}: {team}, {periods}. {grammar} bağlantısı maçın {spread} farklı bölümünde tekrar görülüyor. "
                "Bu bağlantının karşılaştırılabilir varyantları hem olumlu hem olumsuz görünür sonuçlara gidiyor. "
                "Analist için asıl soru, aynı başlangıçtan sonra hangi aksiyon veya bağlam değişiminin sonuçları ayırdığı."
            )
            evidence = (
                f"Kanıt notu: karşılaştırma yüzeyinde {resolved} çözümlenmiş varyant kaydı var; "
                f"{success} olumlu ve {failure} olumsuz görünür sonuca bağlı. "
                f"Bu kayıtlar {clusters} birbirinden ayrı görünür aksiyon kümesine dayanıyor; bağımsız kanıt sayısı değildir. "
                "Neden, antrenör planı ve başarı olasılığı çıkarılamaz."
            )
        else:
            football = (
                f"Review point {idx}: {team}, {periods}. The {grammar} connection recurs across {spread} distinct match segments. "
                "Comparable variants of the same visible start lead to both positive and negative visible outcomes. "
                "The analyst question is which subsequent action or context change separates those outcomes."
            )
            evidence = (
                f"Evidence note: the comparison surface contains {resolved} resolved variant records; "
                f"{success} are linked to positive and {failure} to negative visible outcomes. "
                f"They rest on {clusters} distinct visible action clusters, not {clusters} independent pieces of evidence. "
                "They do not establish cause, coaching intention, or success probability."
            )
        cards.extend([football, evidence])
    return cards


def _human_c02_cards(rich: dict[str, Any], language: str) -> list[str]:
    c02 = (rich.get("constructs") or {}).get("C02") or {}
    rows = [
        ("PLAYER", c02.get("representative_actor_argument")),
        ("DYAD", c02.get("representative_dyad_argument")),
    ]
    cards: list[str] = []
    for entity_type, candidate in rows:
        if not isinstance(candidate, dict):
            continue
        names = " + ".join(_display_label(value) for value in (candidate.get("actor_labels") or [])) or "UNKNOWN"
        family = _football_family_label(candidate.get("process_family_candidate"), language)
        eligible_n = int(candidate.get("eligible_n") or candidate.get("support_n") or 0)
        positive_k = int(candidate.get("visible_target_annotation_k") or candidate.get("shot_ending_n") or 0)
        unresolved_u = int(candidate.get("target_outcome_unresolved_u") or candidate.get("not_target_annotated_n") or 0)
        rate = candidate.get("observed_visible_target_annotation_frequency")
        baseline = candidate.get("match_local_baseline_shot_frequency")
        lift = candidate.get("descriptive_lift")
        eligible_spread = int(candidate.get("eligible_episode_spread") or 0)
        positive_spread = int(candidate.get("positive_episode_spread") or 0)
        pool_n = int(candidate.get("selection_candidate_pool_n") or 0)
        rank = int(candidate.get("selection_rank") or 0)
        if language == "tr":
            label = "Oyuncu" if entity_type == "PLAYER" else "İkili"
            football = (
                f"{label}: {names}. {names}, bu maçta {family} olarak sınıflanan hücumların "
                f"{eligible_n} tanesinde sürecin içinde görünüyor. Bu hücumların {positive_k} tanesinde "
                "şutla bağlantılı görünür bir son aksiyon kaydı var."
            )
            if isinstance(baseline, (int, float)) and isinstance(rate, (int, float)):
                involvement_phrase = (
                    f"{names} bu hücumlarda yer aldığında"
                    if entity_type == "PLAYER"
                    else f"{names} birlikte yer aldığında"
                )
                football += (
                    f" Aynı hücum tipinin maç içindeki genel görünür oranı {_human_pct(baseline, language)} iken "
                    f"{involvement_phrase} oran {_human_pct(rate, language)}."
                )
            football += (
                " Bu fark, analistin bu oyuncu/ikiliyi söz konusu hücumlarda özellikle incelemesi için bir işarettir; "
                "şutun sebebinin bu oyuncu/ikili olduğunu göstermez."
            )
            evidence = (
                f"Kanıt notu: {eligible_n} örneğin {positive_k} tanesinde görünür şut bağlantısı var; "
                f"{unresolved_u} örnekte hedef sonuç çözümlenmiş değil. Oyuncu/ikili bu hücum tipinde "
                f"{eligible_spread} farklı maç bölümünde görülüyor; şut bağlantısı {positive_spread} farklı bölümde görülüyor"
            )
            if isinstance(lift, (int, float)):
                evidence += f"; maç içi betimleyici oran karşılaştırması={float(lift):.2f}x"
            evidence += ". Bu bir katkı skoru, nedensel etki, oyuncu kalitesi veya gelecek tahmini değildir."
        else:
            label = "Player" if entity_type == "PLAYER" else "Pair"
            football = (
                f"{label}: {names}. {names} appeared in {eligible_n} instances of this match's {family} process family. "
                f"{positive_k} of those instances were linked to a visible shot-ending annotation."
            )
            if isinstance(baseline, (int, float)) and isinstance(rate, (int, float)):
                football += (
                    f" The match-local visible rate for the same process family was {_human_pct(baseline, language)}, "
                    f"compared with {_human_pct(rate, language)} when {names} was involved."
                )
            football += (
                " This is a useful analyst-review signal, but it does not show that the player or pair caused the shot outcome."
            )
            evidence = (
                f"Evidence note: {positive_k} of {eligible_n} examples carry a visible shot link; "
                f"{unresolved_u} target outcomes remain unresolved. The player/pair appears across "
                f"{eligible_spread} distinct match segments, with a shot link in {positive_spread} of them"
            )
            if isinstance(lift, (int, float)):
                evidence += f"; match-local descriptive ratio={float(lift):.2f}x"
            evidence += ". This is not a contribution score, causal effect, player-quality estimate, or forecast."
        cards.extend([football, evidence])
    return cards


def build_human_analyst_report_tr(output_root: str | Path, full_spine: dict[str, Any]) -> str:
    root = Path(output_root)
    rich_current = _rich_surface_current(full_spine)
    rich = full_spine.get("rich_multiformat_analysis_lattice") if rich_current else {}
    rich = rich if isinstance(rich, dict) else {}
    identity = _load_json(root / IDENTITY_JSON) if _declared_current(full_spine, IDENTITY_JSON) else {}
    c02_cards = _human_c02_cards(rich, "tr") if rich_current else []
    team_cards = _human_team_process_cards(rich, identity, "tr") if rich_current else []
    mechanism_cards = _human_mechanism_cards(root, full_spine, identity, "tr")
    lines = [
        "HPFA MAÇ ANALİZİ — TÜRKÇE ANALİST RAPORU",
        "========================================",
        "",
        "Bu rapor futbol diliyle yazılmış analist yüzeyidir. Teknik kanıt ayrıntıları ayrı 'Kanıt notu' satırlarında tutulur.",
        "",
        "[1] MAÇIN GÖRÜNÜR SÜREÇ PROFİLİ",
    ]
    if team_cards:
        lines.extend(f"- {line}" for line in team_cards)
    else:
        lines.append("- Bu maçta takım süreç profili güvenli biçimde üretilemedi.")
    lines.extend(["", "[2] OYUNCU / İKİLİ × HÜCUM SONUCU"])
    if c02_cards:
        lines.extend(f"- {line}" for line in c02_cards)
    else:
        lines.append("- Bu maçta bu başlık için güvenli biçimde raporlanabilir current-run aday yok.")
    lines.extend(["", "[3] AYNI HÜCUM BAŞLANGICININ AYRIŞAN SONUÇLARI"])
    if mechanism_cards:
        lines.extend(f"- {line}" for line in mechanism_cards)
    else:
        lines.append("- Bu maçta güvenli biçimde kısa listeye alınmış mekanizma adayı yok.")
    lines.extend([
        "",
        "[4] NE SÖYLEYEBİLİRİZ / NE SÖYLEYEMEYİZ?",
        "- Görünür birlikte-oluş, oyuncu katkısı veya nedensel etki değildir.",
        "- Şut kaydı görülmeyen süreç otomatik olarak başarısız hücum sayılmaz.",
        "- Sıralama, yalnız analistin hangi örneklere önce bakacağını belirleyen maç içi dikkat sırasıdır.",
        "- Aynı aksiyon zincirinin tekrarı, tek başına taktik plan veya antrenör niyeti kanıtı değildir.",
        "- Tracking/video olmadan baskı geometrisi, takım şekli, kompaktlık, gerçek hız veya oyuncu niyeti iddiası üretilmez.",
        "",
    ])
    return "\n".join(lines)


def build_human_analyst_report_en(output_root: str | Path, full_spine: dict[str, Any]) -> str:
    root = Path(output_root)
    rich_current = _rich_surface_current(full_spine)
    rich = full_spine.get("rich_multiformat_analysis_lattice") if rich_current else {}
    rich = rich if isinstance(rich, dict) else {}
    identity = _load_json(root / IDENTITY_JSON) if _declared_current(full_spine, IDENTITY_JSON) else {}
    c02_cards = _human_c02_cards(rich, "en") if rich_current else []
    team_cards = _human_team_process_cards(rich, identity, "en") if rich_current else []
    mechanism_cards = _human_mechanism_cards(root, full_spine, identity, "en")
    lines = [
        "HPFA MATCH ANALYSIS — ENGLISH ANALYST REPORT",
        "===========================================",
        "",
        "This is the analyst-facing football report. Technical evidence limits are kept in separate 'Evidence note' lines.",
        "",
        "[1] VISIBLE MATCH PROCESS PROFILE",
    ]
    if team_cards:
        lines.extend(f"- {line}" for line in team_cards)
    else:
        lines.append("- No safe current-run team process profile is available.")
    lines.extend(["", "[2] PLAYER / PAIR × ATTACK OUTCOME"])
    if c02_cards:
        lines.extend(f"- {line}" for line in c02_cards)
    else:
        lines.append("- No current-run candidate can be reported safely under this heading.")
    lines.extend(["", "[3] DIVERGING OUTCOMES FROM THE SAME ATTACKING START"])
    if mechanism_cards:
        lines.extend(f"- {line}" for line in mechanism_cards)
    else:
        lines.append("- No mechanism candidate was safely shortlisted in this run.")
    lines.extend([
        "",
        "[4] CLAIM BOUNDARY",
        "- Visible co-occurrence is not player contribution or causal effect.",
        "- A process without a visible shot annotation is not automatically a failed attack.",
        "- Ranking is a match-local analyst-attention order, not a stable player ranking.",
        "- Repeated visible action grammar is not, by itself, proof of a tactical plan or coaching intention.",
        "- Without tracking/video, this report does not claim true pressure geometry, team shape, compactness, true speed, or player intent.",
        "",
    ])
    return "\n".join(lines)

def build_analyst_report(output_root: str | Path, full_spine: dict[str, Any]) -> str:
    root = Path(output_root)
    feature_current = _feature_surface_current(full_spine)
    c4_current = _c4_surface_current(full_spine)
    rich_current = _rich_surface_current(full_spine)
    features = _load_json(root / EPISODE_FEATURE_JSON) if feature_current else {}
    rich = full_spine.get("rich_multiformat_analysis_lattice") if rich_current else {}
    rich = rich if isinstance(rich, dict) else {}
    identity = _load_json(root / IDENTITY_JSON) if _declared_current(full_spine, IDENTITY_JSON) else {}
    team_labels = {
        str(row.get("team_identity_candidate_id") or ""): str(
            row.get("team_normalized_key") or row.get("team_aliases_raw", [None])[0] or row.get("team_identity_candidate_id") or "UNKNOWN_TEAM"
        )
        for row in (identity.get("team_identity_candidates") or [])
        if isinstance(row, dict) and str(row.get("team_identity_candidate_id") or "")
    }
    cards = features.get("episode_feature_vectors")
    cards = [item for item in cards if isinstance(item, dict)] if isinstance(cards, list) else []

    family_totals = features.get("eligible_action_family_candidate_counts")
    family_totals = family_totals if isinstance(family_totals, dict) else _counter_sum(cards, "action_family_counts")
    team_totals = _counter_sum(cards, "eligible_action_count_by_team_candidate")
    zone_totals = _counter_sum(cards, "eligible_action_zone_counts")
    channel_totals = _counter_sum(cards, "eligible_action_channel_counts")
    known_team_total = sum(team_totals.values())
    unknown_team_total = sum(int(card.get("unknown_team_eligible_action_count") or 0) for card in cards)

    top_shot = _top(cards, lambda c: (int(c.get("shot_candidate_count") or 0), int(c.get("eligible_action_candidate_count") or 0)))
    top_transition = _top(cards, lambda c: (int(c.get("turnover_candidate_count") or 0) + int(c.get("recovery_candidate_count") or 0), int(c.get("eligible_action_candidate_count") or 0)))
    top_volume = _top(cards, lambda c: int(c.get("eligible_action_candidate_count") or 0))

    visible_total = features.get("total_eligible_action_candidate_count") if feature_current else "UNAVAILABLE_CURRENT_INVOCATION"
    family_surface = json.dumps(family_totals, ensure_ascii=False, sort_keys=True) if feature_current else "UNAVAILABLE_CURRENT_INVOCATION"
    team_surface = json.dumps(team_totals, ensure_ascii=False, sort_keys=True) if feature_current else "UNAVAILABLE_CURRENT_INVOCATION"
    zone_surface = json.dumps(zone_totals, ensure_ascii=False, sort_keys=True) if feature_current else "UNAVAILABLE_CURRENT_INVOCATION"
    channel_surface = json.dumps(channel_totals, ensure_ascii=False, sort_keys=True) if feature_current else "UNAVAILABLE_CURRENT_INVOCATION"

    lines = [
        "HPFA ACTIVE_MATCH ANALIST RAPORU",
        "==============================",
        f"runtime_status={full_spine.get('status')}",
        f"decision={full_spine.get('decision')}",
        f"episode_candidate_count={full_spine.get('episode_candidate_count')}",
        f"episode_feature_vector_count={full_spine.get('episode_feature_vector_count')}",
        f"temporal_episode_signature_count={full_spine.get('temporal_episode_signature_count')}",
        f"intelligence_chain_count={full_spine.get('intelligence_chain_count')}",
        f"hard_block_hits={full_spine.get('hard_block_hits') or []}",
        f"feature_surface_current_invocation={str(feature_current).lower()}",
        f"rich_multiformat_surface_current_invocation={str(rich_current).lower()}",
        f"c4_surface_current_invocation={str(c4_current).lower()}",
        "",
        "[1] WHAT_VISIBLE — GORUNUR MAC YUZEYI",
        f"eligible_action_candidate_total={visible_total}",
        f"action_family_candidates={family_surface}",
        f"known_team_attributed_candidates={known_team_total if feature_current else 'UNAVAILABLE_CURRENT_INVOCATION'}",
        f"unknown_team_attribution_candidates={unknown_team_total if feature_current else 'UNAVAILABLE_CURRENT_INVOCATION'}",
        f"team_candidate_distribution={team_surface}",
        f"zone_candidate_distribution={zone_surface}",
        f"channel_candidate_distribution={channel_surface}",
        "",
        "[2] WHERE_WHEN — EN YUKSEK GORUNUR EPISODE YUZEYLERI",
    ]
    if not feature_current:
        lines.append("- Current invocation Episode Feature producer'u tamamlanmadi; onceki run artifact'i kullanilmadi.")
    else:
        lines.append("shot_candidate_yogunlugu:")
        for card in top_shot:
            lines.append(
                f"- {_episode_window(card)} shots={int(card.get('shot_candidate_count') or 0)} "
                f"actions={int(card.get('eligible_action_candidate_count') or 0)} "
                f"turnovers={int(card.get('turnover_candidate_count') or 0)} recoveries={int(card.get('recovery_candidate_count') or 0)}"
            )
        lines.append("turnover_recovery_candidate_yogunlugu:")
        for card in top_transition:
            lines.append(
                f"- {_episode_window(card)} turnover+recovery="
                f"{int(card.get('turnover_candidate_count') or 0) + int(card.get('recovery_candidate_count') or 0)} "
                f"actions={int(card.get('eligible_action_candidate_count') or 0)} shots={int(card.get('shot_candidate_count') or 0)}"
            )
        lines.append("visible_action_candidate_hacmi:")
        for card in top_volume:
            lines.append(
                f"- {_episode_window(card)} actions={int(card.get('eligible_action_candidate_count') or 0)} "
                f"shots={int(card.get('shot_candidate_count') or 0)} turnovers={int(card.get('turnover_candidate_count') or 0)} "
                f"recoveries={int(card.get('recovery_candidate_count') or 0)}"
            )

    lines.extend(["", "[3] MULTIFORMAT FUSION / XLSX AGGREGATE YUZEYI"])
    if not rich_current:
        lines.append("- Current invocation rich multiformat lane mevcut degil; onceki XLSX/fusion artifact'i kullanilmadi.")
    else:
        entity_summary = _entity_summary(rich)
        lines.extend([
            f"multiformat_inventory_status={rich.get('inventory_status')}",
            f"xlsx_surface_audit_status={rich.get('xlsx_audit_status')}",
            f"xlsx_entity_metric_projection_status={rich.get('xlsx_projection_status')}",
            f"xlsx_projected_row_count={rich.get('xlsx_projected_row_count')}",
            f"observed_xlsx_metric_cell_count={entity_summary['observed_metric_cells']}",
            f"player_view_candidate_count={entity_summary['player']}",
            f"team_view_candidate_count={entity_summary['team']}",
            f"goalkeeper_view_candidate_count={entity_summary['goalkeeper']}",
            "format_fusion_is_independent_evidence_vote=false",
            "representative_entity_surfaces:",
        ])
        lines.extend(f"- {item}" for item in _representative_entities(rich))

    lines.extend(["", "[4] METRIC / CONSTRUCT / OYUN-KATMANI"])
    if rich_current:
        c01 = (rich.get("constructs") or {}).get("C01") or {}
        c02 = (rich.get("constructs") or {}).get("C02") or {}
        c03 = (rich.get("constructs") or {}).get("C03") or {}
        c04 = (rich.get("constructs") or {}).get("C04") or {}
        lines.extend([
            f"primitive_metric_count={len(rich.get('primitive_metrics') or [])}",
            f"phase_state_candidate_count={len(rich.get('phase_state_candidates') or [])}",
            f"phase_state_candidate_distribution={json.dumps(_phase_label_counts(rich), ensure_ascii=False, sort_keys=True)}",
            f"micro_layer_bound={bool((rich.get('analysis_lattice') or {}).get('MICRO'))}",
            f"mezzo_layer_bound={bool((rich.get('analysis_lattice') or {}).get('MEZZO'))}",
            f"macro_layer_bound={bool((rich.get('analysis_lattice') or {}).get('MACRO'))}",
            f"C01_construct_status={c01.get('status')}",
            f"C01_progression_aggregate_ref_count={c01.get('progression_aggregate_ref_count')}",
            f"C01_terminal_aggregate_ref_count={c01.get('terminal_aggregate_ref_count')}",
            f"C01_visible_shot_candidate_count={c01.get('visible_shot_candidate_count')}",
            f"C01_review_reason={c01.get('review_reason')}",
            "phase_state_candidates_are_phase_truth=false",
            f"C02_construct_status={c02.get('status')}",
            f"C02_argument_candidate_count={c02.get('argument_candidate_count')}",
            f"C02_xlsx_actor_binding_count={c02.get('xlsx_actor_binding_count')}",
            f"C03_construct_status={c03.get('status')}",
            f"C03_process_development_signature_count={c03.get('signature_count')}",
            f"C04_construct_status={c04.get('status')}",
            f"C04_closed_composition_profile_count={c04.get('closed_composition_profile_count')}",
            f"C04_model_context_residual_profile_count={c04.get('model_context_residual_profile_count')}",
            f"C04_family_closure_audit={json.dumps(c04.get('family_closure_audit') or {}, ensure_ascii=False, sort_keys=True)}",
            "construct_candidate_is_metric_truth=false",
        ])
        for label, candidate in (
            ("oyuncu", c02.get("representative_actor_argument")),
            ("ikili", c02.get("representative_dyad_argument")),
        ):
            if not isinstance(candidate, dict):
                continue
            names = " + ".join(str(value) for value in (candidate.get("actor_labels") or []))
            support_n = int(candidate.get("support_n") or 0)
            shot_n = int(candidate.get("shot_ending_n") or 0)
            eligible_n = int(candidate.get("eligible_process_n") or 0)
            baseline_shot_n = int(candidate.get("baseline_shot_ending_n") or 0)
            rate = candidate.get("conditional_shot_frequency")
            baseline = candidate.get("match_local_baseline_shot_frequency")
            lift = candidate.get("match_local_lift")
            family = str(candidate.get("process_family_candidate") or "process").replace("_", " ")
            rate_text = f"%{100 * float(rate):.1f}" if isinstance(rate, (int, float)) else "N/A"
            base_text = f"%{100 * float(baseline):.1f}" if isinstance(baseline, (int, float)) else "N/A"
            lift_text = f"{float(lift):.2f}x" if isinstance(lift, (int, float)) else "N/A"
            lines.append(
                f"- POZITIF FUTBOL ARGUMANI ADAYI ({label}): {family} ailesinde genel olarak "
                f"{baseline_shot_n}/{eligible_n} süreçte görünür shot-present anotasyonu vardı ({base_text}). "
                f"{names} bulunan {support_n} eligible süreçte {shot_n} görünür shot-present anotasyonu görüldü "
                f"({rate_text}; descriptive maç-içi lift={lift_text}). "
                f"Hedef anotasyonu görülmeyen birlikte-görülme={int(candidate.get('not_target_annotated_n') or 0)} "
                "(resolved non-shot değildir); "
                f"coverage={((candidate.get('observation_capability_coverage_profile') or {}).get('coverage_state') or 'UNRESOLVED')}; "
                f"negative_claim={((candidate.get('observation_capability_coverage_profile') or {}).get('negative_claim_admission_state') or 'UNRESOLVED')}; "
                f"XLSX oyuncu bağlamı eşleşen kişi={int(candidate.get('xlsx_enriched_actor_count') or 0)}. "
                "Bu, admitted process/occurrence incelemesine öncelik veren maç-içi görünür association adayidir; resolved shot outcome rate, causal credit veya stable signal değildir."
            )
            review = candidate.get("epistemic_review_contract") or {}
            if isinstance(review, dict) and review.get("analyst_action"):
                lines.append(
                    f"  inceleme_yonergesi ({label}): {review.get('analyst_action')} "
                    f"withdrawal_conditions={review.get('withdrawal_conditions') or []}; "
                    "review_contract_creates_new_evidence=false; review_contract_can_authorize_emit=false."
                )
        c03_team_profiles = [row for row in (c03.get("team_process_profiles") or []) if isinstance(row, dict)]
        if c03_team_profiles:
            by_team: dict[str, dict[str, int]] = {}
            for profile in c03_team_profiles:
                team_id = str(profile.get("team_identity_candidate_id") or "")
                if not team_id:
                    continue
                bucket = by_team.setdefault(team_id, {"eligible": 0, "shot": 0, "loss": 0, "recovery": 0})
                bucket["eligible"] += int(profile.get("eligible_process_n") or 0)
                bucket["shot"] += int(profile.get("shot_ending_process_n") or 0)
                bucket["loss"] += int(profile.get("visible_loss_process_n") or 0)
                bucket["recovery"] += int(profile.get("visible_recovery_process_n") or 0)
            for team_id, values in sorted(by_team.items(), key=lambda item: team_labels.get(item[0], item[0])):
                team_name = team_labels.get(team_id, team_id)
                lines.append(
                    f"- TAKIM SUREC/CONSEQUENCE PROFILI: {team_name}; admitted process={values['eligible']}; "
                    f"loss-visible={values['loss']}; recovery-visible={values['recovery']}; "
                    f"shot-terminal={values['shot']}. "
                    "Bunlar possession sayisi veya basari orani degildir; ayni process birden fazla consequence tasiyabilir. "
                    "Profil match-local descriptive candidate'tir; takim kalitesi, taktik ustunluk, opponent-response truth veya causality degildir."
                )
            for profile in sorted(
                c03_team_profiles,
                key=lambda row: (
                    team_labels.get(str(row.get("team_identity_candidate_id") or ""), str(row.get("team_identity_candidate_id") or "")),
                    str(row.get("process_family_candidate") or ""),
                ),
            ):
                team_id = str(profile.get("team_identity_candidate_id") or "")
                team_name = team_labels.get(team_id, team_id or "UNKNOWN_TEAM")
                family_name = str(profile.get("process_family_candidate") or "UNRESOLVED_PROCESS").replace("_CANDIDATE", "").replace("_", " ").lower()
                eligible = int(profile.get("eligible_process_n") or 0)
                shot = int(profile.get("shot_ending_process_n") or 0)
                loss = int(profile.get("visible_loss_process_n") or 0)
                recovery = int(profile.get("visible_recovery_process_n") or 0)
                lines.append(
                    f"  - SUREC AILE PROFILI: {team_name}; {family_name}; denominator={eligible} admitted process; "
                    f"loss-visible={loss}/{eligible}; recovery-visible={recovery}/{eligible}; "
                    f"shot-terminal={shot}/{eligible}; actor-spread-mean={float(profile.get('mean_actor_spread_candidate') or 0):.2f}; "
                    f"temporal-layer-mean={float(profile.get('mean_temporal_layer_n') or 0):.2f}. "
                    "Bu family profile ayni family icindeki gorunur consequence dagilimini ozetler; possession, efficacy, tactical superiority, "
                    "opponent-response truth, independence veya causality kaniti degildir."
                )
        c03_rows = [row for row in (c03.get("signatures") or []) if isinstance(row, dict)]
        if c03_rows:
            representative = max(
                c03_rows,
                key=lambda row: (
                    int(row.get("visible_occurrence_n") or 0),
                    int(row.get("temporal_layer_n") or 0),
                ),
            )
            family = str(representative.get("process_family_candidate") or "process").replace("_", " ")
            duration = representative.get("process_interval_duration_candidate")
            duration_text = f"{float(duration):.1f}s" if isinstance(duration, (int, float)) else "N/A"
            anchor_sum = representative.get("annotation_anchor_segment_distance_sum_provider_units_candidate")
            anchor_text = f"{float(anchor_sum):.2f} provider-unit" if isinstance(anchor_sum, (int, float)) else "N/A"
            lines.append(
                f"- SUREC GELISIM IMZASI ADAYI: {family}; provider process araligi={duration_text}; "
                f"gorunur occurrence={int(representative.get('visible_occurrence_n') or 0)}; "
                f"zamansal katman={int(representative.get('temporal_layer_n') or 0)}; "
                f"annotation-anchor segment={int(representative.get('annotation_anchor_segment_n') or 0)}; "
                f"anchor kapsami={representative.get('annotation_anchor_path_coverage_state')}; "
                f"anchor-mesafe-toplami={anchor_text}; "
                f"actor-spread={int(representative.get('unique_actor_candidate_n') or 0)}; "
                f"start-zone={representative.get('process_start_zone_candidates') or []}; "
                f"end-zone={representative.get('process_end_zone_candidates') or []}; "
                f"action-mix={representative.get('action_family_layer_counts') or {}}; "
                f"pass-carry-mix={representative.get('pass_carry_layer_mix') or {}}; "
                f"loss-visible={bool(representative.get('visible_loss_transition_candidate_present'))}; "
                f"recovery-visible={bool(representative.get('visible_recovery_transition_candidate_present'))}; "
                f"terminal-visible={bool(representative.get('visible_terminal_annotation_candidate_present'))}. "
                "Ayni timestamp icinde total order kurulmaz; annotation-anchor yolu fiziksel top/oyuncu "
                "trajektorisi degildir; bu morfoloji temporal-layer ozetidir ve fiziksel mesafe, hiz, possession truth "
                "veya taktik plan truth degildir."
            )
        closed_compositions = [
            row for row in (c04.get("composition_profiles") or [])
            if isinstance(row, dict) and row.get("closure_state") == "IDENTITY_OBSERVED_WITHIN_TOLERANCE"
        ]
        for family_id in (
            "FINAL_THIRD_ENTRY_MODE_COMPOSITION",
            "BALL_LOSS_MODE_COMPOSITION",
            "RECEPTION_DEPTH_COMPOSITION",
        ):
            family_rows = [row for row in closed_compositions if row.get("family_id") == family_id]
            if not family_rows:
                continue
            representative = max(family_rows, key=lambda row: float(row.get("total_value") or 0))
            components = representative.get("component_values") or {}
            shares = representative.get("composition_shares") or {}
            lines.append(
                f"- XLSX BILESIM ADAYI: {family_id}; entity={representative.get('entity_candidate')}; "
                f"toplam={representative.get('total_value')}; components={components}; shares={shares}. "
                "Toplam hacim ayri eksendir; bilesim yeni bagimsiz kanit veya oyuncu-kalite skoru degildir."
            )
    else:
        lines.append("- Rich metric/construct/layer surface unavailable for this invocation.")

    source_safe, source_safe_states, source_safe_count = _source_bound_safe_sentences(root, full_spine)
    generic_safe, generic_safe_states = _safe_sentences(root, full_spine) if c4_current else ([], {})
    lines.extend(["", "[5] SAFE_ARGUMENT_CANDIDATES / SAFE FINDING → ANALYST OUTPUT — SOURCE-BOUND RENDER"])
    lines.append(f"source_bound_render_contract_count={source_safe_count}")
    lines.append(f"source_bound_render_state_counts={json.dumps(source_safe_states, ensure_ascii=False, sort_keys=True)}")
    lines.append(f"generic_c4_render_state_counts={json.dumps(generic_safe_states, ensure_ascii=False, sort_keys=True)}")
    lines.append("render_creates_new_evidence=false")
    lines.append("render_can_authorize_emit=false")
    lines.append("render_can_strengthen_claim_ceiling=false")
    lines.append("analyst_or_llm_text_is_evidence=false")
    if source_safe:
        lines.extend(f"- {text}" for text in source_safe)
    elif source_safe_count:
        lines.append("- Source-bound Analyst Output contractlari mevcut fakat bu run'da render edilebilir cümle bulunmadi; eksik veya bloklu yorum yayınlanmadi.")
    elif generic_safe:
        lines.append("- Source-bound Safe Finding render surface mevcut degil; generic C4 cümleleri yalnız legacy/review surface olarak tutulur ve Safe Finding yerine gecmez.")
        lines.extend(f"- legacy_review_only: {text}" for text in generic_safe)
    elif c4_current:
        lines.append("- Source-bound render mevcut degil; generic C4 interpretive render da güvenli biçimde bloklandi.")
    else:
        lines.append("- Current invocation C4 producer zinciri tamamlanmadi; onceki run argumani kullanilmadi.")

    lines.extend(["", "[6] ANALYST REVIEW — GORUNUR SUREC MEKANIZMASI ADAYLARI"])
    lines.extend(build_mechanism_review_lines(root, full_spine))

    lines.extend([
        "",
        "[7] COUNTEREVIDENCE / UNCERTAINTY",
        f"review_hits={full_spine.get('review_hits') or []}",
        f"review_debt_feature_vector_count={features.get('review_debt_feature_vector_count') if feature_current else 'UNAVAILABLE_CURRENT_INVOCATION'}",
        f"total_unresolved_semantics_context_count={features.get('total_unresolved_semantics_context_count') if feature_current else 'UNAVAILABLE_CURRENT_INVOCATION'}",
        f"rich_lane_review_hits={(rich.get('review_hits') or []) if rich_current else 'UNAVAILABLE_CURRENT_INVOCATION'}",
        "absence_of_evidence_is_counterevidence=false",
        "",
        "[8] SAFE_MEANING",
    ])
    if feature_current and rich_current and c4_current:
        lines.append("Bu rapor current invocation icinde uretilen ZFGV observation ailesindeki occurrence/episode aday yuzeylerini, XLSX aggregate/tabular yuzeyini, primitive/construct adaylarini ve mevcut C4 defeasible argument yuzeyini ayni evidence zincirinde birlestirir.")
    elif feature_current and rich_current:
        lines.append("Current invocation occurrence/episode ve multiformat aggregate yuzeyi mevcut; C4 tamamlanmadigi icin argument sonucu current evidence olarak yayinlanmadi.")
    elif feature_current:
        lines.append("Current invocation Episode Feature yuzeyi mevcut; multiformat/construct veya C4 yuzeyi tamamlanmadigi icin rapor daha dar claim ceiling'de kalir.")
    else:
        lines.append("Current invocation Episode Feature yuzeyi tamamlanmadi; eski artifact current evidence olarak kullanilmaz.")
    lines.extend([
        "Takim/oyuncu aday dagilimlari yalniz current invocation attribution ve aggregate candidate yuzeyini anlatir; possession, dominance veya control degildir.",
        "",
        "[9] FORBIDDEN_INFERENCE",
        "Tracking/video olmadan team shape, defensive line height, compactness, off-ball structure/run, passing options, body orientation, scanning, fatigue/load/speed, true pressure geometry, coach intention, tactical plan, dominance ve causality kanitlanmis sayilmaz.",
        "",
        "[10] CURRENT PRODUCT CEILING",
        "CSV/XML event-like occurrence ve XLSX aggregate surface artik ayni run'da birlikte tasinir; ayni provider yuzeyleri independent vote degildir.",
        "C01 ilk construct vertical slice'tir; occurrence-level progression semantics tam admission gecmeden progression truth uretilmez.",
        "Phase/state etiketleri activity candidate'dir; phase truth degildir.",
        "MICRO/MEZZO/MACRO bir evidence-routing lattice'tir; macro claim mikro/mezo evidence'dan kopamaz.",
        "Player/GK/team gorunumleri candidate identity ve aggregate cell yuzeyidir; validated identity/quality truth degildir.",
        "",
        "[11] CLAIM LOCKS",
        "canonical_event_count=UNKNOWN",
        "true_action_count=UNKNOWN",
        "phase_truth=false",
        "possession_truth=false",
        "sequence_truth=false",
        "rhythm_truth=false",
        "tactical_truth=false",
        "production_release=false",
        "",
    ])
    return "\n".join(lines)


def _declared_current_artifacts(root: Path, full_spine: dict[str, Any]) -> list[Path]:
    declared = full_spine.get("current_invocation_artifacts")
    values = declared if isinstance(declared, list) else []
    values = [
        *values,
        *_post_sequence_current_artifacts(full_spine),
        str(root / FULL_SPINE_JSON),
        str(root / FULL_SPINE_TXT),
        str(root / ANALYST_REPORT),
        str(root / ANALYST_REPORT_TR),
        str(root / ANALYST_REPORT_EN),
    ]
    seen: set[str] = set()
    candidates: list[Path] = []
    for raw in values:
        path = Path(str(raw)).expanduser().resolve(strict=False)
        if path.parent != root or not path.is_file():
            continue
        if path.name in {BUNDLE_ZIP, BUNDLE_MANIFEST} or path.name in seen:
            continue
        seen.add(path.name)
        candidates.append(path)
    return sorted(candidates, key=lambda item: item.name.casefold())


def write_standard_user_outputs(
    output_root: str | Path,
    full_spine: dict[str, Any],
    *,
    before_state: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    root = Path(output_root).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    _ = before_state

    report_path = root / ANALYST_REPORT
    report_tr_path = root / ANALYST_REPORT_TR
    report_en_path = root / ANALYST_REPORT_EN
    manifest_path = root / BUNDLE_MANIFEST
    zip_path = root / BUNDLE_ZIP
    temp_zip_path = root / f".{BUNDLE_ZIP}.tmp"
    if temp_zip_path.is_file():
        temp_zip_path.unlink()

    report_path.write_text(build_analyst_report(root, full_spine), encoding="utf-8")
    report_tr_path.write_text(build_human_analyst_report_tr(root, full_spine), encoding="utf-8")
    report_en_path.write_text(build_human_analyst_report_en(root, full_spine), encoding="utf-8")
    candidates = _declared_current_artifacts(root, full_spine)
    entries = [
        {"name": path.name, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in candidates
    ]
    manifest = {
        "module_id": "active_match_standard_user_bundle_v1",
        "bundle_scope": "PRODUCER_DECLARED_CURRENT_INVOCATION_ARTIFACTS_PLUS_STANDARD_DELIVERABLES",
        "selection_basis": "PRODUCER_WRITE_LEDGER_NOT_MTIME_OR_CONTENT_CHANGE_HEURISTIC",
        "runtime_status": full_spine.get("status"),
        "active_match_authority": full_spine.get("active_match_authority"),
        "feature_surface_current_invocation": _feature_surface_current(full_spine),
        "rich_multiformat_surface_current_invocation": _rich_surface_current(full_spine),
        "c4_surface_current_invocation": _c4_surface_current(full_spine),
        "post_sequence_current_invocation_artifact_count": len(_post_sequence_current_artifacts(full_spine)),
        "file_count_before_manifest": len(entries),
        "files": entries,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    try:
        with zipfile.ZipFile(temp_zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in candidates:
                archive.write(path, arcname=path.name)
            archive.write(manifest_path, arcname=manifest_path.name)
        with zipfile.ZipFile(temp_zip_path, "r") as check:
            bad_member = check.testzip()
            if bad_member is not None:
                raise ValueError(f"bundle_zip_crc_failed:{bad_member}")
        temp_zip_path.replace(zip_path)
    except Exception:
        if temp_zip_path.is_file():
            temp_zip_path.unlink()
        raise

    return {
        "analyst_report": str(report_path),
        "analyst_report_tr": str(report_tr_path),
        "analyst_report_en": str(report_en_path),
        "bundle_manifest": str(manifest_path),
        "bundle_zip": str(zip_path),
        "bundle_file_count": len(candidates) + 1,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
