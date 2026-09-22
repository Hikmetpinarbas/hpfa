from __future__ import annotations

import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

ANALYST_REPORT = "HPFA_ANALYST_REPORT.txt"
BUNDLE_MANIFEST = "HPFA_ACTIVE_MATCH_BUNDLE_MANIFEST.json"
BUNDLE_ZIP = "HPFA_ACTIVE_MATCH_BUNDLE.zip"
EPISODE_FEATURE_JSON = "episode_feature_vector_lite_v1.json"
FULL_SPINE_JSON = "active_match_full_spine_v1.json"
FULL_SPINE_TXT = "active_match_full_spine_v1.txt"


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


def _safe_sentences(full_spine: dict[str, Any], limit: int = 12) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    chains = full_spine.get("intelligence_chains")
    if not isinstance(chains, list):
        return result
    for chain in chains:
        if not isinstance(chain, dict):
            continue
        safe = chain.get("safe_sentence")
        if not isinstance(safe, dict):
            continue
        text = str(safe.get("safe_sentence_candidate_tr") or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
        if len(result) >= limit:
            break
    return result


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


def _p02_team_name_map(rich: dict[str, Any]) -> dict[str, str]:
    p02 = rich.get("progression_pool_p02") or {}
    result: dict[str, str] = {}
    for item in p02.get("p02_team_pool_items") or []:
        if not isinstance(item, dict):
            continue
        team_id = str(item.get("team_identity_candidate_id") or "")
        team_candidate = str(item.get("team_candidate") or "").strip()
        if team_id and team_candidate and team_id not in result:
            result[team_id] = team_candidate
    return result


def _p02_turnover_response_lines(rich: dict[str, Any]) -> list[str]:
    p02 = rich.get("progression_pool_p02") or {}
    process_units = p02.get("process_units") or {}
    summaries = process_units.get("opponent_response_summary_by_team") or []
    if not isinstance(summaries, list):
        return []
    team_names = _p02_team_name_map(rich)
    lines: list[str] = []
    for row in summaries:
        if not isinstance(row, dict):
            continue
        team_id = str(row.get("team_identity_candidate_id") or "")
        team_name = team_names.get(team_id, team_id or "UNRESOLVED_TEAM")
        denominator = int(row.get("turnover_handover_linked_count") or 0)
        advanced = int(row.get("turnover_handover_opponent_advanced_access_count") or 0)
        no_advanced = int(row.get("turnover_handover_opponent_no_advanced_access_count") or 0)
        unresolved = int(row.get("turnover_handover_opponent_access_unresolved_count") or 0)
        if denominator <= 0:
            continue
        lines.append(
            f"- {team_name}: gorunur TURNOVER iceren ve exact handover ile rakip response'a baglanan "
            f"{denominator} process-unit; rakibin ilk gorunur response'unda advanced access={advanced}, "
            f"no advanced access={no_advanced}, unresolved={unresolved}. "
            "Bu bag nedensellik, tehlikeli gecis veya taktik ustunluk kaniti degildir."
        )
    return lines


def _readable_boundary_counts(counts: dict[str, Any]) -> str:
    labels = {
        "TEAM_HANDOVER_BOUNDARY": "takim el degistirme",
        "MIXED_TEAM_PRIMARY_LAYER_BOUNDARY": "karisik ayni-an siniri",
        "TIME_GAP_BOUNDARY": "zaman boslugu",
        "RESTART_PRIMARY_LAYER_BOUNDARY": "restart",
        "TERMINAL_OUTCOME_SUPPORT_BOUNDARY": "terminal sonuc destegi",
        "PERIOD_END": "devre sonu",
    }
    parts: list[str] = []
    for key, value in sorted((counts or {}).items(), key=lambda item: (-int(item[1] or 0), str(item[0]))):
        try:
            count = int(value or 0)
        except (TypeError, ValueError):
            continue
        if count <= 0:
            continue
        parts.append(f"{labels.get(str(key), str(key).casefold())}={count}")
    return ", ".join(parts) if parts else "gorunur bitis siniri yok"


def _p02_process_mechanism_lines(rich: dict[str, Any]) -> list[str]:
    p02 = rich.get("progression_pool_p02") or {}
    team_names = _p02_team_name_map(rich)
    lines: list[str] = []

    post_loss_signature = "ANCHOR:TURNOVER -> L1:OPPONENT:PASS -> L2:OPPONENT:PASS"
    post_loss_rows = [
        row for row in (p02.get("visible_consequence_path_severity_candidates") or [])
        if isinstance(row, dict)
        and str(row.get("visible_consequence_path_signature") or "") == post_loss_signature
    ]
    if post_loss_rows:
        lines.append("Top kaybi sonrasi rakibin pas-pas devami:")
        for row in sorted(post_loss_rows, key=lambda item: team_names.get(str(item.get("team_identity_candidate_id") or ""), "")):
            team_id = str(row.get("team_identity_candidate_id") or "")
            team_name = team_names.get(team_id, team_id or "cozulemeyen takim")
            eligible = int(row.get("eligible_anchor_population_count") or 0)
            visible = int(row.get("visible_occurrence_count") or 0)
            bound = int(row.get("exact_process_response_bound_count") or 0)
            final_third = int(row.get("final_third_visible_count") or 0)
            no_final_third = int(row.get("no_final_third_visible_count") or 0)
            unresolved = int(row.get("zone_path_unresolved_count") or 0)
            box = int(row.get("penalty_area_visible_count") or 0)
            shots = int(row.get("shot_activity_visible_count") or 0)
            routes = row.get("response_zone_route_counts") or {}
            dominant_route = ""
            if isinstance(routes, dict) and routes:
                route, count = max(
                    routes.items(),
                    key=lambda item: (int(item[1] or 0), str(item[0])),
                )
                dominant_route = f"; en sik gorunur bolge baslangic-bitis yolu {str(route).replace('->', ' -> ')} ({int(count or 0)})"
            lines.append(
                f"- {team_name}: gorunur devami degerlendirilebilir {eligible} top-kaybi adayinin {visible}'inde "
                f"rakip ilk iki devam katmanini pas -> pas ile surdurdu; bunlarin {bound}'i sonraki rakip oyun surecine "
                f"baglanabildi. Bu baglarda final-third gorundu={final_third}, final-third gorunmedi={no_final_third}, "
                f"bolge sonucu cozulmedi={unresolved}, ceza-sahasi gorundu={box}, sut aktivitesi gorundu={shots}"
                f"{dominant_route}."
            )

    pass_signature = "ANCHOR:PASS -> L1:SAME_TEAM:PASS -> L2:SAME_TEAM:PASS"
    pass_rows = [
        row for row in (p02.get("same_team_continuation_process_profiles") or [])
        if isinstance(row, dict)
        and str(row.get("visible_consequence_path_signature") or "") == pass_signature
    ]
    if pass_rows:
        lines.append("Pas dolasiminin final-third'e donusumu:")
        for row in sorted(pass_rows, key=lambda item: team_names.get(str(item.get("team_identity_candidate_id") or ""), "")):
            team_id = str(row.get("team_identity_candidate_id") or "")
            team_name = team_names.get(team_id, team_id or "cozulemeyen takim")
            windows = int(row.get("anchor_visible_occurrence_count") or 0)
            units = int(row.get("unique_process_unit_count") or 0)
            entries = int(row.get("process_unit_with_final_third_entry_count") or 0)
            continuations = int(row.get("process_unit_with_final_third_continuation_count") or 0)
            no_final_third = int(row.get("process_unit_with_no_final_third_visible_count") or 0)
            unresolved = int(row.get("process_unit_with_zone_unresolved_count") or 0)
            entry_shots = int(row.get("final_third_entry_process_with_shot_activity_count") or 0)
            entry_turnovers = int(row.get("final_third_entry_process_with_turnover_activity_count") or 0)
            entry_crosses = int(row.get("final_third_entry_process_with_cross_activity_count") or 0)
            max_windows = int(row.get("max_anchor_windows_within_single_process_unit") or 0)
            boundary_text = _readable_boundary_counts(row.get("final_third_entry_process_end_reason_counts") or {})
            lines.append(
                f"- {team_name}: {windows} gorunur pas -> pas -> pas penceresi {units} benzersiz oyun surecinde toplandi "
                f"(tek surecte en fazla {max_windows} pencere). Yeni final-third girisi gorunen surec={entries}, "
                f"final-third icinde devam eden={continuations}, final-third'e ulasmayan={no_final_third}, "
                f"bolgesi cozulmeyen={unresolved}. Final-third'e yeni giren sureclerde sut aktivitesi={entry_shots}, "
                f"turnover aktivitesi={entry_turnovers}, cross aktivitesi={entry_crosses}; gorunur bitisler: {boundary_text}."
            )

    recovery_signature = "ANCHOR:RECOVERY -> L1:SAME_TEAM:PASS -> L2:SAME_TEAM:PASS"
    recovery_rows = [
        row for row in (p02.get("same_team_continuation_process_profiles") or [])
        if isinstance(row, dict)
        and str(row.get("visible_consequence_path_signature") or "") == recovery_signature
    ]
    if recovery_rows:
        lines.append("Recovery sonrasi ayni takimin yeniden hucum devami:")
        for row in sorted(recovery_rows, key=lambda item: team_names.get(str(item.get("team_identity_candidate_id") or ""), "")):
            team_id = str(row.get("team_identity_candidate_id") or "")
            team_name = team_names.get(team_id, team_id or "cozulemeyen takim")
            units = int(row.get("unique_process_unit_count") or 0)
            entries = int(row.get("process_unit_with_final_third_entry_count") or 0)
            continuations = int(row.get("process_unit_with_final_third_continuation_count") or 0)
            no_final_third = int(row.get("process_unit_with_no_final_third_visible_count") or 0)
            unresolved = int(row.get("process_unit_with_zone_unresolved_count") or 0)
            shots = int(row.get("process_unit_with_shot_activity_after_anchor_count") or 0)
            lines.append(
                f"- {team_name}: recovery -> pas -> pas yolu {units} benzersiz oyun surecine baglandi; "
                f"yeni final-third girisi={entries}, final-third icinde devam={continuations}, "
                f"final-third'e ulasmayan={no_final_third}, bolgesi cozulmeyen={unresolved}, "
                f"recovery sonrasinda ayni surecte sut aktivitesi={shots}."
            )

    if lines:
        lines.append(
            "- Okuma siniri: bunlar mac-ici gorunur surec ve tekrar adaylaridir; ayni surecteki coklu pencereler "
            "bagimsiz kanit sayilmaz. Bu yuzey tek basina taktik niyet, kalite, ustunluk veya nedensellik kaniti degildir."
        )
    return lines


def build_analyst_report(output_root: str | Path, full_spine: dict[str, Any]) -> str:
    root = Path(output_root)
    feature_current = _feature_surface_current(full_spine)
    c4_current = _c4_surface_current(full_spine)
    rich_current = _rich_surface_current(full_spine)
    features = _load_json(root / EPISODE_FEATURE_JSON) if feature_current else {}
    rich = full_spine.get("rich_multiformat_analysis_lattice") if rich_current else {}
    rich = rich if isinstance(rich, dict) else {}
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
            "construct_candidate_is_metric_truth=false",
        ])
        p02_response_lines = _p02_turnover_response_lines(rich)
        if p02_response_lines:
            lines.extend([
                "turnover_handover_opponent_response:",
                *p02_response_lines,
            ])
        mechanism_lines = _p02_process_mechanism_lines(rich)
        if mechanism_lines:
            lines.extend([
                "",
                "MAC MEKANIZMASI ADAYLARI — SUREC / DEVAM / SONUC",
                *mechanism_lines,
            ])
    else:
        lines.append("- Rich metric/construct/layer surface unavailable for this invocation.")

    safe = _safe_sentences(full_spine) if c4_current else []
    lines.extend(["", "[5] SAFE_ARGUMENT_CANDIDATES — MEVCUT C4 BLOKLARI"])
    if safe:
        lines.extend(f"- {text}" for text in safe)
    elif c4_current:
        lines.append("- Bu run'da yayinlanabilir safe-sentence candidate gorunmedi.")
    else:
        lines.append("- Current invocation C4 producer zinciri tamamlanmadi; onceki run argumani kullanilmadi.")

    lines.extend([
        "",
        "[6] COUNTEREVIDENCE / UNCERTAINTY",
        f"review_hits={full_spine.get('review_hits') or []}",
        f"review_debt_feature_vector_count={features.get('review_debt_feature_vector_count') if feature_current else 'UNAVAILABLE_CURRENT_INVOCATION'}",
        f"total_unresolved_semantics_context_count={features.get('total_unresolved_semantics_context_count') if feature_current else 'UNAVAILABLE_CURRENT_INVOCATION'}",
        f"rich_lane_review_hits={(rich.get('review_hits') or []) if rich_current else 'UNAVAILABLE_CURRENT_INVOCATION'}",
        "absence_of_evidence_is_counterevidence=false",
        "",
        "[7] SAFE_MEANING",
    ])
    if feature_current and rich_current and c4_current:
        lines.append("Bu rapor current invocation icinde uretilen ZFGV observation/occurrence/episode/process yuzeyi, XLSX aggregate row projection, primitive/construct adaylari ve mevcut C4 defeasible argument yuzeyini ayni evidence zincirinde birlestirir; EVENT bu gozlem evreninin yalniz bir ailesidir.")
    elif feature_current and rich_current:
        lines.append("Current invocation occurrence/episode ve multiformat aggregate yuzeyi mevcut; C4 tamamlanmadigi icin argument sonucu current evidence olarak yayinlanmadi.")
    elif feature_current:
        lines.append("Current invocation Episode Feature yuzeyi mevcut; multiformat/construct veya C4 yuzeyi tamamlanmadigi icin rapor daha dar claim ceiling'de kalir.")
    else:
        lines.append("Current invocation Episode Feature yuzeyi tamamlanmadi; eski artifact current evidence olarak kullanilmaz.")
    lines.extend([
        "Takim/oyuncu aday dagilimlari yalniz current invocation attribution ve aggregate candidate yuzeyini anlatir; possession, dominance veya control degildir.",
        "",
        "[8] FORBIDDEN_INFERENCE",
        "Tracking/video olmadan team shape, defensive line height, compactness, off-ball structure/run, passing options, body orientation, scanning, fatigue/load/speed, true pressure geometry, coach intention, tactical plan, dominance ve causality kanitlanmis sayilmaz.",
        "",
        "[9] CURRENT PRODUCT CEILING",
        "CSV/XML admitted observation/occurrence ve XLSX aggregate surface artik ayni run'da birlikte tasinir; ayni provider yuzeyleri independent vote degildir.",
        "C01 ilk construct vertical slice'tir; occurrence-level progression semantics tam admission gecmeden progression truth uretilmez.",
        "Phase/state etiketleri activity candidate'dir; phase truth degildir.",
        "MICRO/MEZZO/MACRO bir evidence-routing lattice'tir; macro claim mikro/mezo evidence'dan kopamaz.",
        "Player/GK/team gorunumleri candidate identity ve aggregate cell yuzeyidir; validated identity/quality truth degildir.",
        "",
        "[10] CLAIM LOCKS",
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
    values = [*values, str(root / FULL_SPINE_JSON), str(root / FULL_SPINE_TXT), str(root / ANALYST_REPORT)]
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
    manifest_path = root / BUNDLE_MANIFEST
    zip_path = root / BUNDLE_ZIP
    temp_zip_path = root / f".{BUNDLE_ZIP}.tmp"
    if temp_zip_path.is_file():
        temp_zip_path.unlink()

    report_path.write_text(build_analyst_report(root, full_spine), encoding="utf-8")
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
        "bundle_manifest": str(manifest_path),
        "bundle_zip": str(zip_path),
        "bundle_file_count": len(candidates) + 1,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
