from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

from analyst_mechanism_review import (
    _focus_actor_ref,
    _select_actor_locator,
    build_mechanism_review_lines,
)
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
PROCESS_VARIANT_JSON = "observable_process_variant_binding_projection_v1.json"
PROCESS_PARTICIPATION_JSON = "analyst_episode_process_participation_projection_v1.json"
VARIANT_FEATURE_CHALLENGE_JSON = "variant_feature_challenge_projection_v1.json"
SAFE_FINDING_ADMISSION_JSON = "safe_finding_admission_projection_v1.json"
VISIBLE_SEQUENCE_JSON = "visible_action_sequence_candidates_lite_v1.json"
RICH_MULTIFORMAT_JSON = "rich_multiformat_analysis_lattice_v1.json"
MULTIFORMAT_INVENTORY_JSON = "multiformat_file_inventory_lite_v1.json"


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


def _stable_json_sha256(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _git_head(execution_root: Any) -> str | None:
    root = Path(str(execution_root or "")).expanduser().resolve(strict=False)
    if not root.exists():
        return None
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = completed.stdout.strip().casefold()
    return value if len(value) == 40 and all(ch in "0123456789abcdef" for ch in value) else None


def _input_snapshot_identity(root: Path, full_spine: dict[str, Any]) -> dict[str, Any]:
    if not _declared_current(full_spine, MULTIFORMAT_INVENTORY_JSON):
        return {"status": "REVIEW_REQUIRED", "reason": "current_multiformat_inventory_not_declared"}
    payload = _load_json(root / MULTIFORMAT_INVENTORY_JSON)
    rows: list[dict[str, Any]] = []
    for row in payload.get("files") or []:
        if not isinstance(row, dict):
            continue
        relative = str(row.get("relative_path") or row.get("file_name") or "").strip()
        sha = str(row.get("sha256") or "").strip().casefold()
        if not relative or len(sha) != 64 or not all(ch in "0123456789abcdef" for ch in sha):
            continue
        rows.append({
            "relative_path": relative,
            "sha256": sha,
            "size_bytes": row.get("size_bytes"),
            "source_role": row.get("source_role"),
        })
    rows.sort(key=lambda row: (str(row.get("relative_path") or "").casefold(), str(row.get("sha256") or "")))
    if not rows:
        return {"status": "REVIEW_REQUIRED", "reason": "inventory_has_no_hash_bound_files"}
    return {
        "status": "PASS",
        "file_count": len(rows),
        "fingerprint_sha256": _stable_json_sha256(rows),
        "source": MULTIFORMAT_INVENTORY_JSON,
        "snapshot_fingerprint_is_event_truth": False,
    }


def _runtime_environment_identity() -> dict[str, Any]:
    packages: list[str] = []
    try:
        for dist in importlib.metadata.distributions():
            name = str(dist.metadata.get("Name") or "").strip()
            version = str(dist.version or "").strip()
            if name and version:
                packages.append(f"{name.casefold()}=={version}")
    except Exception:
        packages = []
    packages = sorted(set(packages))
    basis = {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "packages": packages,
    }
    return {
        "fingerprint_sha256": _stable_json_sha256(basis),
        "python_version": basis["python_version"],
        "python_implementation": basis["python_implementation"],
        "package_count": len(packages),
        "environment_fingerprint_is_runtime_acceptance": False,
    }


def _current_run_provenance_envelope(
    root: Path,
    full_spine: dict[str, Any],
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    exact_head = _git_head(full_spine.get("execution_root"))
    input_snapshot = _input_snapshot_identity(root, full_spine)
    environment = _runtime_environment_identity()
    artifact_manifest_digest = _stable_json_sha256(entries)
    status = "PASS" if exact_head and input_snapshot.get("status") == "PASS" else "REVIEW_REQUIRED"
    identity_basis = {
        "exact_head_sha": exact_head,
        "active_match_authority": full_spine.get("active_match_authority"),
        "input_snapshot_fingerprint": input_snapshot.get("fingerprint_sha256"),
        "runtime_environment_fingerprint": environment.get("fingerprint_sha256"),
        "artifact_manifest_digest": artifact_manifest_digest,
    }
    return {
        "module_id": "current_run_provenance_envelope_v1",
        "status": status,
        "identity_kind": "DETERMINISTIC_CONTEXT_FINGERPRINT_NOT_UNIQUE_INVOCATION_UUID",
        "current_run_context_fingerprint_sha256": _stable_json_sha256(identity_basis),
        "exact_head_sha": exact_head,
        "active_match_authority": full_spine.get("active_match_authority"),
        "input_snapshot": input_snapshot,
        "runtime_environment": environment,
        "artifact_manifest_digest_sha256": artifact_manifest_digest,
        "provenance_creates_new_football_evidence": False,
        "provenance_can_authorize_emit": False,
        "provenance_can_strengthen_claim_ceiling": False,
        "artifact_digest_is_semantic_correctness_truth": False,
        "exact_head_is_physical_acceptance_truth": False,
        "reproducibility_is_external_validity_truth": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


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
    secs = round(seconds - minutes * 60)
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
        "COUNTERATTACK": "kontra atak",
        "SET_PIECE_ATTACK": "duran top hücumu",
        "TRANSITION_ATTACK": "geçiş hücumu",
        "CIRCULATION": "top dolaşımı",
        "LOSS_TRANSITION": "top kaybı sonrası geçiş",
        "RECOVERY_TRANSITION": "top kazanımı sonrası geçiş",
        "TERMINAL": "hücumun son aksiyon bölümü",
        "RESTART": "duran top / yeniden başlatma",
    }
    labels_en = {
        "POSITIONAL_ATTACK": "positional attack",
        "COUNTERATTACK": "counterattack",
        "SET_PIECE_ATTACK": "set-piece attack",
        "TRANSITION_ATTACK": "attacking transition",
        "CIRCULATION": "circulation",
        "LOSS_TRANSITION": "post-loss transition",
        "RECOVERY_TRANSITION": "post-recovery transition",
        "TERMINAL": "terminal attacking phase",
        "RESTART": "restart",
    }
    table = labels_tr if language == "tr" else labels_en
    return table.get(key, key.replace("_", " ").lower() or ("süreç" if language == "tr" else "process"))


def _six_phase_label(value: Any, language: str) -> str:
    key = str(value or "").strip()
    labels_tr = {
        "ESTABLISHED_ATTACK": "yerleşik hücum",
        "ATTACKING_TRANSITION": "geçiş hücumu",
        "ATTACKING_SET_PIECE": "duran top hücumu",
        "ESTABLISHED_DEFENCE": "yerleşik savunma",
        "DEFENSIVE_TRANSITION": "geçiş savunması",
        "DEFENSIVE_SET_PIECE": "duran top savunması",
    }
    labels_en = {
        "ESTABLISHED_ATTACK": "established attack",
        "ATTACKING_TRANSITION": "attacking transition",
        "ATTACKING_SET_PIECE": "attacking set piece",
        "ESTABLISHED_DEFENCE": "established defence",
        "DEFENSIVE_TRANSITION": "defensive transition",
        "DEFENSIVE_SET_PIECE": "defensive set piece",
    }
    table = labels_tr if language == "tr" else labels_en
    return table.get(key, key.replace("_", " ").lower() or ("faz" if language == "tr" else "phase"))


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


def _human_validated_actor_labels(identity: dict[str, Any]) -> dict[str, str]:
    """Human-facing actor labels require explicit validated player identity."""
    result: dict[str, str] = {}
    for row in identity.get("actor_identity_candidates") or []:
        if not isinstance(row, dict):
            continue
        if row.get("validated_player_identity") is not True:
            continue
        if str(row.get("decision_state") or "") != "ACTOR_IDENTITY_CANDIDATE_BOUND":
            continue
        ref = str(row.get("actor_identity_candidate_id") or "").strip()
        raw = (
            row.get("actor_aliases_raw", [None])[0]
            if isinstance(row.get("actor_aliases_raw"), list) and row.get("actor_aliases_raw")
            else None
        )
        label = _display_label(raw or row.get("actor_normalized_key") or "")
        if ref and label and label != "UNKNOWN":
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
        bucket = by_team.setdefault(
            team_id,
            {
                "eligible": 0,
                "shot": 0,
                "loss": 0,
                "recovery": 0,
                "opponent_handover": 0,
                "opponent_takeover_after_breakdown": 0,
                "mixed_team_same_time_review": 0,
                "no_visible_followup": 0,
            },
        )
        bucket["eligible"] += int(row.get("eligible_process_n") or 0)
        bucket["shot"] += int(row.get("shot_ending_process_n") or 0)
        bucket["loss"] += int(row.get("visible_loss_process_n") or 0)
        bucket["recovery"] += int(row.get("visible_recovery_process_n") or 0)
        response_profile = row.get("visible_consequence_response_profile")
        presence = (
            response_profile.get("process_presence_counts") or {}
            if isinstance(response_profile, dict)
            else {}
        )
        bucket["opponent_handover"] += int(presence.get("OPPONENT_HANDOVER_CANDIDATE") or 0)
        bucket["opponent_takeover_after_breakdown"] += int(
            presence.get("OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE") or 0
        )
        bucket["mixed_team_same_time_review"] += int(
            presence.get("MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE") or 0
        )
        bucket["no_visible_followup"] += int(presence.get("NO_VISIBLE_FOLLOW_UP_CANDIDATE") or 0)
    cards: list[str] = []
    for team_id, values in sorted(by_team.items(), key=lambda item: teams.get(item[0], item[0])):
        name = teams.get(team_id, team_id)
        if language == "tr":
            football = (
                f"{name}: Sistem bu maçta {values['eligible']} görünür oyun sürecini takım bağlamına bağlayabildi. "
                f"Bunların {values['loss']} tanesinde top kaybı, {values['recovery']} tanesinde top kazanımı ve "
                f"{values['shot']} tanesinde şutla bağlantılı bir son bölüm görüldü. "
                f"Görünür devam/sonuç yüzeyinde {values['opponent_handover']} süreçte rakibe geçiş, "
                f"{values['opponent_takeover_after_breakdown']} süreçte breakdown sonrası rakip takeover, "
                f"{values['mixed_team_same_time_review']} süreçte aynı-zamanlı iki takım belirsizliği ve "
                f"{values['no_visible_followup']} süreçte görünür follow-up yokluğu kaydedildi."
            )
            evidence = (
                "Okuma çerçevesi: Aynı süreçte birden fazla consequence-response kategorisi birlikte yer alabilir. "
                "Bu yüzey rakibe geçiş, breakdown sonrası takeover, same-time review ve follow-up durumlarının "
                "maç-içi süreç kompozisyonunu gösterir."
            )
        else:
            football = (
                f"{name}: The system linked {values['eligible']} visible match processes to this team. "
                f"A visible loss occurred in {values['loss']}, a recovery in {values['recovery']}, and "
                f"a shot-linked terminal state in {values['shot']}. "
                f"On the visible consequence-response surface, {values['opponent_handover']} processes contained an opponent handover, "
                f"{values['opponent_takeover_after_breakdown']} an opponent takeover after breakdown, "
                f"{values['mixed_team_same_time_review']} a mixed-team same-time review state, and "
                f"{values['no_visible_followup']} no visible follow-up."
            )
            evidence = (
                "Reading frame: multiple consequence-response categories may coexist within the same process. "
                "This surface describes the match-local process composition of opponent handover, takeover after breakdown, "
                "same-time review, and follow-up states."
            )
        cards.extend([football, evidence])
    return cards


def _top_distribution_item(values: Any) -> tuple[str, int] | None:
    if not isinstance(values, dict) or not values:
        return None
    rows = []
    for key, value in values.items():
        try:
            rows.append((str(key), int(value)))
        except (TypeError, ValueError):
            continue
    return max(rows, key=lambda item: (item[1], item[0])) if rows else None


def _phase_anatomy_sentence(row: dict[str, Any], language: str) -> str:
    duration = row.get("mean_duration_candidate")
    actors = row.get("mean_actor_spread_candidate")
    layers = row.get("mean_temporal_layer_n")
    zone_transitions = row.get("mean_visible_zone_transition_candidate_n")
    start = _top_distribution_item(row.get("single_start_zone_distribution"))
    end = _top_distribution_item(row.get("single_end_zone_distribution"))
    parts = []
    if isinstance(duration, (int, float)):
        parts.append(f"ort. süre {duration:.1f} sn" if language == "tr" else f"mean duration {duration:.1f}s")
    if isinstance(actors, (int, float)):
        parts.append(f"ort. görünür oyuncu yayılımı {actors:.1f}" if language == "tr" else f"mean visible actor spread {actors:.1f}")
    if isinstance(layers, (int, float)):
        parts.append(f"ort. zaman katmanı {layers:.1f}" if language == "tr" else f"mean temporal layers {layers:.1f}")
    if isinstance(zone_transitions, (int, float)):
        parts.append(f"ort. görünür bölge geçişi {zone_transitions:.1f}" if language == "tr" else f"mean visible zone transitions {zone_transitions:.1f}")
    if start:
        parts.append(f"en sık tekil başlangıç bölgesi {start[0]} ({start[1]})" if language == "tr" else f"top single start zone {start[0]} ({start[1]})")
    if end:
        parts.append(f"en sık tekil bitiş bölgesi {end[0]} ({end[1]})" if language == "tr" else f"top single end zone {end[0]} ({end[1]})")
    return "; ".join(parts)


def _phase_motif_sentence(row: dict[str, Any], language: str) -> str:
    motif_n = int(row.get("recurring_process_motif_family_count") or 0)
    covered = int(row.get("recurring_process_motif_covered_process_n") or 0)
    motifs = [m for m in (row.get("top_recurring_process_motifs") or []) if isinstance(m, dict)]
    if motif_n <= 0 or not motifs:
        return ""
    top = motifs[0]
    morphology = top.get("morphology_signature") or {}
    member_n = int(top.get("member_process_n") or 0)
    shot_n = int(top.get("shot_variant_n") or 0)
    loss_n = int(top.get("visible_loss_variant_n") or 0)
    recovery_n = int(top.get("visible_recovery_variant_n") or 0)
    action_presence = "+".join(str(v) for v in (morphology.get("action_family_presence") or [])) or "NO_ACTION_FAMILY"
    length_bucket = str(morphology.get("length_bucket") or "UNKNOWN")
    style = str(morphology.get("pass_carry_style") or "UNKNOWN")
    route_hint = str(morphology.get("route_hint") or "UNKNOWN")
    divergence = top.get("representative_first_supported_grammar_divergence")
    divergence_text = ""
    if isinstance(divergence, dict):
        first = divergence.get("first_supported_grammar_divergence") or {}
        op = str(first.get("operation") or "")
        left_token = str(first.get("left_token") or "∅")
        right_token = str(first.get("right_token") or "∅")
        left_context = str(divergence.get("left_variant_context") or "UNKNOWN")
        right_context = str(divergence.get("right_variant_context") or "UNKNOWN")
        if op:
            if language == "tr":
                divergence_text = (
                    f" İlk destekli grammar ayrışması: {left_context} ↔ {right_context}; "
                    f"{op}, {left_token} ↔ {right_token}. Bu satır görünür ayrışma noktasını karşılaştırma için işaretler."
                )
            else:
                divergence_text = (
                    f" First supported grammar divergence: {left_context} ↔ {right_context}; "
                    f"{op}, {left_token} ↔ {right_token}. This line marks the visible divergence point for comparison."
                )
    if language == "tr":
        return (
            f"Tekrarlayan motifler: {motif_n} aile, {covered} süreç kapsıyor. En sık motif {member_n} örnek; "
            f"{length_bucket}, {action_presence}, {style}, rota ipucu {route_hint}; "
            f"varyantlar: {shot_n} şut bağlantılı, {loss_n} görünür kayıp, {recovery_n} görünür recovery."
            + divergence_text
        )
    return (
        f"Recurring motifs: {motif_n} families covering {covered} processes. Top motif has {member_n} examples; "
        f"{length_bucket}, {action_presence}, {style}, route hint {route_hint}; "
        f"variants: {shot_n} shot-linked, {loss_n} visible loss, {recovery_n} visible recovery."
        + divergence_text
    )



def _representative_replay_sentence(row: dict[str, Any], language: str) -> str:
    rep = row.get("representative_shot_process")
    if not isinstance(rep, dict):
        rep = row.get("representative_loss_process")
    if not isinstance(rep, dict):
        return ""
    start = _fmt_time(rep.get("process_start_candidate"))
    end = _fmt_time(rep.get("process_end_candidate"))
    start_zones = ", ".join(str(v) for v in (rep.get("start_zone_candidates") or [])) or "UNKNOWN"
    end_zones = ", ".join(str(v) for v in (rep.get("end_zone_candidates") or [])) or "UNKNOWN"
    layers = int(rep.get("temporal_layer_n") or 0)
    actors = int(rep.get("unique_actor_candidate_n") or 0)
    if language == "tr":
        kind = "şut bağlantılı örnek" if rep.get("shot_present_annotation_candidate") is True else "kayıp bağlantılı örnek"
        return f"Örnek replay: {kind} {start}-{end}, {start_zones} → {end_zones}, {layers} zaman katmanı, {actors} görünür oyuncu."
    kind = "shot-linked example" if rep.get("shot_present_annotation_candidate") is True else "loss-linked example"
    return f"Example replay: {kind} {start}-{end}, {start_zones} → {end_zones}, {layers} temporal layers, {actors} visible actors."


def _human_process_contest_cards(rich: dict[str, Any], identity: dict[str, Any], language: str) -> list[str]:
    c03 = (rich.get("constructs") or {}).get("C03") or {}
    matrix = [row for row in (c03.get("six_phase_team_matrix") or []) if isinstance(row, dict)]
    teams = _human_team_labels(identity)
    if matrix:
        phase_order = {
            "ESTABLISHED_ATTACK": 0,
            "ATTACKING_TRANSITION": 1,
            "ATTACKING_SET_PIECE": 2,
            "ESTABLISHED_DEFENCE": 3,
            "DEFENSIVE_TRANSITION": 4,
            "DEFENSIVE_SET_PIECE": 5,
        }
        rows = sorted(
            matrix,
            key=lambda row: (
                teams.get(str(row.get("team_identity_candidate_id") or ""), str(row.get("team_identity_candidate_id") or "")),
                phase_order.get(str(row.get("canonical_phase_slot") or ""), 99),
            ),
        )
        cards: list[str] = []
        current_team = None
        for row in rows:
            team_id = str(row.get("team_identity_candidate_id") or "")
            opp_id = str(row.get("opponent_team_identity_candidate_id") or "")
            team_name = teams.get(team_id, team_id)
            opp_name = teams.get(opp_id, opp_id)
            if team_name != current_team:
                cards.append(f"{team_name} — 6 faz" if language == "tr" else f"{team_name} — six phases")
                current_team = team_name
            phase = _six_phase_label(row.get("canonical_phase_slot"), language)
            state = str(row.get("observation_state") or "")
            if state != "VISIBLE_PROCESS_PROFILE_AVAILABLE":
                cards.append(
                    f"{phase}: mevcut veride değerlendirilemedi." if language == "tr"
                    else f"{phase}: not observable with current data."
                )
                continue
            process_n = int(row.get("eligible_process_n") or 0)
            shot_n = int(row.get("shot_ending_process_n") or 0)
            loss_n = int(row.get("visible_loss_process_n") or 0)
            recovery_n = int(row.get("visible_recovery_process_n") or 0)
            perspective = str(row.get("perspective") or "")
            if language == "tr":
                if perspective == "ATTACK":
                    base = (
                        f"{phase}: {process_n} görünür süreç; {shot_n} şut bağlantılı son bölüm, "
                        f"{loss_n} görünür top kaybı, {recovery_n} görünür top kazanımı."
                    )
                    anatomy = _phase_anatomy_sentence(row, language)
                    motif = _phase_motif_sentence(row, language)
                    replay = _representative_replay_sentence(row, language)
                    cards.append(" ".join(part for part in (base, anatomy, motif, replay) if part))
                else:
                    source_family = _football_family_label(row.get("source_process_family_candidate"), language)
                    base = (
                        f"{phase}: {opp_name} tarafından kurulan {process_n} {source_family} sürecine karşı görünür savunma maruziyeti; "
                        f"rakibin {shot_n} süreci şut bağlantılı sona, {loss_n} süreci görünür top kaybına, "
                        f"{recovery_n} süreci görünür top kazanımına bağlandı."
                    )
                    anatomy = _phase_anatomy_sentence(row, language)
                    motif = _phase_motif_sentence(row, language)
                    replay = _representative_replay_sentence(row, language)
                    cards.append(" ".join(part for part in (base, anatomy, motif, replay) if part))
            else:
                if perspective == "ATTACK":
                    base = (
                        f"{phase}: {process_n} visible processes; {shot_n} shot-linked terminal segments, "
                        f"{loss_n} visible losses, {recovery_n} visible recoveries."
                    )
                    anatomy = _phase_anatomy_sentence(row, language)
                    motif = _phase_motif_sentence(row, language)
                    replay = _representative_replay_sentence(row, language)
                    cards.append(" ".join(part for part in (base, anatomy, motif, replay) if part))
                else:
                    source_family = _football_family_label(row.get("source_process_family_candidate"), language)
                    base = (
                        f"{phase}: visible defensive exposure against {process_n} {opp_name} {source_family} processes; "
                        f"{shot_n} opponent processes reached a shot-linked terminal segment, {loss_n} a visible loss, "
                        f"and {recovery_n} a visible recovery."
                    )
                    anatomy = _phase_anatomy_sentence(row, language)
                    motif = _phase_motif_sentence(row, language)
                    replay = _representative_replay_sentence(row, language)
                    cards.append(" ".join(part for part in (base, anatomy, motif, replay) if part))
        if language == "tr":
            cards.append(
                "Okuma çerçevesi: 12 yön sabit analiz yuvasıdır; savunma satırları rakibin görünür hücum süreçlerini "
                "savunma maruziyeti olarak ters yönden okur. Değerlendirme süreç hacmi, terminal şut bağlantısı, "
                "kayıp ve recovery kompozisyonuna dayanır."
            )
        else:
            cards.append(
                "Reading frame: the 12 directions are fixed analysis slots. Defensive rows read the opponent's visible attacking "
                "processes as defensive exposure. Evaluation uses process volume, shot-linked terminal states, losses, and recovery composition."
            )
        return cards

    profiles = [row for row in (c03.get("team_process_profiles") or []) if isinstance(row, dict)]
    team_ids = sorted({str(row.get("team_identity_candidate_id") or "") for row in profiles if str(row.get("team_identity_candidate_id") or "")})
    if len(team_ids) != 2:
        return []
    by_key = {
        (str(row.get("team_identity_candidate_id") or ""), str(row.get("process_family_candidate") or "")): row
        for row in profiles
    }
    families = [
        "POSITIONAL_ATTACK_CANDIDATE",
        "COUNTERATTACK_CANDIDATE",
        "SET_PIECE_ATTACK_CANDIDATE",
    ]
    cards: list[str] = []
    for team_id in team_ids:
        opp_id = team_ids[1] if team_id == team_ids[0] else team_ids[0]
        team_name = teams.get(team_id, team_id)
        opp_name = teams.get(opp_id, opp_id)
        for family in families:
            own = by_key.get((team_id, family))
            opp = by_key.get((opp_id, family))
            if not own or not opp:
                continue
            own_n = int(own.get("eligible_process_n") or 0)
            own_shot = int(own.get("shot_ending_process_n") or 0)
            own_loss = int(own.get("visible_loss_process_n") or 0)
            opp_n = int(opp.get("eligible_process_n") or 0)
            opp_shot = int(opp.get("shot_ending_process_n") or 0)
            family_name = _football_family_label(family, language)
            if language == "tr":
                cards.append(
                    f"{team_name} — {family_name}: hücum yüzeyinde {own_n} görünür süreç var; "                    f"{own_shot} tanesi şutla bağlantılı son bölüme, {own_loss} tanesi görünür top kaybına bağlanıyor. "                    f"Savunma maruziyeti tarafında {opp_name} aynı ailede {opp_n} süreç kurdu ve {opp_shot} tanesi şutla bağlantılı sona ulaştı."
                )
            else:
                cards.append(
                    f"{team_name} — {family_name}: the attacking surface contains {own_n} visible processes; "                    f"{own_shot} are linked to a shot-ending terminal segment and {own_loss} to a visible loss. "                    f"On the defensive-exposure side, {opp_name} produced {opp_n} processes in the same family, with {opp_shot} linked to a shot-ending terminal segment."
                )
    if cards:
        cards.append(
            "Okuma çerçevesi: Savunma maruziyeti rakibin görünür süreç hacmi ve şutla bağlantılı terminal bölümleri üzerinden okunur."
            if language == "tr" else
            "Reading frame: defensive exposure is read through opponent process volume and shot-linked terminal segments."
        )
    return cards


def _mechanism_visible_split_sentence(record: dict[str, Any], language: str) -> str:
    rows = [row for row in (record.get("consequence_feature_difference_candidates") or []) if isinstance(row, dict)]
    def pick(token_suffix: str):
        candidates = [row for row in rows if str(row.get("feature_token") or "").endswith(token_suffix)]
        if not candidates:
            return None
        return max(candidates, key=lambda row: (row.get("partial_order_layer_index") is not None, abs(float(row.get("descriptive_rate_delta_success_minus_failure") or 0.0))))

    same = pick("primary_consequence_candidates:SAME_TEAM_CONTINUATION_CANDIDATE")
    handover = pick("primary_consequence_candidates:OPPONENT_HANDOVER_CANDIDATE")
    if not same or not handover:
        return ""
    ss = int(same.get("success_visible_numerator") or 0)
    sd = int(same.get("success_eligible_denominator") or 0)
    sfd = int(same.get("failure_eligible_denominator") or 0)
    hd = int(handover.get("success_eligible_denominator") or 0)
    hf = int(handover.get("failure_visible_numerator") or 0)
    hfd = int(handover.get("failure_eligible_denominator") or 0)
    if sd <= 0 or sfd <= 0 or hd <= 0 or hfd <= 0:
        return ""
    if language == "tr":
        return (
            f" Görünür ayrışma: olumlu sonuçlara bağlı varyantların {ss}/{sd} tanesinde aynı takım devamı, "
            f"olumsuz sonuçlara bağlı varyantların {hf}/{hfd} tanesinde rakibe geçiş görülüyor. "
            "Bu satır aynı başlangıçtan sonra oluşan görünür sonuç ayrımını özetler."
        )
    return (
        f" Visible split: same-team continuation appears in {ss}/{sd} variants linked to positive visible outcomes, "
        f"while opponent handover appears in {hf}/{hfd} variants linked to negative visible outcomes. "
        "This line summarizes the visible outcome split after the same starting pattern."
    )



def _score_state_human(score_state: dict[str, Any] | None, language: str) -> str:
    if not isinstance(score_state, dict) or not score_state:
        return ""
    parts = []
    for team, value in score_state.items():
        try:
            score = int(value)
        except (TypeError, ValueError):
            continue
        parts.append(f"{_display_label(team)} {score}")
    if not parts:
        return ""
    return " - ".join(parts)


def _mechanism_safe_context_by_family(
    root: Path,
    full_spine: dict[str, Any],
    process_variant_payload: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    if not (
        _declared_current(full_spine, SAFE_FINDING_ADMISSION_JSON)
        and _declared_current(full_spine, VISIBLE_SEQUENCE_JSON)
    ):
        return {}
    admission = _load_json(root / SAFE_FINDING_ADMISSION_JSON)
    sequence = _load_json(root / VISIBLE_SEQUENCE_JSON)
    if not admission or not sequence:
        return {}

    handoffs = {
        str(row.get("safe_finding_handoff_candidate_id") or "").strip(): row
        for row in (sequence.get("safe_finding_handoff_candidates") or [])
        if isinstance(row, dict)
        and str(row.get("safe_finding_handoff_candidate_id") or "").strip()
    }
    decisions = {
        str(row.get("source_safe_finding_handoff_ref") or "").strip(): row
        for row in (admission.get("safe_finding_admission_decisions") or [])
        if isinstance(row, dict)
        and str(row.get("source_safe_finding_handoff_ref") or "").strip()
    }

    by_divergence: dict[str, list[dict[str, Any]]] = {}
    for handoff_id, handoff in handoffs.items():
        divergence_ref = str(
            handoff.get("source_first_supported_branch_divergence_ref") or ""
        ).strip()
        decision = decisions.get(handoff_id)
        if divergence_ref and isinstance(decision, dict):
            by_divergence.setdefault(divergence_ref, []).append(decision)

    result: dict[str, dict[str, Any]] = {}
    for family in process_variant_payload.get("observable_process_variant_families") or []:
        if not isinstance(family, dict):
            continue
        family_ref = str(
            family.get("observable_process_variant_family_id") or ""
        ).strip()
        if not family_ref:
            continue
        divergence_refs = {
            str(binding.get("source_first_supported_branch_divergence_ref") or "").strip()
            for binding in (family.get("supported_branch_divergence_bindings") or [])
            if isinstance(binding, dict)
            and str(binding.get("source_first_supported_branch_divergence_ref") or "").strip()
        }
        matched = [
            row
            for divergence_ref in divergence_refs
            for row in by_divergence.get(divergence_ref, [])
        ]
        if not matched:
            continue

        score_states: dict[str, dict[str, Any]] = {}
        process_families: list[tuple[str, ...]] = []
        context_states: Counter = Counter()
        for decision in matched:
            context = decision.get("branch_preoutcome_context_enrichment") or {}
            if not isinstance(context, dict):
                continue
            state = str(context.get("state") or "").strip()
            if state:
                context_states[state] += 1
            score_state = context.get("score_state_candidate")
            if isinstance(score_state, dict) and score_state:
                key = json.dumps(score_state, ensure_ascii=False, sort_keys=True)
                score_states[key] = score_state
            process_families.append(
                tuple(
                    str(value)
                    for value in (context.get("provider_process_family_candidates") or [])
                    if str(value)
                )
            )

        nonempty_process = [value for value in process_families if value]
        unique_process = sorted(set(nonempty_process))
        result[family_ref] = {
            "safe_finding_match_count": len(matched),
            "score_state_consensus": len(score_states) == 1,
            "score_state_candidate": (
                next(iter(score_states.values())) if len(score_states) == 1 else None
            ),
            "provider_process_family_consensus": len(unique_process) == 1,
            "provider_process_family_candidates": (
                list(unique_process[0]) if len(unique_process) == 1 else []
            ),
            "provider_process_context_partial_count": (
                len(process_families) - len(nonempty_process)
            ),
            "preoutcome_context_state_counts": dict(sorted(context_states.items())),
            "emit_decision_count": sum(
                str(row.get("decision") or "").upper() == "EMIT" for row in matched
            ),
            "claim_output_allowed_count": sum(
                row.get("claim_output_allowed") is True for row in matched
            ),
            "context_is_preoutcome_only": True,
            "creates_new_evidence": False,
            "creates_independent_support": False,
            "can_change_shortlist_selection": False,
            "can_change_safe_finding_decision": False,
            "can_authorize_emit": False,
        }
    return result



def _player_function_profiles_by_actor(rich: dict[str, Any]) -> dict[str, dict[str, Any]]:
    c02 = (rich.get("constructs") or {}).get("C02") or {}
    return {
        str(row.get("actor_identity_candidate_id") or "").strip(): row
        for row in (c02.get("player_function_profiles") or [])
        if isinstance(row, dict)
        and str(row.get("actor_identity_candidate_id") or "").strip()
    }


def _player_profile_metric_values(profile: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    dimensions = profile.get("function_dimensions") or {}
    for value in dimensions.values():
        if not isinstance(value, list):
            continue
        for row in value:
            if not isinstance(row, dict):
                continue
            key = str(row.get("metric_key") or "").strip()
            raw = row.get("raw_value")
            if not key or raw in (None, "", "-"):
                continue
            result[key] = raw
    return result


def _human_number(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        text = f"{value:.2f}".rstrip("0").rstrip(".")
        return text
    return str(value)


def _actor_aggregate_context_sentence(
    actor_ref: str | None,
    actor_locator: dict[str, Any] | None,
    profiles_by_actor: dict[str, dict[str, Any]],
    validated_actor_labels: dict[str, str],
    language: str,
) -> str:
    if not actor_ref or not actor_locator:
        return ""
    profile = profiles_by_actor.get(actor_ref)
    if not isinstance(profile, dict):
        return ""
    label = validated_actor_labels.get(actor_ref)
    if not label:
        return ""
    metrics = _player_profile_metric_values(profile)

    preferred = [
        ("progressive_passes", "progressive pass", "progressive passes"),
        ("progressive_passes_accurate", "isabetli progressive pass", "accurate progressive passes"),
        ("final_third_entries", "son üçte bir girişi", "final-third entries"),
        ("passes_into_the_penalty_box", "ceza sahasına pas", "passes into the box"),
        ("actions_in_opponent_s_box", "rakip ceza sahası aksiyonu", "opponent-box actions"),
        ("chances_created", "yaratılan şans", "chances created"),
        ("xa_expected_assists", "xA", "xA"),
        ("shots", "şut", "shots"),
        ("shots_on_target", "isabetli şut", "shots on target"),
        ("goals", "gol", "goals"),
        ("xg_expected_goals", "xG", "xG"),
        ("lost_balls", "top kaybı", "ball losses"),
        ("ball_recoveries", "top kazanımı", "ball recoveries"),
        ("shots_faced", "karşılaşılan şut", "shots faced"),
        ("shots_on_target_faced", "karşılaşılan isabetli şut", "shots on target faced"),
        ("goals_conceded", "yenilen gol", "goals conceded"),
    ]
    bits: list[str] = []
    for key, tr_label, en_label in preferred:
        if key not in metrics:
            continue
        label_text = tr_label if language == "tr" else en_label
        bits.append(f"{label_text}={_human_number(metrics[key])}")
        if len(bits) >= 6:
            break

    process_counts = (
        (profile.get("function_dimensions") or {})
        .get("PROCESS", {})
        .get("process_participation_counts", {})
    )
    process_bit = ""
    if isinstance(process_counts, dict) and process_counts:
        family, count = max(
            process_counts.items(),
            key=lambda item: (int(item[1] or 0), str(item[0])),
        )
        if int(count or 0) > 0:
            family_label = _football_family_label(family, language)
            process_bit = (
                f" En yüksek görünür süreç katılımı: {family_label} {int(count)}."
                if language == "tr"
                else f" Highest visible process participation: {family_label} {int(count)}."
            )

    if not bits and not process_bit:
        return ""
    if language == "tr":
        metric_text = ", ".join(bits)
        return (
            f" Oyuncu inceleme odağı: {label}. "
            + (f"XLSX maç toplamı bağlamı: {metric_text}." if metric_text else "")
            + process_bit
            + " Bu aggregate profil yalnız aynı oyuncunun maç-içi işlev bağlamını taşır; mekanizma aksiyon kimliği, oyuncu kalite hükmü ve nedensel katkı için kullanıma kapalıdır."
        )
    metric_text = ", ".join(bits)
    return (
        f" Player review focus: {label}. "
        + (f"XLSX match-total context: {metric_text}." if metric_text else "")
        + process_bit
        + " This aggregate profile is used only as match-local functional context for the same player; action identity, player-quality judgment, and causal contribution remain outside its allowed scope."
    )


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
    process_variant_payload = (
        _load_json(root / PROCESS_VARIANT_JSON)
        if _declared_current(full_spine, PROCESS_VARIANT_JSON)
        else {}
    )
    process_participation_payload = (
        _load_json(root / PROCESS_PARTICIPATION_JSON)
        if _declared_current(full_spine, PROCESS_PARTICIPATION_JSON)
        else {}
    )
    variant_feature_challenge_payload = (
        _load_json(root / VARIANT_FEATURE_CHALLENGE_JSON)
        if _declared_current(full_spine, VARIANT_FEATURE_CHALLENGE_JSON)
        else {}
    )
    rich_payload = (
        _load_json(root / RICH_MULTIFORMAT_JSON)
        if _declared_current(full_spine, RICH_MULTIFORMAT_JSON)
        else {}
    )
    player_profiles_by_actor = _player_function_profiles_by_actor(rich_payload)
    validated_actor_labels = _human_validated_actor_labels(identity)
    shortlist = build_mechanism_story_review_shortlist(
        payload,
        analyst_output_claim_payload=analyst_output or None,
        process_variant_payload=process_variant_payload or None,
        process_participation_payload=process_participation_payload or None,
        variant_feature_challenge_payload=variant_feature_challenge_payload or None,
        limit=5,
    )
    teams = _human_team_labels(identity)
    safe_context_by_family = _mechanism_safe_context_by_family(
        root,
        full_spine,
        process_variant_payload,
    )
    source_records = {
        str(record.get("grammar_stable_variant_feature_delta_id") or ""): record
        for record in (payload.get("grammar_stable_variant_feature_delta_records") or [])
        if isinstance(record, dict)
    }
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
        support_state = str(row.get("review_support_state") or "")
        single_episode_only = support_state.startswith("SINGLE_EPISODE_")
        source_record = source_records.get(str(row.get("source_mechanism_review_ref") or ""), {})
        actor_locator = _select_actor_locator(source_record)
        actor_ref = _focus_actor_ref(actor_locator)
        actor_context_sentence = _actor_aggregate_context_sentence(
            actor_ref,
            actor_locator,
            player_profiles_by_actor,
            validated_actor_labels,
            language,
        )
        safe_context = safe_context_by_family.get(
            str(row.get("source_process_variant_family_ref") or ""),
            {},
        )
        if language == "tr":
            prefix = "Sınırlı karşılaştırma" if single_episode_only else "İnceleme noktası"
            football = (
                f"{prefix} {idx}: {team}, {periods}. {grammar} bağlantısı maçın {spread} farklı bölümünde tekrar görülüyor. "
                "Bu bağlantının karşılaştırılabilir varyantları hem olumlu hem olumsuz görünür sonuçlara gidiyor. "
                "Analist için asıl soru, aynı başlangıçtan sonra hangi aksiyon veya bağlam değişiminin sonuçları ayırdığı."
            )
            if single_episode_only:
                football += " Bu karşılaştırma tek görünür maç bölümünde yoğunlaştığı için ana mekanizma olarak yorumlanmamalıdır."
            else:
                football += _mechanism_visible_split_sentence(source_record, language)
            if safe_context:
                if safe_context.get("score_state_consensus") is True:
                    score_text = _score_state_human(
                        safe_context.get("score_state_candidate"),
                        language,
                    )
                    if score_text:
                        football += (
                            f" Skor bağlamı: bu mekanizma ailesiyle bağlanan Safe Finding örneklerinde ortak görünür skor durumu {score_text}."
                        )
                if safe_context.get("provider_process_family_consensus") is True:
                    families = [
                        _football_family_label(value, language)
                        for value in (
                            safe_context.get("provider_process_family_candidates") or []
                        )
                    ]
                    if families:
                        football += (
                            f" Branch öncesi süreç bağlamı: ortak görünür süreç {', '.join(families)}."
                        )
                partial_n = int(
                    safe_context.get("provider_process_context_partial_count") or 0
                )
                if partial_n:
                    football += (
                        f" {partial_n} bağlı Safe Finding örneğinde provider süreç bağlamı tekil çözülemedi; bu örnekler kısmi bağlam olarak korunuyor."
                    )
            football += actor_context_sentence
            context_state = str(row.get("process_context_binding_state") or "")
            context_counts = dict(row.get("process_family_episode_presence_counts") or {})
            if context_state == "UNAMBIGUOUS_SINGLE_PROCESS_FAMILY_CONTEXT":
                family = _football_family_label(row.get("single_process_family_candidate"), language)
                football += (
                    f" Kaynak-bağlı süreç bağlamı: bu varyant ailesinin görünür bölümleri {family} bağlamına bağlanıyor; "
                    "bu bağlam varyant ailesinin kaynak-bağlı süreç kapsamını tanımlar."
                )
            elif context_counts:
                context_bits = ", ".join(
                    f"{_football_family_label(key, language)} {value}/{int(row.get('process_context_visible_episode_count') or 0)} bölüm"
                    for key, value in sorted(context_counts.items())
                )
                football += (
                    f" Kaynak-bağlı süreç dağılımı: {context_bits}. "
                    "Mekanizma kartı bu dağılımı çoklu süreç bağlamı olarak korur."
                )
            challenge_n = int(row.get("mechanism_challenge_record_count") or 0)
            challenge_note = ""
            if challenge_n:
                challenge_note = (
                    f" Bu aday için {challenge_n} kaynak-bağlı challenge kaydı; örneklem bileşimi, rakip davranışı/skor durumu, "
                    "gözlem/provider semantiği, çözülmemiş bağımlılık ve sonuç ufku gibi alternatif açıklamaları açık tutuyor. "
                    "Bu koşullardan biri görünür ayrışmayı ortadan kaldırırsa mekanizma yorumu geri çekilmeli veya nitelendirilmelidir."
                )
            evidence = (
                f"Kanıt notu: karşılaştırma yüzeyinde {resolved} çözümlenmiş varyant kaydı var; "
                f"{success} olumlu ve {failure} olumsuz görünür sonuca bağlı. "
                f"Kanıt örgüsü {clusters} ayrı görünür aksiyon kümesine yayılıyor. "
                "Yorum kapsamı maç-içi varyant ayrışması ve kaynak-bağlı süreç bağlamıdır."
                + challenge_note
            )
        else:
            prefix = "Limited comparison" if single_episode_only else "Review point"
            football = (
                f"{prefix} {idx}: {team}, {periods}. The {grammar} connection recurs across {spread} distinct match segments. "
                "Comparable variants of the same visible start lead to both positive and negative visible outcomes. "
                "The analyst question is which subsequent action or context change separates those outcomes."
            )
            if single_episode_only:
                football += " This comparison is concentrated in one visible match segment and should not be treated as a main mechanism."
            else:
                football += _mechanism_visible_split_sentence(source_record, language)
            if safe_context:
                if safe_context.get("score_state_consensus") is True:
                    score_text = _score_state_human(
                        safe_context.get("score_state_candidate"),
                        language,
                    )
                    if score_text:
                        football += (
                            f" Score context: Safe Finding examples bound to this mechanism family share the visible score state {score_text}."
                        )
                if safe_context.get("provider_process_family_consensus") is True:
                    families = [
                        _football_family_label(value, language)
                        for value in (
                            safe_context.get("provider_process_family_candidates") or []
                        )
                    ]
                    if families:
                        football += (
                            f" Pre-branch process context: the common visible process is {', '.join(families)}."
                        )
                partial_n = int(
                    safe_context.get("provider_process_context_partial_count") or 0
                )
                if partial_n:
                    football += (
                        f" {partial_n} bound Safe Finding examples do not have a unique provider-process context and remain partial."
                    )
            football += actor_context_sentence
            context_state = str(row.get("process_context_binding_state") or "")
            context_counts = dict(row.get("process_family_episode_presence_counts") or {})
            if context_state == "UNAMBIGUOUS_SINGLE_PROCESS_FAMILY_CONTEXT":
                family = _football_family_label(row.get("single_process_family_candidate"), language)
                football += (
                    f" Source-bound process context: the visible segments of this variant family bind to {family}; "
                    "this context defines the source-bound process scope of the variant family."
                )
            elif context_counts:
                context_bits = ", ".join(
                    f"{_football_family_label(key, language)} {value}/{int(row.get('process_context_visible_episode_count') or 0)} segments"
                    for key, value in sorted(context_counts.items())
                )
                football += (
                    f" Source-bound process distribution: {context_bits}. "
                    "The mechanism card preserves this as a multi-process context."
                )
            challenge_n = int(row.get("mechanism_challenge_record_count") or 0)
            challenge_note = ""
            if challenge_n:
                challenge_note = (
                    f" This candidate carries {challenge_n} source-bound challenge records that keep sample composition, opponent behaviour/score state, "
                    "observation/provider semantics, unresolved dependency and consequence-horizon definitions open as alternative explanations. "
                    "If those conditions remove the visible split, the mechanism interpretation must be withdrawn or qualified."
                )
            evidence = (
                f"Evidence note: the comparison surface contains {resolved} resolved variant records; "
                f"{success} are linked to positive and {failure} to negative visible outcomes. "
                f"The evidence structure spans {clusters} distinct visible action clusters. "
                "Interpretation is scoped to match-local variant separation and source-bound process context."
                + challenge_note
            )
        process_label = (
            _football_family_label(row.get("single_process_family_candidate"), language)
            if str(row.get("process_context_binding_state") or "") == "UNAMBIGUOUS_SINGLE_PROCESS_FAMILY_CONTEXT"
            else ("çoklu/çözülmemiş süreç bağlamı" if language == "tr" else "multi/unresolved process context")
        )
        consequence_layer = source_record.get("first_supported_consequence_difference_layer_candidate")
        context_layer = source_record.get("first_supported_context_difference_layer_candidate")
        challenge_reasons = [
            str(value)
            for value in (row.get("mechanism_challenge_reason_codes") or [])
            if str(value)
        ]
        if language == "tr":
            card = (
                f"MEKANİZMA KARTI {idx} | TAKIM={team} | DÖNEM={periods} | "
                f"TRACE={grammar} | PROCESS={process_label} | "
                f"VARYANT={success} olumlu / {failure} olumsuz / {resolved} çözümlenmiş | "
                f"İLK GÖRÜNÜR AYRIŞMA=context L{context_layer}, consequence L{consequence_layer} | "
                f"YAYILIM={spread} bölüm, {clusters} occurrence-disjoint küme | "
                f"COUNTEREVIDENCE={','.join(challenge_reasons) if challenge_reasons else 'açık challenge kaydı yok'} | "
                "CLAIM=maç-içi görünür varyant/mekanizma adayı; neden, taktik plan veya üstünlük truth değildir."
            )
        else:
            card = (
                f"MECHANISM CARD {idx} | TEAM={team} | PERIOD={periods} | "
                f"TRACE={grammar} | PROCESS={process_label} | "
                f"VARIANT={success} positive / {failure} negative / {resolved} resolved | "
                f"FIRST VISIBLE DIVERGENCE=context L{context_layer}, consequence L{consequence_layer} | "
                f"SPREAD={spread} segments, {clusters} occurrence-disjoint clusters | "
                f"COUNTEREVIDENCE={','.join(challenge_reasons) if challenge_reasons else 'no explicit challenge record'} | "
                "CLAIM=match-local visible variant/mechanism candidate; not causal, tactical-plan, or superiority truth."
            )
        cards.extend([card, football, evidence])
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
                "Bu association oyuncu/ikiliyi söz konusu hücumların varyant incelemesinde öne çıkarır."
            )
            evidence = (
                f"Kanıt notu: {eligible_n} örneğin {positive_k} tanesinde görünür şut bağlantısı var; "
                f"{unresolved_u} örnek unresolved outcome statüsünde. Oyuncu/ikili bu hücum tipinde "
                f"{eligible_spread} farklı maç bölümünde görülüyor; şut bağlantısı {positive_spread} farklı bölümde görülüyor"
            )
            if isinstance(lift, (int, float)):
                evidence += f"; maç içi betimleyici oran karşılaştırması={float(lift):.2f}x"
            evidence += ". Bu profil maç-içi betimleyici association yüzeyidir ve analyst-review önceliği üretir."
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
                " This match-local association signal prioritizes the player or pair for variant review."
            )
            evidence = (
                f"Evidence note: {positive_k} of {eligible_n} examples carry a visible shot link; "
                f"{unresolved_u} target outcomes remain unresolved. The player/pair appears across "
                f"{eligible_spread} distinct match segments, with a shot link in {positive_spread} of them"
            )
            if isinstance(lift, (int, float)):
                evidence += f"; match-local descriptive ratio={float(lift):.2f}x"
            evidence += ". This profile is a match-local descriptive association surface for analyst review."
        cards.extend([football, evidence])
    return cards


def _human_sequence_information_cards(rich: dict[str, Any], identity: dict[str, Any], language: str) -> list[str]:
    c03 = (rich.get("constructs") or {}).get("C03") or {}
    info = c03.get("process_sequence_information") or {}
    profiles = [row for row in (info.get("team_process_family_profiles") or []) if isinstance(row, dict)]
    if not profiles:
        return []
    teams = _human_team_labels(identity)
    cards: list[str] = []
    for row in sorted(profiles, key=lambda x: (-int(x.get("eligible_process_signature_n") or 0), str(x.get("team_identity_candidate_id") or ""), str(x.get("process_family_candidate") or "")))[:8]:
        team_id = str(row.get("team_identity_candidate_id") or "UNKNOWN")
        team = teams.get(team_id, team_id)
        family = str(row.get("process_family_candidate") or "UNKNOWN")
        n = int(row.get("eligible_process_signature_n") or 0)
        variants = int(row.get("distinct_trace_variant_n") or 0)
        transitions = int(row.get("transition_count") or 0)
        duration = (row.get("process_duration_profile") or {}).get("median_process_interval_seconds_candidate")
        top = (row.get("trace_variant_counts") or [])[:1]
        top_text = str(top[0].get("trace_variant")) if top and isinstance(top[0], dict) else "UNKNOWN"
        top_n = int(top[0].get("process_n") or 0) if top and isinstance(top[0], dict) else 0
        if language == "tr":
            text = f"{team} — {family}: {n} görünür süreç, {variants} trace varyantı, {transitions} ardışık layer geçişi."
            if isinstance(duration, (int, float)):
                text += f" Medyan süreç aralığı {float(duration):.1f} sn."
            if top_n:
                text += f" En sık görünür trace: {top_text} ({top_n})."
            text += " Bu profil görünür süreç çeşitliliğini ve geçiş dağılımını betimler; taktik niyet veya nedensellik çıkarmaz."
        else:
            text = f"{team} — {family}: {n} visible processes, {variants} trace variants, {transitions} ordered layer transitions."
            if isinstance(duration, (int, float)):
                text += f" Median process interval {float(duration):.1f}s."
            if top_n:
                text += f" Most frequent visible trace: {top_text} ({top_n})."
            text += " This profile describes visible process diversity and transition distribution within a match-local descriptive claim scope; tactical-intent and causal constructs require their own admitted evidence."
        cards.append(text)
    return cards


def build_human_analyst_report_tr(output_root: str | Path, full_spine: dict[str, Any]) -> str:
    root = Path(output_root)
    rich_current = _rich_surface_current(full_spine)
    rich = full_spine.get("rich_multiformat_analysis_lattice") if rich_current else {}
    rich = rich if isinstance(rich, dict) else {}
    identity = _load_json(root / IDENTITY_JSON) if _declared_current(full_spine, IDENTITY_JSON) else {}
    c02_cards = _human_c02_cards(rich, "tr") if rich_current else []
    team_cards = _human_team_process_cards(rich, identity, "tr") if rich_current else []
    contest_cards = _human_process_contest_cards(rich, identity, "tr") if rich_current else []
    sequence_cards = _human_sequence_information_cards(rich, identity, "tr") if rich_current else []
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
    lines.extend(["", "[2] SEQUENCE / PROCESS INTELLIGENCE"])
    if sequence_cards:
        lines.extend(f"- {line}" for line in sequence_cards)
    else:
        lines.append("- Bu maçta sequence/process information profili üretilemedi.")
    lines.extend(["", "[3] OYUNCU / İKİLİ × HÜCUM SONUCU"])
    if c02_cards:
        lines.extend(f"- {line}" for line in c02_cards)
    else:
        lines.append("- Bu maçta bu başlık için güvenli biçimde raporlanabilir current-run aday yok.")
    lines.extend(["", "[4] 12 YÖNLÜ POSTMATCH — 6 FAZ × 2 TAKIM"])
    if contest_cards:
        lines.extend(f"- {line}" for line in contest_cards)
    else:
        lines.append("- Bu maçta iki takım için karşılaştırılabilir süreç çarpışma yüzeyi üretilemedi.")
    lines.extend(["", "[5] AYNI HÜCUM BAŞLANGICININ AYRIŞAN SONUÇLARI"])
    if mechanism_cards:
        lines.extend(f"- {line}" for line in mechanism_cards)
    else:
        lines.append("- Bu maçta güvenli biçimde kısa listeye alınmış mekanizma adayı yok.")
    lines.extend([
        "",
        "[6] ANALİST OKUMA ÇERÇEVESİ",
        "- Oyuncu ve ikili yüzeyi, görünür süreç katılımı ile sonuç bağlantısını maç-içi association olarak sunar.",
        "- Hedef sonuç etiketi çözülmeyen süreçler unresolved outcome statüsünde izlenir.",
        "- Sıralama, analistin hangi örneklere önce bakacağını belirleyen maç-içi dikkat sırasıdır.",
        "- Tekrarlayan aksiyon grameri recurrence ve varyant incelemesi için kullanılır.",
        "- Fiziksel yapı ve geometri constructları, ilgili observation capability admit edildiğinde raporlanır.",
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
    contest_cards = _human_process_contest_cards(rich, identity, "en") if rich_current else []
    sequence_cards = _human_sequence_information_cards(rich, identity, "en") if rich_current else []
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
    lines.extend(["", "[2] SEQUENCE / PROCESS INTELLIGENCE"])
    if sequence_cards:
        lines.extend(f"- {line}" for line in sequence_cards)
    else:
        lines.append("- No sequence/process information profile is available for this run.")
    lines.extend(["", "[3] PLAYER / PAIR × ATTACK OUTCOME"])
    if c02_cards:
        lines.extend(f"- {line}" for line in c02_cards)
    else:
        lines.append("- No current-run candidate can be reported safely under this heading.")
    lines.extend(["", "[4] 12-DIRECTION POSTMATCH — 6 PHASES × 2 TEAMS"])
    if contest_cards:
        lines.extend(f"- {line}" for line in contest_cards)
    else:
        lines.append("- No comparable two-team process contest surface is available for this run.")
    lines.extend(["", "[5] DIVERGING OUTCOMES FROM THE SAME ATTACKING START"])
    if mechanism_cards:
        lines.extend(f"- {line}" for line in mechanism_cards)
    else:
        lines.append("- No mechanism candidate was safely shortlisted in this run.")
    lines.extend([
        "",
        "[6] ANALYST READING FRAME",
        "- Player and pair surfaces present visible process involvement and outcome linkage as match-local associations.",
        "- Processes with unresolved target outcomes remain in the unresolved-outcome state.",
        "- Ranking is a match-local analyst-attention order.",
        "- Repeated visible action grammar is used for recurrence and variant review.",
        "- Physical-structure and geometry constructs are reported when their required observation capability is admitted.",
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
            f"game_state_context_status={(rich.get('game_state_context') or {}).get('status')}",
            f"game_state_goal_observation_count={(rich.get('game_state_context') or {}).get('goal_observation_count')}",
            f"game_state_segment_count={len((rich.get('game_state_context') or {}).get('score_state_segments') or [])}",
            f"game_state_process_mix_context_status={(rich.get('game_state_process_mix_context') or {}).get('status')}",
            f"game_state_process_mix_profile_count={(rich.get('game_state_process_mix_context') or {}).get('profile_count')}",
            f"recovery_next_process_context_status={(rich.get('recovery_next_process_context') or {}).get('status')}",
            f"recovery_next_process_context_row_count={(rich.get('recovery_next_process_context') or {}).get('recovery_context_row_count')}",
            f"recovery_next_process_family_counts={json.dumps((rich.get('recovery_next_process_context') or {}).get('next_visible_process_family_counts') or {}, ensure_ascii=False, sort_keys=True)}",
            f"loss_next_opponent_process_context_status={(rich.get('loss_next_opponent_process_context') or {}).get('status')}",
            f"loss_next_opponent_process_family_counts={json.dumps((rich.get('loss_next_opponent_process_context') or {}).get('next_opponent_process_family_counts') or {}, ensure_ascii=False, sort_keys=True)}",
            f"goalkeeper_restart_consequence_context_status={(rich.get('goalkeeper_restart_consequence_context') or {}).get('status')}",
            f"goalkeeper_restart_context_row_count={(rich.get('goalkeeper_restart_consequence_context') or {}).get('goalkeeper_restart_context_row_count')}",
            f"goalkeeper_restart_bucket_counts={json.dumps((rich.get('goalkeeper_restart_consequence_context') or {}).get('provider_distance_bucket_counts') or {}, ensure_ascii=False, sort_keys=True)}",
            f"goalkeeper_restart_primary_consequence_counts={json.dumps((rich.get('goalkeeper_restart_consequence_context') or {}).get('primary_consequence_counts') or {}, ensure_ascii=False, sort_keys=True)}",
            f"goalkeeper_restart_next_process_family_counts={json.dumps((rich.get('goalkeeper_restart_consequence_context') or {}).get('next_visible_process_family_counts') or {}, ensure_ascii=False, sort_keys=True)}",
            f"set_piece_process_consequence_context_status={(rich.get('set_piece_process_consequence_context') or {}).get('status')}",
            f"set_piece_process_context_row_count={(rich.get('set_piece_process_consequence_context') or {}).get('set_piece_process_context_row_count')}",
            f"set_piece_primary_consequence_counts={json.dumps((rich.get('set_piece_process_consequence_context') or {}).get('primary_consequence_counts') or {}, ensure_ascii=False, sort_keys=True)}",
            f"set_piece_post_process_team_state_counts={json.dumps((rich.get('set_piece_process_consequence_context') or {}).get('post_set_piece_first_visible_team_state_counts') or {}, ensure_ascii=False, sort_keys=True)}",
            f"counterattack_next_process_context_status={(rich.get('counterattack_next_process_context') or {}).get('status')}",
            f"counterattack_next_process_family_counts={json.dumps((rich.get('counterattack_next_process_context') or {}).get('next_visible_process_family_counts') or {}, ensure_ascii=False, sort_keys=True)}",
            f"counter_to_positional_successor_candidate_count={(rich.get('counterattack_next_process_context') or {}).get('counter_to_positional_successor_candidate_count')}",
            "game_state_context_is_tactical_truth=false",
            "game_state_context_is_causal_truth=false",
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
            f"C01_access_creation_terminal_profile_count={c01.get('access_creation_terminal_profile_count')}",
            f"C01_access_terminal_both_observed_count={c01.get('access_creation_terminal_profiles_with_access_and_terminal_count')}",
            "C01_access_creation_terminal_conversion_rate_emitted=false",
            f"C01_review_reason={c01.get('review_reason')}",
            "phase_state_candidates_are_phase_truth=false",
            f"C02_construct_status={c02.get('status')}",
            f"C02_argument_candidate_count={c02.get('argument_candidate_count')}",
            f"C02_xlsx_actor_binding_count={c02.get('xlsx_actor_binding_count')}",
            f"C02_player_function_profile_count={c02.get('player_function_profile_count')}",
            f"C02_player_function_profile_dimensions={c02.get('player_function_profile_dimensions')}",
            "C02_player_function_profile_is_quality_score=false",
            "C02_player_function_profile_is_tactical_role_truth=false",
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
                "(target outcome unresolved); "
                f"coverage={((candidate.get('observation_capability_coverage_profile') or {}).get('coverage_state') or 'UNRESOLVED')}; "
                f"negative_claim={((candidate.get('observation_capability_coverage_profile') or {}).get('negative_claim_admission_state') or 'UNRESOLVED')}; "
                f"XLSX oyuncu bağlamı eşleşen kişi={int(candidate.get('xlsx_enriched_actor_count') or 0)}. "
                "Bu kayıt, admitted process/occurrence incelemesine öncelik veren maç-içi görünür association adayıdır; kapsamı match-local review priority olarak tanımlıdır."
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
        "Takim/oyuncu aday dagilimlari current-invocation attribution ve aggregate-context yuzeyini betimler.",
        "",
        "[9] SCOPE AUTHORITY",
        "Fiziksel-yapi, geometri, hareket, niyet ve nedensel construct aileleri kendi admitted observation/evidence contractlariyla uretilir.",
        "",
        "[10] CURRENT PRODUCT SCOPE",
        "CSV/XML occurrence ve XLSX aggregate yuzeyleri ayni run'da dependency-aware lineage ile birlikte tasinir.",
        "C01 ilk construct vertical slice'tir; progression output authority occurrence-level progression admission durumunu izler.",
        "Phase/state etiketleri activity-candidate authority tasir.",
        "MICRO/MEZZO/MACRO evidence-routing lattice'i macro yorumlari mikro/mezo evidence lineage'ina baglar.",
        "Player/GK/team gorunumleri candidate-identity ve aggregate-context authority tasir; identity/quality yorumlari validated registry ve construct contractlarini kullanir.",
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
    provenance = _current_run_provenance_envelope(root, full_spine, entries)
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
        "current_run_provenance_envelope": provenance,
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
