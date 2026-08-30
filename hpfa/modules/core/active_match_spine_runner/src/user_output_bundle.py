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


def build_analyst_report(output_root: str | Path, full_spine: dict[str, Any]) -> str:
    root = Path(output_root)
    features = _load_json(root / EPISODE_FEATURE_JSON)
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
        "",
        "[1] WHAT_VISIBLE — GORUNUR MAC YUZEYI",
        f"eligible_action_candidate_total={features.get('total_eligible_action_candidate_count')}",
        f"action_family_candidates={json.dumps(family_totals, ensure_ascii=False, sort_keys=True)}",
        f"known_team_attributed_candidates={known_team_total}",
        f"unknown_team_attribution_candidates={unknown_team_total}",
        f"team_candidate_distribution={json.dumps(team_totals, ensure_ascii=False, sort_keys=True)}",
        f"zone_candidate_distribution={json.dumps(zone_totals, ensure_ascii=False, sort_keys=True)}",
        f"channel_candidate_distribution={json.dumps(channel_totals, ensure_ascii=False, sort_keys=True)}",
        "",
        "[2] WHERE_WHEN — EN YUKSEK GORUNUR EPISODE YUZEYLERI",
        "shot_candidate_yogunlugu:",
    ]
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

    safe = _safe_sentences(full_spine)
    lines.extend(["", "[3] SAFE_ARGUMENT_CANDIDATES — MEVCUT C4 BLOKLARI"])
    if safe:
        lines.extend(f"- {text}" for text in safe)
    else:
        lines.append("- Bu run'da yayinlanabilir safe-sentence candidate gorunmedi.")

    lines.extend([
        "",
        "[4] COUNTEREVIDENCE / UNCERTAINTY",
        f"review_hits={full_spine.get('review_hits') or []}",
        f"review_debt_feature_vector_count={features.get('review_debt_feature_vector_count')}",
        f"total_unresolved_semantics_context_count={features.get('total_unresolved_semantics_context_count')}",
        "absence_of_evidence_is_counterevidence=false",
        "",
        "[5] SAFE_MEANING",
        "Bu rapor admitted event-only yuzeylerden uretilmis aday aksiyon, episode, mekansal dagilim ve mevcut C4 guvenli arguman yuzeylerini bir araya getirir.",
        "Takim/oyuncu aday dagilimlari yalniz bilinen attribution yuzeyini anlatir; possession, dominance veya control degildir.",
        "",
        "[6] FORBIDDEN_INFERENCE",
        "Tracking/video olmadan team shape, defensive line height, compactness, off-ball structure/run, passing options, body orientation, scanning, fatigue/load/speed, true pressure geometry, coach intention, tactical plan, dominance ve causality kanitlanmis sayilmaz.",
        "",
        "[7] PRODUCT GAPS VISIBLE IN THIS REPORT",
        "CSV/XML/XLSX object-level fusion henuz tamamlanmadi.",
        "XLSX row-aligned metric cells henuz current runtime intelligence packet'larina tam bagli degil.",
        "Primitive -> relational -> construct/composite metric katmani henuz tam urunlesmedi.",
        "Phase/state candidate, MICRO->MEZZO->MACRO ve player/GK/team bidirectional argument bloklari siradaki product katmanidir.",
        "",
        "[8] CLAIM LOCKS",
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


def write_standard_user_outputs(
    output_root: str | Path,
    full_spine: dict[str, Any],
    *,
    run_started_ns: int | None = None,
) -> dict[str, Any]:
    root = Path(output_root).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)

    report_path = root / ANALYST_REPORT
    manifest_path = root / BUNDLE_MANIFEST
    zip_path = root / BUNDLE_ZIP
    for path in (report_path, manifest_path, zip_path):
        if path.is_file():
            path.unlink()

    report_path.write_text(build_analyst_report(root, full_spine), encoding="utf-8")

    candidates: list[Path] = []
    for path in sorted(root.iterdir(), key=lambda item: item.name.casefold()):
        if not path.is_file() or path.name in {BUNDLE_ZIP, BUNDLE_MANIFEST}:
            continue
        if path.name == ANALYST_REPORT:
            candidates.append(path)
            continue
        if run_started_ns is None or path.stat().st_mtime_ns >= run_started_ns:
            candidates.append(path)

    entries = [
        {
            "name": path.name,
            "size_bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in candidates
    ]
    manifest = {
        "module_id": "active_match_standard_user_bundle_v1",
        "bundle_scope": "FILES_CREATED_OR_REWRITTEN_DURING_CURRENT_INVOCATION",
        "runtime_status": full_spine.get("status"),
        "active_match_authority": full_spine.get("active_match_authority"),
        "file_count_before_manifest": len(entries),
        "files": entries,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in candidates:
            archive.write(path, arcname=path.name)
        archive.write(manifest_path, arcname=manifest_path.name)

    return {
        "analyst_report": str(report_path),
        "bundle_manifest": str(manifest_path),
        "bundle_zip": str(zip_path),
        "bundle_file_count": len(candidates) + 1,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
