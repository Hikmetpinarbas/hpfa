from __future__ import annotations

import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

try:
    from .analyst_mechanism_review import (
        _focus_actor_ref,
        _select_actor_locator,
        build_mechanism_review_lines,
    )
    from .mechanism_story_review_selector import build_mechanism_story_review_shortlist
except ImportError:  # compatibility for direct src-path test/runtime imports
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

try:
    from .presentation_view_model import build_presentation_view_model, render_professional_html
except ImportError:  # compatibility for direct src-path test/runtime imports
    from presentation_view_model import build_presentation_view_model, render_professional_html

ANALYST_REPORT = "HPFA_ANALYST_REPORT.txt"
ANALYST_REPORT_TR = "HPFA_ANALYST_REPORT_TR.txt"
ANALYST_REPORT_EN = "HPFA_ANALYST_REPORT_EN.txt"
MECHANISM_CARDS_GRAPH_JSON = "HPFA_MECHANISM_CARDS_GRAPH_READY.json"
PRESENTATION_VIEW_MODEL_JSON = "HPFA_PRESENTATION_VIEW_MODEL.json"
PROFESSIONAL_REPORT_HTML = "HPFA_PROFESSIONAL_REPORT.html"
BUNDLE_MANIFEST = "HPFA_ACTIVE_MATCH_BUNDLE_MANIFEST.json"
BUNDLE_ZIP = "HPFA_ACTIVE_MATCH_BUNDLE.zip"
FOOTBALL_DELIVERY_ZIP = "HPFA_FOOTBALL_DELIVERY.zip"
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
PROCESS_ACTOR_CONCENTRATION_JSON = "process_actor_participation_concentration_projection_v1.json"


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
    episode_lane = full_spine.get("episode_lane")
    product_code_root = (
        episode_lane.get("product_code_root")
        if isinstance(episode_lane, dict)
        else None
    )
    exact_head = _git_head(product_code_root) or _git_head(full_spine.get("execution_root"))
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


def _representative_entities(
    rich: dict[str, Any],
    identity: dict[str, Any],
    limit: int = 8,
) -> list[str]:
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
        name = _human_match_local_entity_label(rich, identity, row)
        if not name:
            continue
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


def _football_family_key(value: Any) -> str:
    key = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    key = key.replace("_CANDIDATE", "")
    return {
        "POSITIONAL_ATTACKS": "POSITIONAL_ATTACK",
        "COUNTERATTACKS": "COUNTERATTACK",
        "SET_PIECE_ATTACKS": "SET_PIECE_ATTACK",
        "TRANSITION_ATTACKS": "TRANSITION_ATTACK",
    }.get(key, key)


def _football_family_label(value: Any, language: str) -> str:
    key = _football_family_key(value)
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


def _human_admitted_actor_labels(identity: dict[str, Any]) -> dict[str, str]:
    """Human-facing labels may use validated global identity or source-bound match-local actor identity."""
    result: dict[str, str] = {}
    for row in identity.get("actor_identity_candidates") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("decision_state") or "") != "ACTOR_IDENTITY_CANDIDATE_BOUND":
            continue
        global_validated = row.get("validated_player_identity") is True
        supporting_atoms = [
            str(value) for value in (row.get("supporting_evidence_atom_ids") or [])
            if str(value)
        ]
        match_local_admitted = (
            str(row.get("identity_scope") or "") == "MATCH_LOCAL_CANDIDATE_ONLY"
            and row.get("global_identity_claim_allowed") is False
            and bool(str(row.get("team_identity_candidate_id") or "").strip())
            and bool(supporting_atoms)
        )
        if not global_validated and not match_local_admitted:
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


def _xlsx_row_actor_identity_map(rich: dict[str, Any]) -> dict[str, str]:
    c02 = (rich.get("constructs") or {}).get("C02") or {}
    candidates: dict[str, set[str]] = {}
    for row in (c02.get("player_function_profiles") or []):
        if not isinstance(row, dict):
            continue
        row_ref = str(row.get("xlsx_row_projection_id") or "").strip()
        actor_ref = str(row.get("actor_identity_candidate_id") or "").strip()
        if row_ref and actor_ref:
            candidates.setdefault(row_ref, set()).add(actor_ref)
    return {
        row_ref: next(iter(actor_refs))
        for row_ref, actor_refs in candidates.items()
        if len(actor_refs) == 1
    }


def _human_match_local_entity_label(
    rich: dict[str, Any],
    identity: dict[str, Any],
    row: dict[str, Any],
) -> str | None:
    """Resolve human entity labels through match-local identity owners; never raw XLSX player labels."""
    row_ref = str(row.get("row_projection_id") or "").strip()
    actor_ref = _xlsx_row_actor_identity_map(rich).get(row_ref)
    if actor_ref:
        return _human_admitted_actor_labels(identity).get(actor_ref)

    if row.get("player_candidate") not in (None, "") or row.get("player_raw_candidate") not in (None, ""):
        return None

    raw_team = row.get("team_candidate") or row.get("team_raw_candidate")
    if raw_team in (None, ""):
        return None
    raw_key = _display_label(raw_team).casefold()
    team_labels = _human_team_labels(identity)
    for candidate in (identity.get("team_identity_candidates") or []):
        if not isinstance(candidate, dict):
            continue
        team_ref = str(candidate.get("team_identity_candidate_id") or "").strip()
        if not team_ref:
            continue
        aliases = list(candidate.get("team_aliases_raw") or [])
        normalized = candidate.get("team_normalized_key")
        if normalized not in (None, ""):
            aliases.append(normalized)
        if any(_display_label(alias).casefold() == raw_key for alias in aliases):
            return team_labels.get(team_ref)
    return None


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


def _variant_context_human(value: Any, language: str) -> str:
    key = str(value or "UNKNOWN").strip().upper()
    tr = {
        "SHOT_LINKED": "şut bağlantılı varyant",
        "LOSS_LINKED": "kayıp bağlantılı varyant",
        "RECOVERY_LINKED": "recovery bağlantılı varyant",
        "SHOT_AND_LOSS_VISIBLE": "şut + kayıp bağlantılı varyant",
        "OTHER_VISIBLE": "diğer görünür varyant",
        "UNKNOWN": "bağlamı çözümlenmemiş varyant",
    }
    en = {
        "SHOT_LINKED": "shot-linked variant",
        "LOSS_LINKED": "loss-linked variant",
        "RECOVERY_LINKED": "recovery-linked variant",
        "SHOT_AND_LOSS_VISIBLE": "shot + loss-linked variant",
        "OTHER_VISIBLE": "other visible variant",
        "UNKNOWN": "context-unresolved variant",
    }
    table = tr if language == "tr" else en
    return table.get(key, key.replace("_", " ").lower())


def _grammar_token_human(value: Any, language: str) -> str:
    token = str(value or "").strip()
    if not token:
        return "katman yok" if language == "tr" else "no layer"
    return _grammar_human([token], language)


def _human_team_process_cards(rich: dict[str, Any], identity: dict[str, Any], language: str) -> list[str]:
    c03 = (rich.get("constructs") or {}).get("C03") or {}
    profiles = [row for row in (c03.get("team_process_profiles") or []) if isinstance(row, dict)]
    if not profiles:
        return []
    teams = _human_team_labels(identity)
    actors = _human_admitted_actor_labels(identity)
    by_team: dict[str, dict[str, Any]] = {}
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
                "actor_location_process": 0,
                "actor_location_layers": 0,
                "pass_only_location_excluded": 0,
                "actor_location_actor_presence": {},
                "actor_location_actor_anchor_observations": {},
                "actor_location_actor_consequence_context": {},
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
        actor_location = row.get("visible_actor_location_participation_profile")
        if isinstance(actor_location, dict):
            bucket["actor_location_process"] += int(actor_location.get("actor_location_observable_process_n") or 0)
            bucket["actor_location_layers"] += int(actor_location.get("eligible_location_temporal_layer_n") or 0)
            bucket["pass_only_location_excluded"] += int(actor_location.get("pass_only_temporal_layer_excluded_n") or 0)
            for actor_context in actor_location.get("actor_location_actor_consequence_context_profiles") or []:
                if not isinstance(actor_context, dict):
                    continue
                actor_id = str(actor_context.get("actor_identity_candidate_id") or "").strip()
                if not actor_id:
                    continue
                aggregate = bucket["actor_location_actor_consequence_context"].setdefault(
                    actor_id,
                    {
                        "shot_ending_actor_location_process_n": 0,
                        "non_shot_actor_location_process_n": 0,
                        "consequence_process_presence_counts": {},
                        "actor_context_challenge_contracts": [],
                    },
                )
                aggregate["shot_ending_actor_location_process_n"] += int(
                    actor_context.get("shot_ending_actor_location_process_n") or 0
                )
                aggregate["non_shot_actor_location_process_n"] += int(
                    actor_context.get("non_shot_actor_location_process_n") or 0
                )
                consequence_counts = aggregate["consequence_process_presence_counts"]
                for key, count in (actor_context.get("consequence_process_presence_counts") or {}).items():
                    consequence_counts[str(key)] = int(consequence_counts.get(str(key)) or 0) + int(count or 0)
                challenge_contract = actor_context.get("actor_context_challenge_contract")
                if isinstance(challenge_contract, dict):
                    aggregate["actor_context_challenge_contracts"].append(dict(challenge_contract))
            for actor_profile in actor_location.get("actor_location_actor_profiles") or []:
                if not isinstance(actor_profile, dict):
                    continue
                actor_id = str(actor_profile.get("actor_identity_candidate_id") or "").strip()
                if not actor_id:
                    continue
                bucket["actor_location_actor_presence"][actor_id] = (
                    int(bucket["actor_location_actor_presence"].get(actor_id) or 0)
                    + int(actor_profile.get("visible_process_presence_n") or 0)
                )
                bucket["actor_location_actor_anchor_observations"][actor_id] = (
                    int(bucket["actor_location_actor_anchor_observations"].get(actor_id) or 0)
                    + int(actor_profile.get("anchor_observation_n") or 0)
                )
    cards: list[str] = []
    for team_id, values in sorted(by_team.items(), key=lambda item: teams.get(item[0], item[0])):
        name = teams.get(team_id, team_id)
        actor_location_candidates = [
            (
                int(presence_n or 0),
                int(values["actor_location_actor_anchor_observations"].get(actor_id) or 0),
                actors.get(actor_id),
                actor_id,
            )
            for actor_id, presence_n in values["actor_location_actor_presence"].items()
            if actors.get(actor_id)
        ]
        actor_location_candidates.sort(key=lambda item: (-item[0], -item[1], str(item[2])))
        top_actor_location = actor_location_candidates[0] if actor_location_candidates else None
        top_actor_context = (
            values["actor_location_actor_consequence_context"].get(top_actor_location[3], {})
            if top_actor_location
            else {}
        )
        top_actor_challenge_contracts = [
            row
            for row in (top_actor_context.get("actor_context_challenge_contracts") or [])
            if isinstance(row, dict)
        ]
        top_actor_mixed_challenge = any(
            row.get("observed_variation_state")
            == "MIXED_VISIBLE_CONTINUATION_AND_OPPONENT_RESPONSE_CONTEXT"
            and row.get("challenge_type_candidate") == "UNDERCUT_CANDIDATE"
            and bool(row.get("withdrawal_condition_candidates"))
            for row in top_actor_challenge_contracts
        )
        if language == "tr":
            actor_location_sentence = ""
            if top_actor_location:
                consequence_counts = top_actor_context.get("consequence_process_presence_counts") or {}
                handover_n = int(consequence_counts.get("OPPONENT_HANDOVER_CANDIDATE") or 0)
                continuation_n = int(consequence_counts.get("SAME_TEAM_CONTINUATION_CANDIDATE") or 0)
                context_sentence = ""
                if handover_n or continuation_n:
                    challenge_sentence = ""
                    if top_actor_mixed_challenge:
                        challenge_sentence = (
                            " Aynı oyuncu bağlamında hem devam hem rakip cevabı görünür; "
                            "tek yönlü sonuç anlatısı qualify edilmeli ve yalnız ek kanıtla genişletilmelidir."
                        )
                    context_sentence = (
                        f" Bu actor-location bağlamındaki süreçlerin {handover_n} tanesinde rakibe geçiş, "
                        f"{continuation_n} tanesinde aynı takım devamı görüldü; "
                        "bu eşleşmenin claim kapsamı maç-içi görünür bağlamla sınırlıdır; nedensel oyuncu katkısı için ek kanıt gerekir."
                        f"{challenge_sentence}"
                    )
                actor_location_sentence = (
                    f" Kimliği admitted olan {top_actor_location[2]} "
                    f"{top_actor_location[0]} görünür süreçte actor-location katılımı verdi; "
                    f"bu yüzeyde {top_actor_location[1]} anchor gözlemi var."
                    f"{context_sentence}"
                )
            football = (
                f"{name}: Sistem bu maçta {values['eligible']} görünür oyun sürecini takım bağlamına bağlayabildi. "
                f"Bunların {values['loss']} tanesinde top kaybı, {values['recovery']} tanesinde top kazanımı ve "
                f"{values['shot']} tanesinde şutla bağlantılı bir son bölüm görüldü. "
                f"Görünür devam/sonuç yüzeyinde {values['opponent_handover']} süreçte rakibe geçiş, "
                f"{values['opponent_takeover_after_breakdown']} süreçte breakdown sonrası rakip takeover, "
                f"{values['mixed_team_same_time_review']} süreçte aynı-zamanlı iki takım belirsizliği ve "
                f"{values['no_visible_followup']} süreçte görünür follow-up yokluğu kaydedildi. "
                f"Konum katılım yüzeyinde {values['actor_location_process']} süreçte actor-location gözlemi, "
                f"{values['actor_location_layers']} admitted actor-location katmanı görüldü; "
                f"{values['pass_only_location_excluded']} PASS-only katman konum hesabından dışlandı."
                f"{actor_location_sentence}"
            )
            evidence = (
                "Okuma çerçevesi: Aynı süreçte birden fazla consequence-response kategorisi birlikte yer alabilir. "
                "Bu yüzey rakibe geçiş, breakdown sonrası takeover, same-time review ve follow-up durumlarının "
                "maç-içi süreç kompozisyonunu gösterir. Actor-location yüzeyi admitted on-ball/interaction "
                "konum katılımını betimler; takım şekli, off-ball geometri ve fiziksel oyuncu konumu bu yüzeyin claim kapsamı dışındadır."
            )
        else:
            actor_location_sentence = ""
            if top_actor_location:
                consequence_counts = top_actor_context.get("consequence_process_presence_counts") or {}
                handover_n = int(consequence_counts.get("OPPONENT_HANDOVER_CANDIDATE") or 0)
                continuation_n = int(consequence_counts.get("SAME_TEAM_CONTINUATION_CANDIDATE") or 0)
                context_sentence = ""
                if handover_n or continuation_n:
                    challenge_sentence = ""
                    if top_actor_mixed_challenge:
                        challenge_sentence = (
                            " Both continuation and opponent-response contexts are visible for the same actor; "
                            "a one-direction outcome narrative should remain qualified unless additional evidence supports it."
                        )
                    context_sentence = (
                        f" Within those actor-location contexts, {handover_n} processes showed opponent handover and "
                        f"{continuation_n} same-team continuation; this co-observation is match-local context only."
                        f"{challenge_sentence}"
                    )
                actor_location_sentence = (
                    f" Admitted identity {top_actor_location[2]} appeared in actor-location participation across "
                    f"{top_actor_location[0]} visible processes with {top_actor_location[1]} anchor observations."
                    f"{context_sentence}"
                )
            football = (
                f"{name}: The system linked {values['eligible']} visible match processes to this team. "
                f"A visible loss occurred in {values['loss']}, a recovery in {values['recovery']}, and "
                f"a shot-linked terminal state in {values['shot']}. "
                f"On the visible consequence-response surface, {values['opponent_handover']} processes contained an opponent handover, "
                f"{values['opponent_takeover_after_breakdown']} an opponent takeover after breakdown, "
                f"{values['mixed_team_same_time_review']} a mixed-team same-time review state, and "
                f"{values['no_visible_followup']} no visible follow-up. "
                f"On the location-participation surface, {values['actor_location_process']} processes contained actor-location observations, "
                f"covering {values['actor_location_layers']} admitted actor-location layers; "
                f"{values['pass_only_location_excluded']} PASS-only layers were excluded from location calculation."
                f"{actor_location_sentence}"
            )
            evidence = (
                "Reading frame: multiple consequence-response categories may coexist within the same process. "
                "This surface describes the match-local process composition of opponent handover, takeover after breakdown, "
                "same-time review, and follow-up states. The actor-location surface is scoped to admitted on-ball/interaction "
                "location participation; team shape, off-ball geometry, and physical player-location truth remain outside this claim scope."
            )
        cards.extend([football, evidence])
    return cards


def _human_score_state_process_outcome_cards(
    rich: dict[str, Any], identity: dict[str, Any], language: str
) -> list[str]:
    context = rich.get("score_state_visible_process_outcome_context") or {}
    profiles = [row for row in (context.get("profiles") or []) if isinstance(row, dict)]
    if not profiles or str(context.get("status") or "") not in {"PASS", "REVIEW_REQUIRED"}:
        return []

    teams = _human_team_labels(identity)
    score_state_surface = rich.get("player_score_state_process_participation") or {}
    score_state_profiles = [
        row for row in (score_state_surface.get("profiles") or [])
        if isinstance(row, dict)
    ]
    score_state_by_actor: dict[str, list[dict[str, Any]]] = {}
    for score_row in score_state_profiles:
        actor_id = str(score_row.get("actor_identity_candidate_id") or "").strip()
        if actor_id:
            score_state_by_actor.setdefault(actor_id, []).append(score_row)

    state_function_evidence = (
        identity.get("__spatial_progression_evidence__")
        if isinstance(identity.get("__spatial_progression_evidence__"), dict)
        else {}
    )
    state_function_by_actor: dict[str, dict[str, Any]] = {
        str(row.get("actor_identity_candidate_id") or "").strip(): row
        for row in (state_function_evidence.get("actor_visible_state_change_function_profiles") or [])
        if isinstance(row, dict)
        and str(row.get("actor_identity_candidate_id") or "").strip()
    }

    by_team: dict[str, list[dict[str, Any]]] = {}
    for row in profiles:
        team_id = str(row.get("team_identity_candidate_id") or "").strip()
        if team_id:
            by_team.setdefault(team_id, []).append(row)

    cards: list[str] = []
    for team_id, rows in sorted(by_team.items(), key=lambda item: teams.get(item[0], item[0])):
        name = teams.get(team_id, team_id)
        rows = sorted(
            rows,
            key=lambda row: (
                float(row.get("segment_start_second_candidate") or 0.0),
                float(row.get("segment_end_second_candidate") or 0.0),
            ),
        )
        segments: list[str] = []
        rate_segments: list[str] = []
        for row in rows:
            score_text = _score_state_human(row.get("score_state_candidate"), language)
            if not score_text:
                score_text = "skor bağlamı çözümlenmedi" if language == "tr" else "score context unresolved"
            eligible = int(row.get("eligible_visible_process_n") or 0)
            shot = int(row.get("shot_ending_process_n") or 0)
            loss = int(row.get("visible_loss_process_n") or 0)
            recovery = int(row.get("visible_recovery_process_n") or 0)
            process_rate = row.get("eligible_visible_process_rate_per_10_minutes")
            shot_rate = row.get("shot_ending_process_rate_per_10_minutes")
            if language == "tr":
                segments.append(
                    f"{score_text}: süreç {eligible}, şut-sonlanma {shot}, görünür kayıp {loss}, görünür kazanım {recovery}"
                )
                if isinstance(process_rate, (int, float)) and isinstance(shot_rate, (int, float)):
                    rate_segments.append(
                        f"{score_text}: süreç/10dk {process_rate:.2f}, şut-sonlanma/10dk {shot_rate:.2f}"
                    )
            else:
                segments.append(
                    f"{score_text}: processes {eligible}, shot-ending {shot}, visible loss {loss}, visible recovery {recovery}"
                )
                if isinstance(process_rate, (int, float)) and isinstance(shot_rate, (int, float)):
                    rate_segments.append(
                        f"{score_text}: processes/10m {process_rate:.2f}, shot-ending/10m {shot_rate:.2f}"
                    )

        if language == "tr":
            football = f"{name} — skor bağlamına göre görünür süreç/sonuç profili: " + "; ".join(segments) + "."
            evidence = (
                "Kanıt kapsamı: paydalar admitted görünür süreç sayısı ve skor-segmenti maruziyet süresidir. "
                + ("Oranlar: " + "; ".join(rate_segments) + ". " if rate_segments else "")
                + "Bu yüzey skor bağlamındaki görünür bileşimi tanımlar; neden, teknik plan, dominance ve risk iştahı yorumları için ayrı evidence gerekir."
            )
        else:
            football = f"{name} — visible process/outcome profile by score context: " + "; ".join(segments) + "."
            evidence = (
                "Evidence scope: denominators are admitted visible process count and score-segment exposure time. "
                + ("Rates: " + "; ".join(rate_segments) + ". " if rate_segments else "")
                + "This surface describes visible composition under score context; causal explanation, tactical-plan, dominance, and risk-appetite interpretation require separate evidence."
            )
        cards.extend([football, evidence])
    return cards


def _human_loss_recovery_score_state_cards(
    rich: dict[str, Any],
    identity: dict[str, Any],
    language: str,
) -> list[str]:
    m05 = rich.get("m05_loss_recovery_dynamics_synthesis") or {}
    if str(m05.get("status") or "").upper() != "PASS":
        return []
    teams = _human_team_labels(identity)
    cards: list[str] = []
    for profile in m05.get("profiles") or []:
        if not isinstance(profile, dict):
            continue
        team_id = str(profile.get("team_identity_candidate_id") or "").strip()
        team = teams.get(team_id, team_id or ("Takım çözümlenmedi" if language == "tr" else "Team unresolved"))
        for row in profile.get("score_state_profiles") or []:
            if not isinstance(row, dict):
                continue
            score = row.get("score_state_candidate")
            if not isinstance(score, dict) or not score:
                continue
            loss_n = int(row.get("visible_loss_context_n") or 0)
            recovery_n = int(row.get("visible_recovery_context_n") or 0)
            if loss_n == 0 and recovery_n == 0:
                continue
            exposure_seconds = row.get("score_state_exposure_seconds_candidate")
            exposure_minutes = (
                float(exposure_seconds) / 60.0
                if isinstance(exposure_seconds, (int, float)) and not isinstance(exposure_seconds, bool)
                else None
            )
            score_text = " - ".join(f"{_display_label(k)} {v}" for k, v in score.items())
            loss_families = row.get("loss_next_opponent_process_family_counts") or {}
            recovery_families = row.get("recovery_next_own_process_family_counts") or {}
            loss_bits = ", ".join(
                f"{_football_family_label(key, language)} {value}"
                for key, value in sorted(loss_families.items())
            )
            recovery_bits = ", ".join(
                f"{_football_family_label(key, language)} {value}"
                for key, value in sorted(recovery_families.items())
            )
            if language == "tr":
                exposure_note = (
                    f" yaklaşık {exposure_minutes:.1f} dakikalık görünür skor-state maruziyetinde"
                    if exposure_minutes is not None
                    else ""
                )
                sentence = (
                    f"{team}, skor {score_text}:{exposure_note} {loss_n} görünür kayıp bağlamı ve "
                    f"{recovery_n} görünür geri kazanım bağlamı."
                )
                if loss_bits:
                    sentence += f" Kayıp sonrası rakibin eşleşen görünür süreçleri: {loss_bits}."
                if recovery_bits:
                    sentence += f" Geri kazanım sonrası eşleşen kendi görünür süreçleri: {recovery_bits}."
                sentence += (
                    " Bu dağılım skor durumuyla birlikte gözlenen bağlamdır; "
                    "skor durumunu neden, taktik plan veya geçiş kalitesi olarak yorumlamaz."
                )
            else:
                exposure_note = (
                    f" across approximately {exposure_minutes:.1f} minutes of visible score-state exposure,"
                    if exposure_minutes is not None
                    else ""
                )
                sentence = (
                    f"{team}, score {score_text}:{exposure_note} {loss_n} visible loss contexts and "
                    f"{recovery_n} visible recovery contexts."
                )
                if loss_bits:
                    sentence += f" Matched opponent processes after losses: {loss_bits}."
                if recovery_bits:
                    sentence += f" Matched own processes after recoveries: {recovery_bits}."
                sentence += (
                    " This is score-conditioned observed context; score state is not treated "
                    "as cause, tactical plan, or transition quality."
                )
            cards.append(sentence)
    return cards


def _human_process_variant_board_cards(
    rich: dict[str, Any],
    identity: dict[str, Any],
    language: str,
) -> list[str]:
    c03 = (rich.get("constructs") or {}).get("C03") or {}
    board = c03.get("process_variant_board") or {}
    if str(board.get("status") or "").upper() != "PASS":
        return []
    teams = _human_team_labels(identity)
    actors = _human_admitted_actor_labels(identity)

    def actor_summary(counts: dict[str, Any]) -> str:
        visible = []
        hidden_n = 0
        for actor_id, count in sorted(
            counts.items(),
            key=lambda item: (-int(item[1] or 0), str(item[0])),
        ):
            label = actors.get(str(actor_id))
            if label:
                visible.append(f"{label} ({int(count or 0)})")
            else:
                hidden_n += int(count or 0)
        if hidden_n:
            visible.append(
                f"{hidden_n} kimliği bu maçta çözümlenmemiş oyuncu-katman adayı"
                if language == "tr"
                else f"{hidden_n} player-layer candidates without admitted match-local identity"
            )
        return ", ".join(visible) if visible else (
            "kabul edilmiş maç-içi oyuncu etiketi yok" if language == "tr" else "no admitted match-local player label"
        )

    board_rows = [row for row in (board.get("rows") or []) if isinstance(row, dict)]
    grouped_rows: dict[str, list[dict[str, Any]]] = {}
    for row in board_rows:
        team_id = str(row.get("team_identity_candidate_id") or "")
        grouped_rows.setdefault(team_id, []).append(row)

    selected_rows: list[dict[str, Any]] = []
    for team_id in sorted(grouped_rows):
        rows = sorted(
            grouped_rows[team_id],
            key=lambda row: (
                -int(row.get("member_process_n") or 0),
                str(row.get("process_family_candidate") or ""),
                str(row.get("process_motif_family_candidate_id") or ""),
            ),
        )
        selected_rows.extend(rows[:3])

    cards: list[str] = []
    for row in selected_rows:
        team_id = str(row.get("team_identity_candidate_id") or "")
        team = teams.get(team_id, team_id or ("Takım çözümlenmedi" if language == "tr" else "Team unresolved"))
        family = _football_family_label(row.get("process_family_candidate"), language)
        member_n = int(row.get("member_process_n") or 0)
        variants = row.get("member_variant_context_counts") or {}
        shot_n = int(variants.get("SHOT_LINKED") or 0)
        loss_n = int(variants.get("LOSS_LINKED") or 0)
        recovery_n = int(variants.get("RECOVERY_LINKED") or 0)
        morphology = row.get("morphology_signature") or {}
        route = str(morphology.get("route_hint") or "UNKNOWN")
        style = str(morphology.get("pass_carry_style") or "UNKNOWN")
        start_players = actor_summary(row.get("visible_start_actor_candidate_counts") or {})
        end_players = actor_summary(row.get("visible_end_actor_candidate_counts") or {})
        axis_profile = row.get("provider_attack_axis_transition_profile") or {}
        axis_text = ""
        if axis_profile:
            axis_counts = axis_profile.get("direction_transition_counts") or {}
            forward_n = int(axis_counts.get("FORWARD_PROVIDER_ATTACK_AXIS_CANDIDATE") or 0)
            rearward_n = int(axis_counts.get("REARWARD_PROVIDER_ATTACK_AXIS_CANDIDATE") or 0)
            stable_n = int(axis_counts.get("STABLE_PROVIDER_ATTACK_AXIS_CANDIDATE") or 0)
            axis_members = int(axis_profile.get("member_with_visible_axis_transition_n") or 0)
            axis_total_members = int(axis_profile.get("member_process_n") or 0)
            if language == "tr":
                axis_text = (
                    f" Provider hücum ekseni: {axis_members}/{axis_total_members} üye süreçte görünür yön geçişi; "
                    f"ileri {forward_n}, geri {rearward_n}, stabil {stable_n}. "
                    "Bu profil provider eksenindeki görünür yön değişimini özetler; fiziksel rota, line-break ve taktik progresyon bu kapsamın dışındadır."
                )
            else:
                axis_text = (
                    f" Provider attack axis: visible directional transitions in {axis_members}/{axis_total_members} member processes; "
                    f"forward {forward_n}, rearward {rearward_n}, stable {stable_n}. "
                    "This summarizes visible direction changes on the provider axis; physical route, line-break, and tactical progression remain outside scope."
                )
        consequence_profile = row.get("visible_consequence_state_change_profile") or {}
        consequence_text = ""
        if consequence_profile:
            consequence_counts = consequence_profile.get("primary_consequence_member_presence_counts") or {}
            consequence_member_n = int(consequence_profile.get("member_process_n") or member_n)
            consequence_bound_n = int(
                consequence_profile.get("member_with_visible_primary_consequence_n") or 0
            )
            consequence_label_map = {
                "SAME_TEAM_CONTINUATION_CANDIDATE": (
                    "aynı takım devamı", "same-team continuation"
                ),
                "OPPONENT_HANDOVER_CANDIDATE": (
                    "rakibe geçiş", "opponent handover"
                ),
                "OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE": (
                    "breakdown sonrası rakip takeover", "opponent takeover after breakdown"
                ),
                "MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE": (
                    "same-time review", "same-time review"
                ),
                "NO_VISIBLE_FOLLOW_UP_CANDIDATE": (
                    "görünür follow-up yok", "no visible follow-up"
                ),
                "SHOT_FOLLOW_UP_CANDIDATE": (
                    "şut follow-up", "shot follow-up"
                ),
                "RECOVERY_TO_SAME_TEAM_CONTINUATION_CANDIDATE": (
                    "recovery sonrası aynı takım devamı", "same-team continuation after recovery"
                ),
                "TERMINAL_OUTCOME_SUPPORT_CANDIDATE": (
                    "terminal sonuç desteği", "terminal-outcome support"
                ),
                "BREAKDOWN_WITH_UNCERTAIN_VISIBLE_RESPONSE_CANDIDATE": (
                    "breakdown sonrası görünür cevap belirsiz",
                    "visible response unresolved after breakdown",
                ),
            }
            consequence_bits: list[str] = []
            for key, raw_count in sorted(
                consequence_counts.items(),
                key=lambda item: (-int(item[1] or 0), str(item[0])),
            ):
                count = int(raw_count or 0)
                if count <= 0:
                    continue
                labels = consequence_label_map.get(str(key))
                if labels is None:
                    fallback = str(key).replace("_CANDIDATE", "").replace("_", " ").lower()
                    labels = (fallback, fallback)
                label = labels[0] if language == "tr" else labels[1]
                consequence_bits.append(f"{label} {count}/{consequence_member_n}")
            if language == "tr":
                consequence_text = (
                    f" Görünür devam/sonuç kompozisyonu: {consequence_bound_n}/{consequence_member_n} "
                    "üye süreçte görünür consequence bağlamı"
                    + (f"; {', '.join(consequence_bits)}" if consequence_bits else "")
                    + ". Kategoriler birbirini dışlamaz; sayılar üye süreç-varlığıdır. "
                    "Rakibe geçiş yalnız görünür handover bağlamıdır; zorlanmış top kaybı ve savunma başarısı yorumları kapsam dışındadır. "
                    "Görünür follow-up yokluğu başarısızlık yorumu için kullanılmaz; rakip tepkisi, taktik üstünlük ve nedensellik bu yüzeyin kapsamı dışındadır."
                )
            else:
                consequence_text = (
                    f" Visible continuation/consequence composition: visible consequence context in "
                    f"{consequence_bound_n}/{consequence_member_n} member processes"
                    + (f"; {', '.join(consequence_bits)}" if consequence_bits else "")
                    + ". Categories are non-exclusive and counts are member-process presence counts. "
                    "Opponent handover is visible handover context only; forced-turnover and defensive-success interpretations remain outside scope. "
                    "No visible follow-up is not used as failure evidence; opponent-response truth, tactical superiority, and causality remain outside scope."
                )
        score_context = row.get("visible_score_state_context") or {}
        score_counts = score_context.get("relative_score_state_counts") or {}
        score_context_text = ""
        if score_context:
            draw_n = int(score_counts.get("DRAW") or 0)
            leading_n = int(score_counts.get("LEADING") or 0)
            trailing_n = int(score_counts.get("TRAILING") or 0)
            bound_n = int(score_context.get("bound_member_process_n") or 0)
            member_context_n = int(score_context.get("member_process_n") or 0)
            unresolved_n = int(score_context.get("unresolved_member_process_n") or 0)
            if language == "tr":
                score_context_text = (
                    f" Skor bağlamı: beraberlikte {draw_n}, öndeyken {leading_n}, gerideyken {trailing_n}; "
                    f"{bound_n}/{member_context_n} üye süreç skor-state'e bağlandı"
                    + (f", {unresolved_n} bağ çözümlenemedi" if unresolved_n else "")
                    + ". Skor-state birlikteliği betimleyici bağlamdır; taktik uyarlama ve nedensellik bu yüzeyin kapsamı dışındadır."
                )
            else:
                score_context_text = (
                    f" Score context: draw {draw_n}, leading {leading_n}, trailing {trailing_n}; "
                    f"{bound_n}/{member_context_n} member processes were bound to visible score state"
                    + (f", with {unresolved_n} unresolved bindings" if unresolved_n else "")
                    + ". Score-state co-occurrence is descriptive context; tactical adaptation and causality remain outside this surface."
                )
        divergence = row.get("representative_first_supported_grammar_divergence") or {}
        first = divergence.get("first_supported_grammar_divergence") or {}
        divergence_text = ""
        if first.get("operation"):
            left = _variant_context_human(divergence.get("left_variant_context"), language)
            right = _variant_context_human(divergence.get("right_variant_context"), language)
            lt = _grammar_token_human(first.get("left_token"), language)
            rt = _grammar_token_human(first.get("right_token"), language)
            divergence_text = (
                f" İlk görünür ayrışma adayı: {left} ↔ {right}; {lt} ↔ {rt}."
                if language == "tr"
                else f" First visible divergence candidate: {left} ↔ {right}; {lt} ↔ {rt}."
            )

        if language == "tr":
            cards.append(
                f"{team} — {family}: {member_n} görünür süreç; "
                f"{shot_n} şut bağlantılı, {loss_n} kayıp bağlantılı, {recovery_n} recovery bağlantılı varyant. "
                f"Rota ipucu {route}; profil {style}. "
                f"İlk görünür katman oyuncuları: {start_players}. "
                f"Son görünür katman oyuncuları: {end_players}."
                f"{axis_text}"
                f"{consequence_text}"
                f"{score_context_text}"
                f"{divergence_text} "
                "Bu başlangıç/bitiş rolü yalnız görünür katman adayını gösterir; aynı timestamp içinde total order kurulmaz. "
                "Gösterim sırası görünür üye süreç sayısına göre yalnız inceleme önceliği üretir; futbol doğruluğu sıralaması üretmez."
            )
        else:
            cards.append(
                f"{team} — {family}: {member_n} visible processes; "
                f"{shot_n} shot-linked, {loss_n} loss-linked, {recovery_n} recovery-linked variants. "
                f"Route hint {route}; profile {style}. "
                f"First visible-layer players: {start_players}. "
                f"Last visible-layer players: {end_players}."
                f"{axis_text}"
                f"{consequence_text}"
                f"{score_context_text}"
                f"{divergence_text} "
                "These start/end roles are not definitive player order; no total order is imposed within the same timestamp. "
                "Display order is an attention priority based on visible member-process count, not a ranking of football truth."
            )
    return cards


def _human_circulation_fate_cards(rich: dict[str, Any], identity: dict[str, Any], language: str) -> list[str]:
    context = rich.get("visible_circulation_fate_profile") or {}
    profiles = [row for row in (context.get("profiles") or []) if isinstance(row, dict)]
    if not profiles:
        return []
    teams = _human_team_labels(identity)
    cards: list[str] = []
    for row in sorted(profiles, key=lambda item: (teams.get(str(item.get("team_identity_candidate_id") or ""), ""), str(item.get("process_family_candidate") or ""))):
        team_id = str(row.get("team_identity_candidate_id") or "UNKNOWN_TEAM")
        name = teams.get(team_id, team_id)
        family = _football_family_label(str(row.get("process_family_candidate") or ""), language)
        n = int(row.get("eligible_circulation_process_n") or 0)
        counts = row.get("visible_fate_counts") or {}
        shot = int(counts.get("SHOT_LINKED_VISIBLE") or 0) + int(counts.get("SHOT_AND_LOSS_VISIBLE") or 0)
        loss = int(counts.get("LOSS_LINKED_VISIBLE") or 0) + int(counts.get("SHOT_AND_LOSS_VISIBLE") or 0)
        recovery = int(counts.get("RECOVERY_LINKED_VISIBLE") or 0)
        other = int(counts.get("OTHER_VISIBLE_OR_UNRESOLVED") or 0)
        if language == "tr":
            football = (
                f"{name} — {family}: pas/taşıma içeren {n} görünür süreç; "
                f"{shot} şut bağlantılı, {loss} görünür kayıp bağlantılı, {recovery} recovery bağlantılı, "
                f"{other} diğer/çözümlenmemiş görünür kader."
            )
            evidence = (
                "Kanıt notu: payda yalnız PASS veya CARRY katmanı görülen admitted süreç imzalarıdır. "
                "Bu yüzey 'steril/üretken oyun', possession üstünlüğü, taktik kalite, neden veya oyuncu katkısı gerçeği üretmez."
            )
        else:
            football = (
                f"{name} — {family}: {n} visible processes contain pass/carry circulation; "
                f"{shot} are shot-linked, {loss} visible-loss-linked, {recovery} recovery-linked, "
                f"and {other} have other/unresolved visible fate."
            )
            evidence = (
                "Evidence note: the denominator contains only admitted process signatures with a visible PASS or CARRY layer. "
                "Scope is limited to visible process fate; sterile/productive football, possession superiority, tactical quality, causality, and player credit require separate evidence."
            )
        cards.extend([football, evidence])
    return cards


def _human_process_route_breadth_cards(
    rich: dict[str, Any],
    identity: dict[str, Any],
    language: str,
) -> list[str]:
    context = rich.get("visible_process_route_breadth_profile") or {}
    if str(context.get("status") or "").upper() != "PASS":
        return []
    profiles = [row for row in (context.get("profiles") or []) if isinstance(row, dict)]
    if not profiles:
        return []

    teams = _human_team_labels(identity)
    cards: list[str] = []
    for row in sorted(
        profiles,
        key=lambda item: (
            teams.get(str(item.get("team_identity_candidate_id") or ""), ""),
            str(item.get("process_family_candidate") or ""),
        ),
    ):
        # Fail closed if any stronger route/tactical interpretation leaked upstream.
        if any(
            row.get(flag) is not False
            for flag in (
                "route_is_physical_trajectory_truth",
                "route_is_line_break_truth",
                "route_breadth_is_tactical_flexibility_truth",
                "route_breadth_is_unpredictability_truth",
                "route_breadth_is_superiority_truth",
                "coach_intention_truth",
            )
        ):
            continue

        team_id = str(row.get("team_identity_candidate_id") or "").strip()
        team = teams.get(team_id, team_id or ("Takım çözümlenmedi" if language == "tr" else "Team unresolved"))
        family = _football_family_label(row.get("process_family_candidate"), language)
        eligible = int(row.get("eligible_process_n") or 0)
        route_n = int(row.get("eligible_unambiguous_route_process_n") or 0)
        unresolved_n = int(row.get("ambiguous_or_unresolved_route_process_n") or 0)
        unique_n = int(row.get("unique_visible_route_candidate_n") or 0)
        recurring_n = int(row.get("recurring_visible_route_candidate_n") or 0)
        top_route = str(row.get("top_visible_route_candidate") or "").strip()
        top_route_display = top_route.replace("_", " ").replace("->", "→")
        top_n = int(row.get("top_visible_route_process_n") or 0)

        if eligible <= 0 or route_n <= 0 or unique_n <= 0:
            continue

        if language == "tr":
            football = (
                f"{team} — {family}: {route_n}/{eligible} süreçte tekil başlangıç→bitiş rotası adayı çözüldü; "
                f"{unique_n} farklı görünür rota adayı, {recurring_n} tekrarlanan rota adayı."
            )
            if top_route and top_n > 0:
                football += f" En sık görünür rota adayı {top_route_display} {top_n}/{route_n}."
            if unresolved_n:
                football += f" {unresolved_n} süreçte başlangıç/bitiş rota bağlamı belirsiz veya çözümlenmemiş kaldı."
            evidence = (
                "Kanıt notu: bu yüzeyin kapsamı admitted süreç imzalarındaki tekil görünür başlangıç ve bitiş bölge adaylarıdır; fiziksel rota, gerçek oyuncu/top yolu, line-break, taktik esneklik, öngörülemezlik, üstünlük ve teknik ekip niyeti yorumları için ayrı observation gerekir."
            )
        else:
            football = (
                f"{team} — {family}: a single visible start→end route candidate was resolved in {route_n}/{eligible} processes; "
                f"{unique_n} distinct visible route candidates, {recurring_n} recurring route candidates."
            )
            if top_route and top_n > 0:
                football += f" Most frequent visible route candidate: {top_route_display} {top_n}/{route_n}."
            if unresolved_n:
                football += f" Start/end route context remained ambiguous or unresolved in {unresolved_n} processes."
            evidence = (
                "Evidence note: this surface is scoped to single visible start- and end-zone candidates from admitted process signatures; physical trajectory, actual player/ball path, line breaks, tactical flexibility, unpredictability, superiority, and coaching-intention interpretations require separate observations."
            )
        cards.extend([football, evidence])
    return cards


def _human_set_piece_process_cards(
    rich: dict[str, Any],
    identity: dict[str, Any],
    language: str,
) -> list[str]:
    context = rich.get("set_piece_process_consequence_context") or {}
    rows = [row for row in (context.get("rows") or []) if isinstance(row, dict)]
    if not rows:
        return []

    teams = _human_team_labels(identity)
    horizon = context.get("declared_consequence_horizon_seconds")
    by_team: dict[str, dict[str, int]] = {}
    restart_types_by_team: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        team_id = str(row.get("team_identity_candidate_id") or "").strip() or "UNKNOWN_TEAM"
        bucket = by_team.setdefault(
            team_id,
            {
                "process_n": 0,
                "shot_n": 0,
                "consequence_bound_n": 0,
                "same_team_first_n": 0,
                "opponent_first_n": 0,
                "outside_horizon_n": 0,
                "no_strict_after_n": 0,
            },
        )
        bucket["process_n"] += 1
        for restart_type in (row.get("provider_restart_type_candidates") or []):
            value = str(restart_type or "").strip()
            if value:
                restart_types_by_team[team_id][value] += 1
        if row.get("shot_present_annotation_candidate") is True:
            bucket["shot_n"] += 1
        if str(row.get("binding_state") or "") == "VISIBLE_CONSEQUENCE_CONTEXT_BOUND":
            bucket["consequence_bound_n"] += 1
        post = str(row.get("post_set_piece_first_visible_team_state") or "")
        if post == "SAME_TEAM_FIRST_STRICT_AFTER_VISIBLE_CANDIDATE":
            bucket["same_team_first_n"] += 1
        elif post == "OPPONENT_FIRST_STRICT_AFTER_VISIBLE_CANDIDATE":
            bucket["opponent_first_n"] += 1
        elif post == "FIRST_STRICT_AFTER_OUTSIDE_DECLARED_CONSEQUENCE_HORIZON":
            bucket["outside_horizon_n"] += 1
        elif post == "NO_STRICT_AFTER_VISIBLE_TRACE":
            bucket["no_strict_after_n"] += 1

    cards: list[str] = []
    for team_id, values in sorted(by_team.items(), key=lambda item: teams.get(item[0], item[0])):
        name = teams.get(team_id, team_id)
        horizon_text = (
            (f"{float(horizon):.1f} sn" if language == "tr" else f"{float(horizon):.1f}s")
            if isinstance(horizon, (int, float)) and not isinstance(horizon, bool)
            else ("çözümlenmemiş" if language == "tr" else "unresolved")
        )
        restart_counts = restart_types_by_team.get(team_id, Counter())
        restart_labels = {
            "CORNER": ("korner", "corner"),
            "CORNER_KICK": ("korner", "corner"),
            "FREE_KICK": ("serbest vuruş", "free kick"),
            "THROW_IN": ("taç", "throw-in"),
            "GOAL_KICK": ("aut", "goal kick"),
            "PENALTY_KICK": ("penaltı", "penalty"),
            "KICK_OFF": ("başlama vuruşu", "kick-off"),
            "OTHER_RESTART": ("diğer yeniden başlatma", "other restart"),
        }
        restart_parts = []
        for key, count in sorted(restart_counts.items()):
            labels = restart_labels.get(key, (key.lower(), key.lower()))
            restart_parts.append(f"{labels[0] if language == 'tr' else labels[1]} {count}")
        restart_text = ", ".join(restart_parts)
        type_profiles = [
            row for row in (context.get("restart_type_profiles") or [])
            if isinstance(row, dict)
            and str(row.get("team_identity_candidate_id") or "").strip() == team_id
        ]
        type_detail_parts: list[str] = []
        for profile in sorted(
            type_profiles,
            key=lambda row: str(row.get("provider_restart_type_candidate") or ""),
        ):
            restart_type = str(profile.get("provider_restart_type_candidate") or "").strip()
            labels = restart_labels.get(restart_type, (restart_type.lower(), restart_type.lower()))
            label_text = labels[0] if language == "tr" else labels[1]
            process_n = int(profile.get("process_n") or 0)
            shot_n = int(profile.get("shot_annotated_n") or 0)
            consequence_n = int(profile.get("visible_consequence_bound_n") or 0)
            same_n = int(profile.get("same_team_first_visible_n") or 0)
            opponent_n = int(profile.get("opponent_first_visible_n") or 0)
            outside_n = int(profile.get("outside_declared_horizon_n") or 0)
            no_visible_n = int(profile.get("no_visible_continuation_n") or 0)
            if language == "tr":
                type_detail_parts.append(
                    f"{label_text} n={process_n} (şut={shot_n}, sonuç-bağlı={consequence_n}, "
                    f"sonrası aynı={same_n}/rakip={opponent_n}/ufuk-dışı={outside_n}/görünür-devam-yok={no_visible_n})"
                )
            else:
                type_detail_parts.append(
                    f"{label_text} n={process_n} (shot={shot_n}, consequence-bound={consequence_n}, "
                    f"post same={same_n}/opponent={opponent_n}/outside-horizon={outside_n}/no-visible-follow-up={no_visible_n})"
                )
        type_detail_text = "; ".join(type_detail_parts)

        if language == "tr":
            football = (
                f"{name}: {values['process_n']} görünür duran top hücum süreci; "
                + (f"provider-reviewed tür dağılımı: {restart_text}; " if restart_text else "")
                + f"{values['shot_n']} süreçte şut anotasyonu görüldü, "
                f"{values['consequence_bound_n']} süreç görünür sonuç bağlamına bağlandı. "
                f"İlan edilmiş {horizon_text} sonuç ufku içinde süreç sonrası ilk strikt görünür takım durumu: "
                f"aynı takım {values['same_team_first_n']}, rakip {values['opponent_first_n']}; "
                f"ufuk dışında {values['outside_horizon_n']}, görünür devam yok {values['no_strict_after_n']}."
                + (f" Tür bazında görünür sonuç: {type_detail_text}." if type_detail_text else "")
            )
            evidence = (
                "Kanıt notu: bu yüzey yalnız provider-reviewed duran top süreç anotasyonu, reviewed restart türü ve görünür sonuç/sonraki takım durumunu bağlar. "
                "Restart türü yalnız reviewed provider bağlamı olarak korunur; action identity, tasarlanmış duran top rutini gerçeği, ikinci top hâkimiyeti, possession kontrolü ve nedensel sonuç bu kartın claim scope'u dışında kalır."
            )
        else:
            football = (
                f"{name}: {values['process_n']} visible attacking set-piece processes; "
                + (f"provider-reviewed restart types: {restart_text}; " if restart_text else "")
                + f"{values['shot_n']} carried a shot annotation and "
                f"{values['consequence_bound_n']} bound to visible consequence context. "
                f"Within the declared {horizon_text} consequence horizon, the first strictly visible post-process team state was "
                f"same team {values['same_team_first_n']}, opponent {values['opponent_first_n']}; "
                f"outside horizon {values['outside_horizon_n']}, no visible continuation {values['no_strict_after_n']}."
                + (f" Visible outcome by restart type: {type_detail_text}." if type_detail_text else "")
            )
            evidence = (
                "Evidence note: this surface only binds provider-reviewed set-piece process annotations, reviewed restart type, and visible consequence/post-process team state. "
                "Restart type is retained only as reviewed provider context; action identity, designed set-piece routine truth, second-ball control, possession control, and causal consequence remain outside this scope."
            )
        cards.extend([football, evidence])
    return cards


def _human_aerial_duel_cards(rich: dict[str, Any], identity: dict[str, Any], language: str) -> list[str]:
    context = rich.get("aerial_duel_first_visible_state_context") or {}
    rows = [row for row in (context.get("rows") or []) if isinstance(row, dict)]
    if not rows:
        return []
    teams = _human_team_labels(identity)
    by_team: dict[str, dict[str, int]] = {}
    for row in rows:
        team_id = str(row.get("team_identity_candidate_id") or "").strip() or "UNKNOWN_TEAM"
        bucket = by_team.setdefault(
            team_id,
            {
                "won": 0,
                "lost": 0,
                "same_team_first_visible": 0,
                "opponent_first_visible": 0,
                "mixed_team_review": 0,
                "no_visible_followup": 0,
                "single_process_bound": 0,
            },
        )
        outcome = str(row.get("provider_aerial_duel_outcome_candidate") or "")
        if outcome.endswith("_WON_CANDIDATE"):
            bucket["won"] += 1
        elif outcome.endswith("_LOST_CANDIDATE"):
            bucket["lost"] += 1
        relation = str(row.get("first_visible_team_relation_to_aerial_actor_team") or "")
        if relation == "SAME_TEAM_FIRST_VISIBLE_ACTION":
            bucket["same_team_first_visible"] += 1
        elif relation == "OPPONENT_TEAM_FIRST_VISIBLE_ACTION":
            bucket["opponent_first_visible"] += 1
        state = str(row.get("binding_state") or "")
        if state == "REVIEW_REQUIRED_MIXED_TEAM_FIRST_VISIBLE_LAYER":
            bucket["mixed_team_review"] += 1
        elif state == "NO_VISIBLE_FOLLOWUP":
            bucket["no_visible_followup"] += 1
        elif state == "SINGLE_VISIBLE_PROCESS_FAMILY_MATCH":
            bucket["single_process_bound"] += 1

    cards: list[str] = []
    for team_id, values in sorted(by_team.items(), key=lambda item: teams.get(item[0], item[0])):
        name = teams.get(team_id, team_id)
        if language == "tr":
            football = (
                f"{name}: provider tarafından hava topu kazanıldı/kaybedildi olarak etiketlenmiş "
                f"{values['won'] + values['lost']} görünür duel izinin {values['won']} tanesi kazanıldı, "
                f"{values['lost']} tanesi kaybedildi etiketi taşıyor. İlk kesin sonraki görünür aksiyon "
                f"{values['same_team_first_visible']} örnekte aynı takımda, {values['opponent_first_visible']} örnekte rakipte göründü; "
                f"{values['single_process_bound']} örnek tek bir görünür sonraki süreç ailesine bağlanabildi."
            )
            evidence = (
                f"Kanıt notu: {values['mixed_team_review']} örnek aynı zaman katmanında iki takım içerdiği için review-required, "
                f"{values['no_visible_followup']} örnekte görünür follow-up yok. Provider hava topu sonucu top kontrolü, "
                "Claim scope yalnız ilk strikt-sonraki görünür takım durumuyla sınırlıdır; top kontrolü, possession ve ikinci top hâkimiyeti için ayrı observation gerekir."
            )
        else:
            football = (
                f"{name}: among {values['won'] + values['lost']} visible duel traces carrying provider reviewed aerial-won/lost labels, "
                f"{values['won']} are labelled won and {values['lost']} lost. The first strictly later visible action belonged to the same team "
                f"in {values['same_team_first_visible']} cases and the opponent in {values['opponent_first_visible']}; "
                f"{values['single_process_bound']} cases bound to one visible next process family."
            )
            evidence = (
                f"Evidence note: {values['mixed_team_review']} cases remain review-required because both teams appear in the same next timestamp layer; "
                f"{values['no_visible_followup']} have no visible follow-up. A provider aerial-duel outcome is not ball-control, possession, "
                "or second-ball-control truth; only the first strictly later visible team state is reported."
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


def _visible_response_composition_sentence(
    process_profile: dict[str, Any],
    team_label: str,
    language: str,
) -> str:
    response = process_profile.get("visible_consequence_response_profile") or {}
    if not isinstance(response, dict):
        return ""
    counts = response.get("process_presence_counts") or {}
    if not isinstance(counts, dict) or not counts:
        return ""
    same_n = int(counts.get("SAME_TEAM_CONTINUATION_CANDIDATE") or 0)
    handover_n = int(counts.get("OPPONENT_HANDOVER_CANDIDATE") or 0)
    takeover_n = int(counts.get("OPPONENT_TAKEOVER_AFTER_BREAKDOWN_CANDIDATE") or 0)
    mixed_n = int(counts.get("MIXED_TEAM_SAME_TIME_FOLLOW_UP_REVIEW_REQUIRED_CANDIDATE") or 0)
    no_follow_n = int(counts.get("NO_VISIBLE_FOLLOW_UP_CANDIDATE") or 0)
    if language == "tr":
        return (
            f"{team_label}: aynı takım devamı {same_n}, rakibe geçiş {handover_n}, "
            f"breakdown sonrası rakip takeover {takeover_n}, same-time review {mixed_n}, "
            f"görünür follow-up yok {no_follow_n}"
        )
    return (
        f"{team_label}: same-team continuation {same_n}, opponent handover {handover_n}, "
        f"opponent takeover after breakdown {takeover_n}, same-time review {mixed_n}, "
        f"no visible follow-up {no_follow_n}"
    )


def _human_opponent_interaction_cards(
    rich: dict[str, Any], identity: dict[str, Any], language: str
) -> list[str]:
    synthesis = rich.get("m09_opponent_interaction_synthesis") or {}
    if str(synthesis.get("status") or "").upper() not in {"PASS", "REVIEW_REQUIRED"}:
        return []
    profiles = [row for row in (synthesis.get("profiles") or []) if isinstance(row, dict)]
    if not profiles:
        return []
    teams = _human_team_labels(identity)
    cards: list[str] = []
    seen_reciprocal_keys: set[tuple[str, str, str]] = set()
    for profile in profiles:
        team_id = str(profile.get("team_identity_candidate_id") or "")
        team = teams.get(team_id, team_id or ("Takım çözümlenmedi" if language == "tr" else "Team unresolved"))
        visible_direction_n = int(profile.get("visible_six_phase_direction_n") or 0)
        direction_n = int(profile.get("six_phase_direction_n") or 0)
        comparisons = [
            row for row in (profile.get("reciprocal_same_family_comparisons") or [])
            if isinstance(row, dict)
        ]
        for row in comparisons:
            opponent_id = str(row.get("opponent_team_identity_candidate_id") or "")
            opponent = teams.get(
                opponent_id,
                opponent_id or ("Rakip çözümlenmedi" if language == "tr" else "Opponent unresolved"),
            )
            family_id = str(row.get("process_family_candidate") or "")
            reciprocal_key = tuple(sorted((team_id, opponent_id))) + (family_id,)
            if reciprocal_key in seen_reciprocal_keys:
                continue
            seen_reciprocal_keys.add(reciprocal_key)
            family = _football_family_label(family_id, language)
            own = row.get("self_visible_process_profile") or {}
            opp = row.get("opponent_visible_process_profile") or {}
            own_n = int(own.get("eligible_process_n") or 0)
            own_shot = int(own.get("shot_ending_process_n") or 0)
            own_loss = int(own.get("visible_loss_process_n") or 0)
            opp_n = int(opp.get("eligible_process_n") or 0)
            opp_shot = int(opp.get("shot_ending_process_n") or 0)
            opp_loss = int(opp.get("visible_loss_process_n") or 0)
            own_response = _visible_response_composition_sentence(own, team, language)
            opp_response = _visible_response_composition_sentence(opp, opponent, language)
            if language == "tr":
                response_text = ""
                if own_response or opp_response:
                    joined = "; ".join(value for value in (own_response, opp_response) if value)
                    response_text = (
                        f" Görünür devam/sonuç kompozisyonu: {joined}. "
                        "Bu kategoriler birbirini dışlamaz; sayılar süreç-varlığı sayımıdır ve görünür follow-up yokluğu başarısızlık olarak yorumlanmaz. "
                    )
                cards.append(
                    f"{team} ↔ {opponent} — {family}: {team} tarafında {own_n} görünür süreç; "
                    f"{own_shot} şut bağlantılı son bölüm ve {own_loss} görünür kayıp. "
                    f"{opponent} aynı ailede {opp_n} görünür süreç; {opp_shot} şut bağlantılı son bölüm "
                    f"ve {opp_loss} görünür kayıp. Etkileşim kapsamı: {visible_direction_n}/{direction_n} yön görünür."
                    + response_text
                    + "Opponent-response, taktik üstünlük ve nedensellik için ayrı kanıt gerekir."
                )
            else:
                response_text = ""
                if own_response or opp_response:
                    joined = "; ".join(value for value in (own_response, opp_response) if value)
                    response_text = (
                        f" Visible continuation/consequence composition: {joined}. "
                        "These categories are non-exclusive process-presence counts; no visible follow-up is not interpreted as failure. "
                    )
                cards.append(
                    f"{team} ↔ {opponent} — {family}: {team} has {own_n} visible processes, "
                    f"with {own_shot} shot-linked terminal segments and {own_loss} visible losses. "
                    f"{opponent} has {opp_n} visible processes in the same family, with {opp_shot} shot-linked terminal segments "
                    f"and {opp_loss} visible losses. Interaction coverage: {visible_direction_n}/{direction_n} directions visible."
                    + response_text
                    + "Opponent-response, tactical superiority, and causality require separate evidence."
                )
    return cards


def _human_visible_state_function_lens(
    full_spine: dict[str, Any],
    language: str,
) -> list[str]:
    evidence = full_spine.get("spatial_progression_evidence") or {}
    if not isinstance(evidence, dict):
        return []
    if str(evidence.get("status") or "") == "NOT_EVALUATED":
        return []
    counts = evidence.get("visible_state_change_function_counts") or {}
    if not isinstance(counts, dict) or not counts:
        return []

    preserve_n = int(counts.get("VISIBLE_SAME_TEAM_CONTINUATION_CANDIDATE") or 0)
    amplify_n = int(counts.get("VISIBLE_STATE_ADVANCEMENT_CONTINUATION_CANDIDATE") or 0) + int(
        counts.get("VISIBLE_ADVANCED_ACCESS_CONTINUATION_CANDIDATE") or 0
    )
    exploit_n = int(counts.get("VISIBLE_ADVANTAGE_EXPLOITATION_CANDIDATE") or 0)
    loss_n = int(counts.get("VISIBLE_ADVANTAGE_LOSS_OR_HANDOVER_CANDIDATE") or 0)
    review_n = int(counts.get("VISIBLE_STATE_CHANGE_REVIEW_REQUIRED_CANDIDATE") or 0)
    unresolved_n = int(counts.get("VISIBLE_STATE_CHANGE_UNRESOLVED_NO_FOLLOW_UP_CANDIDATE") or 0)
    total_n = int(evidence.get("state_transition_dynamics_candidate_count") or 0)

    if language == "tr":
        return [
            (
                f"Görünür durum-değişimi lensi: toplam {total_n} aday; "
                f"koruma-benzeri aynı takım devamı {preserve_n}, "
                f"büyütme/ilerletme-benzeri görünür devam {amplify_n}, "
                f"kullanma-benzeri görünür avantaj değerlendirme {exploit_n}, "
                f"avantaj kaybı/rakibe geçiş {loss_n}; "
                f"review-required {review_n}, görünür devam çözümlenmemiş {unresolved_n}."
            ),
            (
                "CREATE=UNKNOWN; DENY=UNKNOWN. Bu yüzey yalnız state-before → action/process → visible state-after adaylarını özetler. "
                "Oyuncu nedensel katkısı, rakip organizasyonu ve değer modeli yorumu bu kartın kapsamı dışındadır."
            ),
        ]
    return [
        (
            f"Visible state-change lens: {total_n} candidates; "
            f"preserve-like same-team continuation {preserve_n}, "
            f"amplify/advance-like visible continuation {amplify_n}, "
            f"exploit-like visible advantage use {exploit_n}, "
            f"advantage loss/handover {loss_n}; "
            f"review-required {review_n}, unresolved visible continuation {unresolved_n}."
        ),
        (
            "CREATE=UNKNOWN; DENY=UNKNOWN. This surface summarizes state-before → action/process → visible state-after candidates; "
            "it is not player causal credit, opponent-organization truth, or value-model output."
        ),
    ]


def _human_match_story_cards(
    rich: dict[str, Any],
    identity: dict[str, Any],
    language: str,
) -> list[str]:
    c03 = (rich.get("constructs") or {}).get("C03") or {}
    matrix = [
        row for row in (c03.get("six_phase_team_matrix") or [])
        if isinstance(row, dict)
        and str(row.get("perspective") or "") == "ATTACK"
        and str(row.get("observation_state") or "") == "VISIBLE_PROCESS_PROFILE_AVAILABLE"
    ]
    if not matrix:
        return []

    teams = _human_team_labels(identity)
    by_team: dict[str, list[dict[str, Any]]] = {}
    for row in matrix:
        team_id = str(row.get("team_identity_candidate_id") or "").strip()
        if team_id:
            by_team.setdefault(team_id, []).append(row)

    cards: list[str] = []
    for team_id, rows in sorted(by_team.items(), key=lambda item: teams.get(item[0], item[0])):
        row = max(
            rows,
            key=lambda value: (
                int(value.get("eligible_process_n") or 0),
                str(value.get("canonical_phase_slot") or ""),
            ),
        )
        team = teams.get(team_id, team_id)
        phase = _six_phase_label(row.get("canonical_phase_slot"), language)
        process_n = int(row.get("eligible_process_n") or 0)
        shot_n = int(row.get("shot_ending_process_n") or 0)
        loss_n = int(row.get("visible_loss_process_n") or 0)
        recovery_n = int(row.get("visible_recovery_process_n") or 0)
        if language == "tr":
            cards.append(
                f"{team}: kabul edilmiş hücum fazları içinde en yüksek görünür süreç hacmi {phase} yüzeyinde; "
                f"{process_n} görünür süreç, {shot_n} şut bağlantılı son bölüm, "
                f"{loss_n} görünür kayıp ve {recovery_n} görünür kazanım."
            )
        else:
            cards.append(
                f"{team}: among admitted attacking phases, the largest visible process volume is in {phase}; "
                f"{process_n} visible processes, {shot_n} shot-linked terminal segments, "
                f"{loss_n} visible losses and {recovery_n} visible recoveries."
            )

    game_state = rich.get("game_state_context") or {}
    if str(game_state.get("status") or "").upper() in {"PASS", "REVIEW_REQUIRED"}:
        score_bits: list[str] = []
        for segment in (game_state.get("score_state_segments") or []):
            if not isinstance(segment, dict):
                continue
            score_text = _score_state_human(segment.get("score_state_candidate"), language)
            duration = segment.get("duration_second_candidate")
            if not score_text or not isinstance(duration, (int, float)) or isinstance(duration, bool):
                continue
            minutes = max(0.0, float(duration)) / 60.0
            if language == "tr":
                score_bits.append(f"{score_text} ≈ {minutes:.1f} dk")
            else:
                score_bits.append(f"{score_text} ≈ {minutes:.1f} min")
        if score_bits:
            if language == "tr":
                cards.append("Skor akışı — görünür skor-durumu maruziyeti: " + "; ".join(score_bits) + ".")
            else:
                cards.append("Score-state exposure: " + "; ".join(score_bits) + ".")

    interaction = rich.get("m09_opponent_interaction_synthesis") or {}
    profiles = [
        row for row in (interaction.get("profiles") or [])
        if isinstance(row, dict)
    ]
    seen_pairs: set[tuple[str, str, str]] = set()
    interaction_bits: list[str] = []
    for profile in profiles:
        team_id = str(profile.get("team_identity_candidate_id") or "")
        for row in (profile.get("reciprocal_same_family_comparisons") or []):
            if not isinstance(row, dict):
                continue
            opponent_id = str(row.get("opponent_team_identity_candidate_id") or "")
            family_id = str(row.get("process_family_candidate") or "")
            pair = tuple(sorted((team_id, opponent_id))) + (family_id,)
            if not team_id or not opponent_id or not family_id or pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            own = row.get("self_visible_process_profile") or {}
            opp = row.get("opponent_visible_process_profile") or {}
            team_name = teams.get(team_id, team_id)
            opp_name = teams.get(opponent_id, opponent_id)
            family = _football_family_label(family_id, language)
            own_n = int(own.get("eligible_process_n") or 0)
            own_shot = int(own.get("shot_ending_process_n") or 0)
            own_loss = int(own.get("visible_loss_process_n") or 0)
            opp_n = int(opp.get("eligible_process_n") or 0)
            opp_shot = int(opp.get("shot_ending_process_n") or 0)
            opp_loss = int(opp.get("visible_loss_process_n") or 0)
            if language == "tr":
                interaction_bits.append(
                    f"{family}: {team_name} {own_n} süreç / {own_shot} şut bağlantılı / {own_loss} kayıp ↔ "
                    f"{opp_name} {opp_n} süreç / {opp_shot} şut bağlantılı / {opp_loss} kayıp"
                )
            else:
                interaction_bits.append(
                    f"{family}: {team_name} {own_n} processes / {own_shot} shot-linked / {own_loss} losses ↔ "
                    f"{opp_name} {opp_n} processes / {opp_shot} shot-linked / {opp_loss} losses"
                )
    if interaction_bits:
        if language == "tr":
            cards.append("Takım ↔ rakip, aynı süreç ailesi: " + "; ".join(interaction_bits) + ".")
        else:
            cards.append("Team ↔ opponent, same process family: " + "; ".join(interaction_bits) + ".")

    if language == "tr":
        cards.append(
            "Kanıt kapsamı: bu maç hikâyesi kartı yalnız kabul edilmiş altı-faz süreçlerinin görünür hacim özetidir. "
            "Faz sıklığı; kalite, üstünlük, niyet veya neden hükmüne dönüştürülmez. "
            "Mekanizma ve ayrışma yorumları aşağıdaki kaynak-bağlı kartlarda ayrıca değerlendirilir."
        )
    else:
        cards.append(
            "Evidence scope: this match-story card is only a visible-volume summary of admitted six-phase processes. "
            "Phase frequency is not promoted to quality, superiority, intention, or causal explanation. "
            "Mechanism and divergence interpretation remains in the source-bound cards below."
        )
    return cards


def _human_match_story_mechanism_highlights(
    mechanism_cards: list[str],
    language: str,
    *,
    limit: int = 2,
) -> list[str]:
    if limit <= 0:
        return []
    if language == "tr":
        prefixes = (
            "İnceleme noktası ",
            "Geniş bağlam karşılaştırması ",
            "Sınırlı karşılaştırma ",
        )
        marker = " Analist için asıl soru"
    else:
        prefixes = (
            "Review point ",
            "Broad context comparison ",
            "Limited comparison ",
        )
        marker = " The analyst question is"

    highlights: list[str] = []
    for line in mechanism_cards:
        if not isinstance(line, str) or not line.startswith(prefixes):
            continue
        compact = line.split(marker, 1)[0].rstrip() if marker in line else line
        highlights.append(compact)
        if len(highlights) >= limit:
            break
    return highlights


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
    divergence_by_ref = {
        str(row.get("first_supported_branch_divergence_id") or "").strip(): row
        for row in (sequence.get("first_supported_branch_divergence_candidates") or [])
        if isinstance(row, dict)
        and str(row.get("first_supported_branch_divergence_id") or "").strip()
    }
    sequence_by_ref = {
        str(row.get("visible_action_sequence_candidate_id") or "").strip(): row
        for row in (sequence.get("visible_action_sequence_candidates") or [])
        if isinstance(row, dict)
        and str(row.get("visible_action_sequence_candidate_id") or "").strip()
    }

    def sequence_locators(refs: list[str]) -> list[dict[str, Any]]:
        locators: list[dict[str, Any]] = []
        for ref in refs:
            row = sequence_by_ref.get(ref)
            if not isinstance(row, dict):
                continue
            locators.append({
                "sequence_ref": ref,
                "period_candidate": row.get("period_candidate"),
                "start_time_candidate": row.get("start_time_candidate"),
                "end_time_candidate": row.get("end_time_candidate"),
            })
        return locators

    by_divergence: dict[str, list[dict[str, Any]]] = {}
    for handoff_id, handoff in handoffs.items():
        divergence_ref = str(
            handoff.get("source_first_supported_branch_divergence_ref") or ""
        ).strip()
        decision = decisions.get(handoff_id)
        if divergence_ref and isinstance(decision, dict):
            by_divergence.setdefault(divergence_ref, []).append({
                "safe_finding_handoff_ref": handoff_id,
                "handoff": handoff,
                "decision": decision,
            })

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
        matched_entries = [
            row
            for divergence_ref in divergence_refs
            for row in by_divergence.get(divergence_ref, [])
        ]
        if not matched_entries:
            continue
        matched = [
            row.get("decision")
            for row in matched_entries
            if isinstance(row.get("decision"), dict)
        ]
        matched_divergence_refs = sorted(
            divergence_ref for divergence_ref in divergence_refs if by_divergence.get(divergence_ref)
        )
        lineage_rows = [
            divergence_by_ref.get(divergence_ref) or {}
            for divergence_ref in matched_divergence_refs
        ]
        shared_ancestor_overlap_handoff_count = sum(
            row.get("shared_ancestor_overlap_state") == "SHARED_ANCESTOR_OVERLAP"
            for row in lineage_rows
        )
        no_shared_ancestor_handoff_count = sum(
            row.get("shared_ancestor_overlap_state") == "NO_SHARED_ANCESTOR_WITHIN_TRACKED_SCOPE"
            for row in lineage_rows
        )
        ancestry_unresolved_handoff_count = len(lineage_rows) - (
            shared_ancestor_overlap_handoff_count + no_shared_ancestor_handoff_count
        )
        shared_ancestor_refs = sorted({
            str(value)
            for row in lineage_rows
            for value in (row.get("shared_ancestor_refs") or [])
            if str(value)
        })
        matched_handoff_refs = sorted({
            str(row.get("safe_finding_handoff_ref") or "").strip()
            for row in matched_entries
            if str(row.get("safe_finding_handoff_ref") or "").strip()
        })
        representative_support_refs = sorted({
            str(value)
            for row in matched_entries
            for value in (
                ((row.get("handoff") or {}).get("support") or {}).get(
                    "visible_success_sequence_refs"
                )
                or []
            )
            if str(value)
        })
        representative_counterexample_pair_refs = sorted({
            str(value)
            for row in matched_entries
            for value in (
                ((row.get("handoff") or {}).get("counterevidence") or {}).get(
                    "comparable_counterexample_refs"
                )
                or []
            )
            if str(value)
        })
        representative_counterexample_sequence_refs = sorted({
            str(value)
            for row in matched_entries
            for value in (
                ((row.get("handoff") or {}).get("counterevidence") or {}).get(
                    "visible_failure_sequence_refs"
                )
                or []
            )
            if str(value)
        })
        representative_support_locators = sequence_locators(representative_support_refs)
        representative_counterexample_locators = sequence_locators(
            representative_counterexample_sequence_refs
        )

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
            "safe_finding_handoff_refs": matched_handoff_refs,
            "source_first_supported_branch_divergence_refs": sorted(divergence_refs),
            "source_process_variant_family_ref": family_ref,
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
            "shared_ancestor_overlap_handoff_count": shared_ancestor_overlap_handoff_count,
            "no_shared_ancestor_within_tracked_scope_handoff_count": no_shared_ancestor_handoff_count,
            "ancestry_unresolved_handoff_count": ancestry_unresolved_handoff_count,
            "shared_ancestor_ref_count": len(shared_ancestor_refs),
            "shared_ancestor_refs": shared_ancestor_refs,
            "bounded_ancestry_distinctness_is_independence_proof": False,
            "shared_ancestor_overlap_can_increase_support": False,
            "representative_support_sequence_refs": representative_support_refs,
            "representative_counterexample_pair_refs": representative_counterexample_pair_refs,
            "representative_counterexample_sequence_refs": representative_counterexample_sequence_refs,
            "representative_support_sequence_locators": representative_support_locators,
            "representative_counterexample_sequence_locators": representative_counterexample_locators,
            "representative_links_create_independent_support": False,
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

    minutes = profile.get("total_minutes_observed_candidate")
    total_exposure_state = str(profile.get("total_exposure_state") or "")
    interval_exposure_state = str(profile.get("interval_exposure_state") or "")
    exposure_bit = ""
    if (
        isinstance(minutes, (int, float))
        and not isinstance(minutes, bool)
        and total_exposure_state == "MATCH_TOTAL_MINUTES_OBSERVED_CANDIDATE"
    ):
        minute_text = _human_number(minutes)
        if language == "tr":
            exposure_bit = (
                f" Toplam süre bağlamı: {minute_text} dk; süreç anındaki saha-içi zaman aralığı "
                "çözümlenmedi. Per-90 süreç oranı bu kartta üretilmez."
            )
        else:
            exposure_bit = (
                f" Match-total exposure context: {minute_text} minutes; the on-field interval at process time "
                "remains unresolved. No per-90 process rate is produced on this card."
            )
    elif interval_exposure_state:
        exposure_bit = (
            " Süreç anındaki saha-içi exposure bu kartta çözümlenmedi."
            if language == "tr"
            else " On-field exposure at process time remains unresolved on this card."
        )

    if not bits and not process_bit and not exposure_bit:
        return ""
    if language == "tr":
        metric_text = ", ".join(bits)
        return (
            f" Oyuncu inceleme odağı: {label}. "
            + (f"XLSX maç toplamı bağlamı: {metric_text}." if metric_text else "")
            + process_bit
            + exposure_bit
            + " Bu aggregate profil yalnız aynı oyuncunun maç-içi işlev bağlamını taşır; mekanizma aksiyon kimliği, oyuncu kalite hükmü ve nedensel katkı bu kapsamın dışında kalır."
        )
    metric_text = ", ".join(bits)
    return (
        f" Player review focus: {label}. "
        + (f"XLSX match-total context: {metric_text}." if metric_text else "")
        + process_bit
        + exposure_bit
        + " This aggregate profile is used only as match-local functional context for the same player; action identity, player-quality judgment, and causal contribution remain outside its allowed scope."
    )


def _mechanism_representative_links_sentence(
    safe_context: dict[str, Any],
    language: str,
) -> str:
    support_locators = [
        row
        for row in (safe_context.get("representative_support_sequence_locators") or [])
        if isinstance(row, dict)
    ]
    counter_locators = [
        row
        for row in (safe_context.get("representative_counterexample_sequence_locators") or [])
        if isinstance(row, dict)
    ]
    support_refs = [
        str(value)
        for value in (safe_context.get("representative_support_sequence_refs") or [])
        if str(value)
    ]
    counter_refs = [
        str(value)
        for value in (safe_context.get("representative_counterexample_sequence_refs") or [])
        if str(value)
    ]
    if not support_refs and not counter_refs:
        return ""

    def locator_text(row: dict[str, Any]) -> str:
        ref = str(row.get("sequence_ref") or "").strip()
        period = str(row.get("period_candidate") or "").strip()
        start = _fmt_time(row.get("start_time_candidate"))
        end = _fmt_time(row.get("end_time_candidate"))
        if language == "tr":
            period_label = (
                "1. devre"
                if period == "1"
                else ("2. devre" if period == "2" else (f"dönem {period}" if period else "dönem bilinmiyor"))
            )
        else:
            period_label = (
                "first half"
                if period == "1"
                else ("second half" if period == "2" else (f"period {period}" if period else "period unresolved"))
            )
        window = (
            f"{start}–{end}"
            if start != "UNKNOWN" and end != "UNKNOWN"
            else (start if start != "UNKNOWN" else end)
        )
        if window and window != "UNKNOWN":
            return f"{period_label} {window} [{ref}]" if ref else f"{period_label} {window}"
        return ref

    support_shown = [locator_text(row) for row in support_locators[:2]]
    counter_shown = [locator_text(row) for row in counter_locators[:2]]
    if not support_shown:
        support_shown = support_refs[:2]
    if not counter_shown:
        counter_shown = counter_refs[:2]

    if language == "tr":
        bits = []
        if support_shown:
            bits.append(f"Temsilî destek: {', '.join(support_shown)}.")
        if counter_shown:
            bits.append(f"Karşı örnek: {', '.join(counter_shown)}.")
        bits.append("Bu bağlantılar bağımsız destek sayılmaz.")
        return " " + " ".join(bits)

    bits = []
    if support_shown:
        bits.append(f"Representative support: {', '.join(support_shown)}.")
    if counter_shown:
        bits.append(f"Counterexample: {', '.join(counter_shown)}.")
    bits.append("These links do not count as independent support.")
    return " " + " ".join(bits)


def _mechanism_governance_sentence(language: str) -> str:
    if language == "tr":
        return (
            " Güvenli anlam: bu kart yalnız maç-içi görünür varyant farkını analist incelemesine taşır."
            " Yasak çıkarım: nedensellik, taktik plan gerçeği, üstünlük, fiziksel şekil ve oyuncu kalite hükmü üretmez."
            " Analist aksiyonu: ilk görünür ayrışmayı karşılaştırılabilir varyantlarda kontrol et; counterevidence ve kısmi bağlamı incele;"
            " oyuncu aggregate verisini yalnız maç-içi işlev bağlamı olarak kullan."
        )
    return (
        " Safe meaning: this card is only a match-local visible-variant cue for analyst review."
        " Scope boundary: causality, tactical-plan truth, superiority, physical shape, and player quality remain outside this card's admitted scope."
        " Analyst action: review the first visible divergence across comparable variants, inspect counterevidence and partial context,"
        " and use player aggregates only as match-local functional context."
    )


def _mechanism_horizon_sentence(
    reason_codes: list[str],
    language: str,
    *,
    sensitive_n: int = 0,
    denominator_n: int = 0,
    incomplete_n: int = 0,
    censored_n: int = 0,
) -> str:
    reasons = {str(value) for value in (reason_codes or []) if str(value)}
    if not reasons:
        return ""
    sensitive = "ADMITTED_FOLLOWUP_HORIZON_SENSITIVE" in reasons
    untested = "CONSEQUENCE_HORIZON_SENSITIVITY_NOT_TESTED" in reasons
    partial = "ADMITTED_FOLLOWUP_HORIZON_SENSITIVITY_PARTIAL" in reasons
    followup_untested = "ADMITTED_FOLLOWUP_HORIZON_SENSITIVITY_NOT_TESTED" in reasons
    if not any((sensitive, untested, partial, followup_untested)):
        return ""
    if language == "tr":
        bits = []
        if sensitive:
            bits.append("görünür sonuç bağlantısının en az bir bölümü kullanılan admitted follow-up sonuç ufkuna duyarlı")
        if untested:
            bits.append("ayrışma alternatif sonuç ufuklarında tam sınanmadı")
        if partial:
            bits.append("follow-up ufku duyarlılık kontrolü yalnız kısmi kapsamda tamamlandı")
        if followup_untested:
            bits.append("admitted follow-up ufku duyarlılığı henüz tam test edilmedi")
        if denominator_n > 0:
            bits.append(f"duyarlı varyant yükü {max(0, sensitive_n)}/{denominator_n}")
        if incomplete_n > 0:
            bits.append(f"{incomplete_n} incomplete duyarlılık kaydı")
        if censored_n > 0:
            bits.append(f"{censored_n} sansürlü varyant")
        return (
            " Sonuç ufku notu: " + "; ".join(bits) + ". "
            "Bu sayımlar bağımsız destek sayılmaz ve görünür ayrışmanın ufuk seçimine dayanıklılığını sınırlar; "
            "nedensellik veya taktik doğruluk üretmez."
        )
    bits = []
    if sensitive:
        bits.append("at least part of the visible outcome linkage is sensitive to the admitted follow-up horizon")
    if untested:
        bits.append("the split was not fully tested across alternative consequence horizons")
    if partial:
        bits.append("follow-up-horizon sensitivity testing is only partially complete")
    if followup_untested:
        bits.append("admitted follow-up-horizon sensitivity is not fully tested")
    if denominator_n > 0:
        bits.append(f"horizon-sensitive variant burden {max(0, sensitive_n)}/{denominator_n}")
    if incomplete_n > 0:
        bits.append(f"{incomplete_n} incomplete sensitivity record")
    if censored_n > 0:
        bits.append(f"{censored_n} censored variant")
    return (
        " Consequence-horizon note: " + "; ".join(bits) + ". "
        "These counts do not count as independent support and limit robustness to horizon choice; "
        "causality and tactical truth remain outside the admitted scope."
    )


def _mechanism_same_grammar_context_sentence(
    row: dict[str, Any],
    teams: dict[str, str],
    language: str,
) -> str:
    summaries = [
        value
        for value in (row.get("same_grammar_context_review_summaries") or [])
        if isinstance(value, dict)
    ]
    if len(summaries) < 2:
        return ""
    details: list[str] = []
    for summary in summaries:
        team_ids = [
            str(value)
            for value in (summary.get("team_identity_candidate_ids") or [])
            if str(value)
        ]
        team = ", ".join(teams.get(value, value) for value in team_ids) or (
            "Takım çözümlenmedi" if language == "tr" else "Team unresolved"
        )
        periods = ", ".join(
            _period_human(value, language)
            for value in (summary.get("period_candidates") or [])
        ) or _period_human(None, language)
        resolved = int(summary.get("resolved_variant_count") or 0)
        success = int(summary.get("success_resolved_variant_count") or 0)
        failure = int(summary.get("failure_resolved_variant_count") or 0)
        if language == "tr":
            details.append(
                f"{team} {periods}: {resolved} çözülmüş ({success} olumlu / {failure} olumsuz)"
            )
        else:
            details.append(
                f"{team} {periods}: {resolved} resolved ({success} positive / {failure} negative)"
            )
    if language == "tr":
        return (
            f" Aynı gramer bağlam kontrolü: {len(summaries)} ayrı takım/devre bağlamı görünür; "
            + "; ".join(details)
            + ". Bu yüzey bağlam yayılımını gösterir; context robustness için ayrı test gerekir."
        )
    return (
        f" Same-grammar context check: {len(summaries)} separate team/period contexts are visible; "
        + "; ".join(details)
        + ". This surface shows context spread; context robustness requires a separate test."
    )


def _mechanism_maturity_sentence(row: dict[str, Any], language: str) -> str:
    profile = row.get("evidence_maturity_profile")
    if not isinstance(profile, dict) or not profile:
        return ""
    resolved = int(profile.get("resolved_variant_denominator_n") or 0)
    episodes = int(profile.get("episode_spread_n") or 0)
    clusters = int(profile.get("occurrence_disjoint_support_cluster_n") or 0)
    cluster_member_total = int(
        profile.get("occurrence_disjoint_support_cluster_member_variant_total") or 0
    )
    largest_cluster_member_n = int(
        profile.get("largest_occurrence_disjoint_support_cluster_member_variant_count") or 0
    )
    censored = int(profile.get("right_censored_variant_n") or 0)
    dependency = profile.get("dependency_independence_proven") is True
    counterevidence = profile.get("counterevidence_present") is True
    safe_context = row.get("safe_finding_context") if isinstance(row.get("safe_finding_context"), dict) else {}
    match_n = int(safe_context.get("safe_finding_match_count") or 0)
    shared_n = int(safe_context.get("shared_ancestor_overlap_handoff_count") or 0)
    no_shared_n = int(safe_context.get("no_shared_ancestor_within_tracked_scope_handoff_count") or 0)
    unresolved_n = int(safe_context.get("ancestry_unresolved_handoff_count") or 0)
    if language == "tr":
        dependency_text = "dependency bağımsızlığı doğrulandı" if dependency else "dependency bağımsızlığı doğrulanmadı"
        counter_text = "karşı kanıt yüzeyi görünür" if counterevidence else "karşı kanıt yüzeyi bu profilde görünür değil"
        cluster_text = ""
        if cluster_member_total > 0 and largest_cluster_member_n > 0:
            cluster_text = (
                f" Küme yoğunluğu: en büyük occurrence-ayrık küme {largest_cluster_member_n}/{cluster_member_total} "
                "cluster-bound varyant taşıyor; bu oran yalnız küme yoğunluğunu gösterir, bağımsızlık için ayrı kanıt gerekir."
            )
        provenance_text = ""
        if match_n and (shared_n or no_shared_n or unresolved_n):
            provenance_text = (
                f" Provenance bağımlılığı: {shared_n}/{match_n} bağlı Safe Finding başka divergence adaylarıyla occurrence kökü paylaşıyor; "
                f"{no_shared_n}/{match_n} tracked scope içinde ortak kök göstermiyor."
            )
            if unresolved_n:
                provenance_text += f" {unresolved_n}/{match_n} bağlı bulgunun ancestry durumu çözümlenmedi."
            provenance_text += " Bu ayrım bounded ancestry görünürlüğünü açıklar; bağımsızlık için ayrı kanıt gerekir."
        return (
            f" Kanıt olgunluğu: {resolved} çözümlenmiş varyant, {episodes} görünür maç bölümü, "
            f"{clusters} occurrence-ayrık destek kümesi; sağdan sansürlü varyant={censored}; "
            f"{dependency_text}; {counter_text}."
            + cluster_text
            + provenance_text
            + " Bu çok boyutlu profil olgunluk boyutlarını ayrı tutar; "
            "tek güven skoruna indirgeme yapmaz ve claim/emit yetkisi bu profilin kapsamı dışında kalır."
        )
    dependency_text = "dependency independence is proven" if dependency else "dependency independence is not proven"
    counter_text = "a counterevidence surface is visible" if counterevidence else "no counterevidence surface is visible in this profile"
    cluster_text = ""
    if cluster_member_total > 0 and largest_cluster_member_n > 0:
        cluster_text = (
            f" Cluster concentration: the largest occurrence-disjoint cluster carries "
            f"{largest_cluster_member_n}/{cluster_member_total} cluster-bound variants; "
            "this ratio is not an independence probability."
        )
    provenance_text = ""
    if match_n and (shared_n or no_shared_n or unresolved_n):
        provenance_text = (
            f" Provenance dependency: {shared_n}/{match_n} linked Safe Findings share occurrence ancestors with other divergence candidates; "
            f"{no_shared_n}/{match_n} show no shared ancestor within the tracked scope."
        )
        if unresolved_n:
            provenance_text += f" {unresolved_n}/{match_n} linked findings have unresolved ancestry."
        provenance_text += " This distinction is not proof of independence."
    return (
        f" Evidence maturity: {resolved} resolved variants, {episodes} visible match episodes, "
        f"{clusters} occurrence-disjoint support clusters; right-censored variants={censored}; "
        f"{dependency_text}; {counter_text}."
        + cluster_text
        + provenance_text
        + " This multidimensional profile keeps maturity dimensions separate "
        "rather than collapsing them into a confidence score; claim/emit authority remains outside this profile."
    )


def _context_feature_human(value: Any, language: str) -> str:
    token = str(value or "").strip()
    core = token.split("::", 1)[-1] if "::" in token else token
    tr = {
        "process_shot_present_annotation_candidate:TRUE": "süreçte şut-var işareti",
        "process_semantic_role:PARTICIPATION_INTERVAL": "süreç katılım bağlamı",
    }
    en = {
        "process_shot_present_annotation_candidate:TRUE": "shot-present process annotation",
        "process_semantic_role:PARTICIPATION_INTERVAL": "process participation context",
    }
    table = tr if language == "tr" else en
    return table.get(core, core.replace("_", " ").replace(":TRUE", "").lower())


def _mechanism_context_review_payload(
    source_record: dict[str, Any],
    rich_payload: dict[str, Any],
    team_ids: list[str],
    process_family_candidate: Any,
    safe_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    safe_context = safe_context or {}
    provider_rows = [
        dict(row)
        for row in (source_record.get("process_context_feature_difference_candidates") or [])
        if isinstance(row, dict)
    ]
    provider_rows.sort(
        key=lambda row: abs(float(row.get("descriptive_rate_delta_success_minus_failure") or 0.0)),
        reverse=True,
    )
    provider_rows = provider_rows[:3]

    family = str(process_family_candidate or "").strip()

    opponent_context: dict[str, Any] = {}
    if len(team_ids) == 1 and family:
        team_id = team_ids[0]
        m09 = rich_payload.get("m09_opponent_interaction_synthesis") or {}
        for profile in m09.get("profiles") or []:
            if not isinstance(profile, dict) or str(profile.get("team_identity_candidate_id") or "") != team_id:
                continue
            for comparison in profile.get("reciprocal_same_family_comparisons") or []:
                if not isinstance(comparison, dict):
                    continue
                if str(comparison.get("process_family_candidate") or "") != family:
                    continue
                opponent_context = {
                    "team_identity_candidate_id": team_id,
                    "opponent_team_identity_candidate_id": str(
                        comparison.get("opponent_team_identity_candidate_id") or ""
                    ),
                    "process_family_candidate": family,
                    "self_visible_process_profile": dict(
                        comparison.get("self_visible_process_profile") or {}
                    ),
                    "opponent_visible_process_profile": dict(
                        comparison.get("opponent_visible_process_profile") or {}
                    ),
                    "difference_is_opponent_response_truth": False,
                    "difference_is_tactical_superiority_truth": False,
                    "difference_is_causal_truth": False,
                    "creates_independent_support": False,
                }
                break
            if opponent_context:
                break

    return {
        "provider_context_difference_candidates": provider_rows,
        "opponent_same_family_context": opponent_context,
        "score_state_context": {
            "score_state_consensus": safe_context.get("score_state_consensus") is True,
            "score_state_candidate": safe_context.get("score_state_candidate"),
            "context_is_preoutcome_only": True,
        },
        "context_is_causal_explanation": False,
        "context_is_tactical_adaptation_truth": False,
        "context_is_opponent_response_truth": False,
        "context_creates_independent_support": False,
        "context_can_increase_claim_ceiling": False,
        "claim_ceiling": "MATCH_LOCAL_VISIBLE_MECHANISM_CONTEXT_REVIEW_ONLY",
    }


def _mechanism_context_review_sentence(
    source_record: dict[str, Any],
    rich_payload: dict[str, Any],
    team_ids: list[str],
    process_family_candidate: Any,
    teams: dict[str, str],
    language: str,
) -> str:
    bits: list[str] = []
    context_rows = [
        row
        for row in (source_record.get("process_context_feature_difference_candidates") or [])
        if isinstance(row, dict)
    ]
    context_rows.sort(
        key=lambda row: abs(float(row.get("descriptive_rate_delta_success_minus_failure") or 0.0)),
        reverse=True,
    )
    if context_rows:
        row = context_rows[0]
        feature = _context_feature_human(row.get("feature_token"), language)
        s_num = int(row.get("success_visible_numerator") or 0)
        s_den = int(row.get("success_eligible_denominator") or 0)
        f_num = int(row.get("failure_visible_numerator") or 0)
        f_den = int(row.get("failure_eligible_denominator") or 0)
        layer = row.get("partial_order_layer_index")
        layer_text = (
            f"{int(layer) + 1}. görünür katmanda " if isinstance(layer, int) else ""
        ) if language == "tr" else (
            f"at visible layer {int(layer) + 1}, " if isinstance(layer, int) else ""
        )
        if language == "tr":
            bits.append(
                f"Bağlam ayrışması: {layer_text}{feature}; olumlu {s_num}/{s_den}, olumsuz {f_num}/{f_den}."
            )
        else:
            bits.append(
                f"Context difference: {layer_text}{feature}; positive {s_num}/{s_den}, negative {f_num}/{f_den}."
            )

    family = str(process_family_candidate or "").strip()
    if len(team_ids) == 1 and family:
        team_id = team_ids[0]
        m09 = rich_payload.get("m09_opponent_interaction_synthesis") or {}
        for profile in m09.get("profiles") or []:
            if not isinstance(profile, dict) or str(profile.get("team_identity_candidate_id") or "") != team_id:
                continue
            for comparison in profile.get("reciprocal_same_family_comparisons") or []:
                if not isinstance(comparison, dict):
                    continue
                if str(comparison.get("process_family_candidate") or "") != family:
                    continue
                opponent_id = str(comparison.get("opponent_team_identity_candidate_id") or "")
                own = comparison.get("self_visible_process_profile") or {}
                opp = comparison.get("opponent_visible_process_profile") or {}
                team = teams.get(team_id, team_id)
                opponent = teams.get(opponent_id, opponent_id)
                own_n = int(own.get("eligible_process_n") or 0)
                own_shot = int(own.get("shot_ending_process_n") or 0)
                own_loss = int(own.get("visible_loss_process_n") or 0)
                opp_n = int(opp.get("eligible_process_n") or 0)
                opp_shot = int(opp.get("shot_ending_process_n") or 0)
                opp_loss = int(opp.get("visible_loss_process_n") or 0)
                if language == "tr":
                    bits.append(
                        f"Aynı süreç ailesinin karşılıklı görünümü: {team} {own_n} süreç ({own_shot} şut bağlantılı, {own_loss} görünür kayıp); "
                        f"{opponent} {opp_n} süreç ({opp_shot} şut bağlantılı, {opp_loss} görünür kayıp)."
                    )
                else:
                    bits.append(
                        f"Reciprocal view of the same process family: {team} {own_n} processes ({own_shot} shot-linked, {own_loss} visible losses); "
                        f"{opponent} {opp_n} processes ({opp_shot} shot-linked, {opp_loss} visible losses)."
                    )
                break
            if len(bits) >= 2:
                break

    if bits:
        if language == "tr":
            bits.append("Bu bağlar betimleyicidir; neden, rakip tepkisi veya taktik üstünlük kanıtı üretmez.")
        else:
            bits.append("These bindings are descriptive; they do not establish cause, opponent-response truth, or tactical superiority.")
    return " " + " ".join(bits) if bits else ""


def _human_mechanism_cards(
    root: Path,
    full_spine: dict[str, Any],
    identity: dict[str, Any],
    language: str,
    *,
    analyst_question_payload: dict[str, Any] | None = None,
) -> list[str]:
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
    admitted_actor_labels = _human_admitted_actor_labels(identity)
    shortlist = build_mechanism_story_review_shortlist(
        payload,
        analyst_output_claim_payload=analyst_output or None,
        process_variant_payload=process_variant_payload or None,
        process_participation_payload=process_participation_payload or None,
        variant_feature_challenge_payload=variant_feature_challenge_payload or None,
        analyst_question_payload=analyst_question_payload,
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
            admitted_actor_labels,
            language,
        )
        safe_context = safe_context_by_family.get(
            str(row.get("source_process_variant_family_ref") or ""),
            {},
        )
        context_review_sentence = _mechanism_context_review_sentence(
            source_record, rich_payload, team_ids, row.get("single_process_family_candidate"), teams, language
        )
        broad_context_only = (
            str(row.get("process_context_binding_state") or "")
            == "AMBIGUOUS_MULTI_PROCESS_FAMILY_CONTEXT"
        )
        if language == "tr":
            prefix = (
                "Sınırlı karşılaştırma"
                if single_episode_only
                else (
                    "Geniş bağlam karşılaştırması"
                    if broad_context_only
                    else "İnceleme noktası"
                )
            )
            football = (
                f"{prefix} {idx}: {team}, {periods}. {grammar} bağlantısı maçın {spread} farklı bölümünde tekrar görülüyor. "
                "Bu bağlantının karşılaştırılabilir varyantları hem olumlu hem olumsuz görünür sonuçlara gidiyor. "
                "Analist için asıl soru, aynı başlangıçtan sonra hangi aksiyon veya bağlam değişiminin sonuçları ayırdığı."
            )
            if single_episode_only:
                football += " Bu karşılaştırma tek görünür maç bölümünde yoğunlaştığı için ana mekanizma olarak yorumlanmamalıdır."
            elif broad_context_only:
                football += (
                    " Süreç bağlamı birden fazla aileye yayıldığı için bu geniş örüntü ana mekanizma olarak sunulmaz; "
                    "daha özgül süreç ayrışmaları için inceleme yüzeyi olarak korunur."
                )
                football += _mechanism_visible_split_sentence(source_record, language)
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
            football += _mechanism_representative_links_sentence(safe_context, language)
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
            football += context_review_sentence
            challenge_n = int(row.get("mechanism_challenge_record_count") or 0)
            challenge_note = ""
            if challenge_n:
                challenge_note = (
                    f" Bu aday için {challenge_n} kaynak-bağlı challenge kaydı; örneklem bileşimi, rakip davranışı/skor durumu, "
                    "gözlem/provider semantiği, çözülmemiş bağımlılık ve sonuç ufku gibi alternatif açıklamaları açık tutuyor. "
                    "Bu koşullardan biri görünür ayrışmayı ortadan kaldırırsa mekanizma yorumu geri çekilmeli veya nitelendirilmelidir."
                )
            horizon_note = _mechanism_horizon_sentence(
                [str(value) for value in (row.get("mechanism_challenge_reason_codes") or []) if str(value)],
                language,
                sensitive_n=int(row.get("admitted_followup_horizon_sensitive_variant_count") or 0),
                denominator_n=resolved,
                incomplete_n=int(row.get("admitted_followup_horizon_sensitivity_incomplete_variant_count") or 0),
                censored_n=int(row.get("right_censored_variant_count") or 0),
            )
            evidence = (
                f"Kanıt notu: karşılaştırma yüzeyinde {resolved} çözümlenmiş varyant kaydı var; "
                f"{success} olumlu ve {failure} olumsuz görünür sonuca bağlı. "
                f"Kanıt örgüsü {clusters} ayrı görünür aksiyon kümesine yayılıyor. "
                "Yorum kapsamı maç-içi varyant ayrışması ve kaynak-bağlı süreç bağlamıdır."
                + challenge_note
                + horizon_note
                + _mechanism_maturity_sentence(row, language)
                + _mechanism_same_grammar_context_sentence(row, teams, language)
            )
        else:
            prefix = (
                "Limited comparison"
                if single_episode_only
                else (
                    "Broad context comparison"
                    if broad_context_only
                    else "Review point"
                )
            )
            football = (
                f"{prefix} {idx}: {team}, {periods}. The {grammar} connection recurs across {spread} distinct match segments. "
                "Comparable variants of the same visible start lead to both positive and negative visible outcomes. "
                "The analyst question is which subsequent action or context change separates those outcomes."
            )
            if single_episode_only:
                football += " This comparison is concentrated in one visible match segment and should not be treated as a main mechanism."
            elif broad_context_only:
                football += (
                    " The process context spans multiple families, so this broad pattern is not presented as a main mechanism; "
                    "it remains a review surface for more specific process separation."
                )
                football += _mechanism_visible_split_sentence(source_record, language)
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
            football += _mechanism_representative_links_sentence(safe_context, language)
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
            football += context_review_sentence
            challenge_n = int(row.get("mechanism_challenge_record_count") or 0)
            challenge_note = ""
            if challenge_n:
                challenge_note = (
                    f" This candidate carries {challenge_n} source-bound challenge records that keep sample composition, opponent behaviour/score state, "
                    "observation/provider semantics, unresolved dependency and consequence-horizon definitions open as alternative explanations. "
                    "If those conditions remove the visible split, the mechanism interpretation must be withdrawn or qualified."
                )
            horizon_note = _mechanism_horizon_sentence(
                [str(value) for value in (row.get("mechanism_challenge_reason_codes") or []) if str(value)],
                language,
                sensitive_n=int(row.get("admitted_followup_horizon_sensitive_variant_count") or 0),
                denominator_n=resolved,
                incomplete_n=int(row.get("admitted_followup_horizon_sensitivity_incomplete_variant_count") or 0),
                censored_n=int(row.get("right_censored_variant_count") or 0),
            )
            evidence = (
                f"Evidence note: the comparison surface contains {resolved} resolved variant records; "
                f"{success} are linked to positive and {failure} to negative visible outcomes. "
                f"The evidence structure spans {clusters} distinct visible action clusters. "
                "Interpretation is scoped to match-local variant separation and source-bound process context."
                + challenge_note
                + horizon_note
                + _mechanism_maturity_sentence(row, language)
                + _mechanism_same_grammar_context_sentence(row, teams, language)
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
            card_class = (
                "SINIRLI KARŞILAŞTIRMA"
                if single_episode_only
                else (
                    "GENİŞ BAĞLAM KARŞILAŞTIRMASI"
                    if broad_context_only
                    else "ANA MEKANİZMA ADAYI"
                )
            )
            card = (
                f"MEKANİZMA KARTI {idx} | SINIF={card_class} | TAKIM={team} | DÖNEM={periods} | "
                f"TRACE={grammar} | PROCESS={process_label} | "
                f"VARYANT={success} olumlu / {failure} olumsuz / {resolved} çözümlenmiş | "
                f"İLK GÖRÜNÜR AYRIŞMA=context L{context_layer}, consequence L{consequence_layer} | "
                f"YAYILIM={spread} bölüm, {clusters} occurrence-disjoint küme | "
                f"COUNTEREVIDENCE={','.join(challenge_reasons) if challenge_reasons else 'açık challenge kaydı yok'} | "
                "CLAIM=maç-içi görünür varyant/mekanizma adayı; kapsam yalnız görünür varyant, süreç ve sonuç bağlantısıdır."
            )
        else:
            card_class = (
                "LIMITED COMPARISON"
                if single_episode_only
                else (
                    "BROAD CONTEXT COMPARISON"
                    if broad_context_only
                    else "MAIN MECHANISM CANDIDATE"
                )
            )
            card = (
                f"MECHANISM CARD {idx} | CLASS={card_class} | TEAM={team} | PERIOD={periods} | "
                f"TRACE={grammar} | PROCESS={process_label} | "
                f"VARIANT={success} positive / {failure} negative / {resolved} resolved | "
                f"FIRST VISIBLE DIVERGENCE=context L{context_layer}, consequence L{consequence_layer} | "
                f"SPREAD={spread} segments, {clusters} occurrence-disjoint clusters | "
                f"COUNTEREVIDENCE={','.join(challenge_reasons) if challenge_reasons else 'no explicit challenge record'} | "
                "CLAIM=match-local visible variant/mechanism candidate; not causal, tactical-plan, or superiority truth."
            )
        football += _mechanism_governance_sentence(language)
        cards.extend([card, football, evidence])
    return cards


def _human_model_context_cards(
    rich: dict[str, Any],
    identity: dict[str, Any],
    language: str,
) -> list[str]:
    c04 = (rich.get("constructs") or {}).get("C04") or {}
    cards: list[str] = []
    for row in (c04.get("model_context_residual_profiles") or []):
        if not isinstance(row, dict):
            continue
        entity = _human_match_local_entity_label(rich, identity, row)
        if not entity:
            continue
        xgt = _human_number(row.get("xgt"))
        xgopp = _human_number(row.get("xgopp"))
        nxg = _human_number(row.get("nxg_observed"))
        rung = str(row.get("causal_ladder_rung") or "")
        rung_label = "Rung-1" if rung.startswith("RUNG_1") else (rung or "UNRESOLVED")
        calibration_unknown = str(row.get("model_calibration_state") or "") == "UNKNOWN_NOT_ADMITTED"
        if language == "tr":
            sentence = (
                f"{entity} — provider model bağlamı: xGT {xgt}, xGOPP {xgopp}, NxG {nxg}. "
                f"Nedensellik sınıfı {rung_label}: kapsam ilişkisel/prediktif bağlamla sınırlıdır; "
                "oyuncu nedensel katkısı bu kapsam dışında kalır."
            )
            if calibration_unknown:
                sentence += " Model kalibrasyon durumu UNKNOWN_NOT_ADMITTED."
            if row.get("model_output_is_fact") is False:
                sentence += " Model çıktısı yalnız model bağlamı olarak ele alınır."
        else:
            sentence = (
                f"{entity} — provider model context: xGT {xgt}, xGOPP {xgopp}, NxG {nxg}. "
                f"Causal classification {rung_label}: scope is limited to associational/predictive context; "
                "causal player contribution remains outside this scope."
            )
            if calibration_unknown:
                sentence += " Model calibration state is UNKNOWN_NOT_ADMITTED."
            if row.get("model_output_is_fact") is False:
                sentence += " Model output is treated as model context only."
        cards.append(sentence)
    return cards


def _human_c02_cards(
    rich: dict[str, Any],
    identity: dict[str, Any],
    language: str,
) -> list[str]:
    c02 = (rich.get("constructs") or {}).get("C02") or {}
    rows = [
        ("PLAYER", c02.get("representative_actor_argument")),
        ("DYAD", c02.get("representative_dyad_argument")),
    ]
    actor_labels = _human_admitted_actor_labels(identity)
    cards: list[str] = []
    for entity_type, candidate in rows:
        if not isinstance(candidate, dict):
            continue
        actor_ids = [
            str(value).strip()
            for value in (candidate.get("actor_identity_candidate_ids") or [])
            if str(value).strip()
        ]
        resolved_names = [actor_labels.get(actor_id) for actor_id in actor_ids]
        if not actor_ids or any(not name for name in resolved_names):
            continue
        names = " + ".join(str(name) for name in resolved_names)
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
            evidence += (
                ". Bu profil maç-içi betimleyici association yüzeyidir ve analyst-review önceliği üretir. "
                "Oyuncu adı yalnız kabul edilmiş maç-içi oyuncu etiketidir; global/cross-match oyuncu kimliği bu kartın kapsamı dışındadır."
            )
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
            evidence += (
                ". This profile is a match-local descriptive association surface for analyst review. "
                "The player name is only an admitted actor-identity label; global/cross-match player identity remains outside scope."
            )
        cards.extend([football, evidence])
    return cards


def _human_player_function_cards(
    rich: dict[str, Any],
    identity: dict[str, Any],
    language: str,
    *,
    per_team_limit: int = 3,
) -> list[str]:
    c02 = (rich.get("constructs") or {}).get("C02") or {}
    profiles = [
        row for row in (c02.get("player_function_profiles") or [])
        if isinstance(row, dict) and row.get("profile_has_any_context") is True
    ]
    if not profiles or per_team_limit <= 0:
        return []

    teams = _human_team_labels(identity)
    admitted_actor_labels = _human_admitted_actor_labels(identity)
    score_state_surface = rich.get("player_score_state_process_participation") or {}
    score_state_profiles = [
        row for row in (score_state_surface.get("profiles") or [])
        if isinstance(row, dict)
    ]
    score_state_by_actor: dict[str, list[dict[str, Any]]] = {}
    for score_row in score_state_profiles:
        actor_id = str(score_row.get("actor_identity_candidate_id") or "").strip()
        if actor_id:
            score_state_by_actor.setdefault(actor_id, []).append(score_row)

    function_review_by_actor: dict[str, dict[str, Any]] = {
        str(row.get("actor_identity_candidate_id") or "").strip(): row
        for row in (score_state_surface.get("function_hypothesis_review_candidates") or [])
        if isinstance(row, dict)
        and str(row.get("actor_identity_candidate_id") or "").strip()
        and str(row.get("review_state") or "")
        == "MATCH_LOCAL_FUNCTION_CONTEXT_VARIATION_REVIEW_CANDIDATE"
        and row.get("creates_new_evidence") is False
        and row.get("can_authorize_player_value_claim") is False
    }

    state_function_evidence = (
        identity.get("__spatial_progression_evidence__")
        if isinstance(identity.get("__spatial_progression_evidence__"), dict)
        else {}
    )
    state_function_by_actor: dict[str, dict[str, Any]] = {
        str(row.get("actor_identity_candidate_id") or "").strip(): row
        for row in (state_function_evidence.get("actor_visible_state_change_function_profiles") or [])
        if isinstance(row, dict)
        and str(row.get("actor_identity_candidate_id") or "").strip()
    }

    by_team: dict[str, list[dict[str, Any]]] = {}
    for row in profiles:
        team_id = str(row.get("team_identity_candidate_id") or "").strip()
        if not team_id:
            continue
        by_team.setdefault(team_id, []).append(row)

    preferred_metrics = [
        ("progressive_passes", "progressive pass", "progressive passes"),
        ("chances_created", "yaratılan şans", "chances created"),
        ("shots", "şut", "shots"),
        ("goals", "gol", "goals"),
        ("ball_recoveries", "top kazanımı", "ball recoveries"),
        ("lost_balls", "top kaybı", "ball losses"),
    ]

    cards: list[str] = []
    for team_id, rows in sorted(by_team.items(), key=lambda item: teams.get(item[0], item[0])):
        ranked = sorted(
            rows,
            key=lambda row: (
                -sum(int(v or 0) for v in (row.get("process_participation_counts") or {}).values()),
                str(row.get("actor_label") or ""),
            ),
        )[:per_team_limit]
        team_name = teams.get(team_id, team_id)
        for row in ranked:
            actor_id = str(row.get("actor_identity_candidate_id") or "").strip()
            actor = admitted_actor_labels.get(actor_id)
            if not actor:
                continue
            process_counts = row.get("process_participation_counts") or {}
            shot_counts = row.get("shot_ending_process_participation_counts") or {}
            process_bits = [
                f"{_football_family_label(family, language)} {int(count or 0)}"
                for family, count in sorted(
                    process_counts.items(),
                    key=lambda item: (-int(item[1] or 0), str(item[0])),
                )
                if int(count or 0) > 0
            ][:3]
            shot_bits = [
                f"{_football_family_label(family, language)} {int(count or 0)}"
                for family, count in sorted(
                    shot_counts.items(),
                    key=lambda item: (-int(item[1] or 0), str(item[0])),
                )
                if int(count or 0) > 0
            ][:3]

            score_rows = sorted(
                score_state_by_actor.get(actor_id, []),
                key=lambda value: (
                    -int(value.get("visible_process_participation_n") or 0),
                    -int(value.get("shot_ending_process_participation_n") or 0),
                    float(value.get("score_segment_start_second_candidate") or 0.0),
                ),
            )[:2]
            score_bits: list[str] = []
            for score_row in score_rows:
                score_text = _score_state_human(score_row.get("score_state_candidate"), language)
                if not score_text:
                    continue
                visible_n = int(score_row.get("visible_process_participation_n") or 0)
                shot_n = int(score_row.get("shot_ending_process_participation_n") or 0)
                if language == "tr":
                    score_bits.append(f"{score_text}: {visible_n} görünür süreç katılımı / {shot_n} şut bağlantılı")
                else:
                    score_bits.append(f"{score_text}: {visible_n} visible process participations / {shot_n} shot-linked")

            state_profile = state_function_by_actor.get(actor_id) or {}
            state_counts = state_profile.get("visible_state_change_function_counts") or {}
            preserve_n = int(state_counts.get("VISIBLE_SAME_TEAM_CONTINUATION_CANDIDATE") or 0)
            amplify_n = int(state_counts.get("VISIBLE_STATE_ADVANCEMENT_CONTINUATION_CANDIDATE") or 0) + int(
                state_counts.get("VISIBLE_ADVANCED_ACCESS_CONTINUATION_CANDIDATE") or 0
            )
            exploit_n = int(state_counts.get("VISIBLE_ADVANTAGE_EXPLOITATION_CANDIDATE") or 0)
            loss_n = int(state_counts.get("VISIBLE_ADVANTAGE_LOSS_OR_HANDOVER_CANDIDATE") or 0)
            review_n = int(state_counts.get("VISIBLE_STATE_CHANGE_REVIEW_REQUIRED_CANDIDATE") or 0)
            unresolved_n = int(state_counts.get("VISIBLE_STATE_CHANGE_UNRESOLVED_NO_FOLLOW_UP_CANDIDATE") or 0)
            state_function_bit = ""
            if state_counts:
                if language == "tr":
                    state_function_bit = (
                        f" Oyuncuya bağlanmış görünür durum-değişimi adayları: koruma-benzeri {preserve_n}, "
                        f"büyütme/ilerletme-benzeri {amplify_n}, kullanma-benzeri {exploit_n}, "
                        f"kayıp/rakibe geçiş {loss_n}, review {review_n}, çözümlenmemiş {unresolved_n}. "
                        "CREATE=UNKNOWN; DENY=UNKNOWN."
                    )
                else:
                    state_function_bit = (
                        f" Actor-bound visible state-change candidates: preserve-like {preserve_n}, "
                        f"amplify/advance-like {amplify_n}, exploit-like {exploit_n}, "
                        f"loss/handover {loss_n}, review {review_n}, unresolved {unresolved_n}. "
                        "CREATE=UNKNOWN; DENY=UNKNOWN."
                    )

            review_contract = function_review_by_actor.get(actor_id) or {}
            function_review_bit = ""
            if review_contract:
                state_n = int(review_contract.get("observed_score_state_context_n") or 0)
                family_n = int(review_contract.get("observed_process_family_n") or 0)
                if language == "tr":
                    function_review_bit = (
                        f" İşlev inceleme adayı: {state_n} admitted skor bağlamında {family_n} görünür süreç ailesi izlendi "
                        "ve süreç bileşimi bağlamlar arasında farklılaştı. "
                        "Bu adayın kapsamı maç-içi görünür işlev değişimidir; oyuncu değeri, kalıcı rol, off-ball rol ve "
                        "nedensel katkı yorumları için ayrı evidence gerekir. "
                        "Alternatif açıklamalar arasında skor durumlarındaki oyuncu maruziyeti, takım süreç fırsat bileşimi, "
                        "rakip/maç bağlamı ve shared-process dependency açık tutulur. "
                        "Analist aksiyonu: aynı oyuncunun görünür süreç-aile katılımını skor bağlamları arasında karşılaştır; "
                        "fırsat bileşimi, consequence bağlamı, dependency ve exposure sınırlarını birlikte kontrol et."
                    )
                else:
                    function_review_bit = (
                        f" Function review candidate: {state_n} admitted score contexts contain {family_n} visible process families "
                        "and the visible process mix varies across those contexts. "
                        "The review scope is match-local visible function variation; player value, persistent role, off-ball role, "
                        "and causal-contribution interpretations require separate evidence. "
                        "Alternative explanations keep player exposure, team process-opportunity mix, opponent/match context, and "
                        "shared-process dependency open. "
                        "Analyst action: compare the same player's visible process-family participation across score contexts, then "
                        "review opportunity mix, consequence context, dependency, and exposure limits together."
                    )

            metrics = _player_profile_metric_values(row)
            metric_bits: list[str] = []
            for key, tr_label, en_label in preferred_metrics:
                if key not in metrics:
                    continue
                raw = metrics[key]
                if raw in (None, "", "-"):
                    continue
                label = tr_label if language == "tr" else en_label
                metric_bits.append(f"{label}={_human_number(raw)}")
                if len(metric_bits) >= 6:
                    break

            if language == "tr":
                text = (
                    f"{team_name} — {actor}: görünür süreç katılımı "
                    + (", ".join(process_bits) if process_bits else "çözümlenmemiş")
                    + "."
                )
                if shot_bits:
                    text += " Şut bağlantılı süreç katılımı: " + ", ".join(shot_bits) + "."
                if score_bits:
                    text += " Skor-durumu bağlamı: " + "; ".join(score_bits) + "."
                if metric_bits:
                    text += " Aggregate fonksiyon bağlamı: " + ", ".join(metric_bits) + "."
                text += state_function_bit
                text += function_review_bit
                text += (
                    " Bu kart yalnız maç-içi görünür işlev bağlamıdır. İsim yalnız kabul edilmiş maç-içi oyuncu etiketidir; "
                    "global/cross-match oyuncu kimliği bu kartın kapsamı dışındadır. Oyuncu niteliği ve kalıcı/taktik rol yorumu "
                    "bu kapsamın dışındadır. Skor-durumu satırları görülen katılımı sayar; görünmeyen katılım saha-dışı "
                    "yokluk kanıtı olarak kullanılmaz. Nedensel katkı yorumu kapsam dışındadır; "
                    "substitution timeline otoritesi olmadığı için per-90 süreç oranı üretilmez."
                )
            else:
                text = (
                    f"{team_name} — {actor}: visible process participation "
                    + (", ".join(process_bits) if process_bits else "unresolved")
                    + "."
                )
                if shot_bits:
                    text += " Shot-linked process participation: " + ", ".join(shot_bits) + "."
                if score_bits:
                    text += " Score-state context: " + "; ".join(score_bits) + "."
                if metric_bits:
                    text += " Aggregate function context: " + ", ".join(metric_bits) + "."
                text += state_function_bit
                text += function_review_bit
                text += (
                    " This is match-local function context only. The name is only an admitted actor-identity label; "
                    "global/cross-match player identity remains outside scope. Player quality and persistent/tactical-role interpretation "
                    "remain outside scope. Score-state rows count visible participation only; missing participation is not used "
                    "as proof of off-field absence. Causal-contribution interpretation remains outside scope, "
                    "and no per-90 process rate is produced without substitution-timeline authority."
                )
            cards.append(text)
    return cards


def _human_player_mechanism_link_cards(
    mechanism_graph: dict[str, Any],
    rich: dict[str, Any],
    identity: dict[str, Any],
    language: str,
    *,
    limit: int = 6,
) -> list[str]:
    if limit <= 0:
        return []
    c02 = (rich.get("constructs") or {}).get("C02") or {}
    admitted_actor_labels = _human_admitted_actor_labels(identity)
    profiles_by_actor = {
        str(row.get("actor_identity_candidate_id") or "").strip(): row
        for row in (c02.get("player_function_profiles") or [])
        if isinstance(row, dict)
        and str(row.get("actor_identity_candidate_id") or "").strip()
    }
    cards = [
        row for row in (mechanism_graph.get("cards") or [])
        if isinstance(row, dict)
    ]
    result: list[str] = []
    for card in sorted(cards, key=lambda row: int(row.get("card_index") or 0)):
        player_context = card.get("player_context") or {}
        actor_id = str(player_context.get("actor_identity_candidate_id") or "").strip()
        profile = profiles_by_actor.get(actor_id)
        actor = admitted_actor_labels.get(actor_id)
        if not actor_id or not isinstance(profile, dict) or not actor:
            continue
        team = ", ".join(str(v) for v in (card.get("team_labels") or []) if str(v))
        periods = ", ".join(
            _period_human(v, language)
            for v in (card.get("period_candidates") or [])
        ) or _period_human(None, language)
        grammar_tokens = [str(v) for v in (card.get("trace_grammar_tokens") or []) if str(v)]
        trace = _grammar_human(grammar_tokens, language) if grammar_tokens else str(card.get("trace_human_tr") or "UNKNOWN")
        resolved = int(card.get("resolved_variant_n") or 0)
        positive = int(card.get("positive_visible_variant_n") or 0)
        negative = int(card.get("negative_visible_variant_n") or 0)
        score = _score_state_human(
            (card.get("safe_finding_context") or {}).get("score_state_candidate"),
            language,
        )
        process_state = str(card.get("process_context_binding_state") or "")
        classification = str(card.get("classification") or "")
        if classification == "LIMITED_COMPARISON":
            class_text = "sınırlı karşılaştırma" if language == "tr" else "limited comparison"
        elif process_state == "AMBIGUOUS_MULTI_PROCESS_FAMILY_CONTEXT":
            class_text = "geniş bağlam karşılaştırması" if language == "tr" else "broad context comparison"
        else:
            class_text = "ana mekanizma adayı" if language == "tr" else "main mechanism candidate"

        if language == "tr":
            text = (
                f"{class_text}: {actor}"
                + (f", {team}" if team else "")
                + f", {periods}; {trace}. "
                f"{resolved} çözümlenmiş varyant; {positive} olumlu / {negative} olumsuz görünür sonuç."
            )
            if score:
                text += f" Skor bağlamı: {score}."
            text += (
                " Bu bağlantı kaynak-bağlı oyuncu locator + varyant bağlamıdır. "
                "İsim yalnız kabul edilmiş maç-içi oyuncu etiketidir; global/cross-match oyuncu kimliği bu kartın kapsamı dışındadır. "
                "Oyuncu niteliği ve nedensel katkı yorumu kapsam dışındadır."
            )
        else:
            text = (
                f"{class_text}: {actor}"
                + (f", {team}" if team else "")
                + f", {periods}; {trace}. "
                f"{resolved} resolved variants; {positive} positive / {negative} negative visible outcomes."
            )
            if score:
                text += f" Score context: {score}."
            text += (
                " This source-bound mechanism link uses only the actor locator plus visible variant context. "
                "The name is only an admitted actor-identity label; global/cross-match player identity remains outside scope. "
                "Player-quality and causal-contribution interpretation remain outside scope."
            )
        result.append(text)
        if len(result) >= limit:
            break
    return result


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


def build_graph_ready_mechanism_cards_payload(
    output_root: str | Path,
    full_spine: dict[str, Any],
    *,
    analyst_question_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(output_root)
    if not _declared_current(full_spine, FEATURE_DELTA_JSON):
        return {
            "module_id": "mechanism_cards_graph_ready_v1",
            "status": "NOT_EVALUATED",
            "cards": [],
            "card_count": 0,
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

    payload = _load_json(root / FEATURE_DELTA_JSON)
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
    identity = _load_json(root / IDENTITY_JSON) if _declared_current(full_spine, IDENTITY_JSON) else {}
    teams = _human_team_labels(identity)
    rich_payload = (
        _load_json(root / RICH_MULTIFORMAT_JSON)
        if _declared_current(full_spine, RICH_MULTIFORMAT_JSON)
        else {}
    )
    player_profiles_by_actor = _player_function_profiles_by_actor(rich_payload)
    admitted_actor_labels = _human_admitted_actor_labels(identity)
    safe_context_by_family = _mechanism_safe_context_by_family(
        root,
        full_spine,
        process_variant_payload,
    )

    shortlist = build_mechanism_story_review_shortlist(
        payload,
        analyst_output_claim_payload=analyst_output or None,
        process_variant_payload=process_variant_payload or None,
        process_participation_payload=process_participation_payload or None,
        variant_feature_challenge_payload=variant_feature_challenge_payload or None,
        analyst_question_payload=analyst_question_payload,
        limit=5,
    )
    source_records = {
        str(record.get("grammar_stable_variant_feature_delta_id") or ""): record
        for record in (payload.get("grammar_stable_variant_feature_delta_records") or [])
        if isinstance(record, dict)
    }

    cards: list[dict[str, Any]] = []
    for idx, row in enumerate(shortlist.get("shortlist") or [], start=1):
        if not isinstance(row, dict):
            continue
        source_record = source_records.get(str(row.get("source_mechanism_review_ref") or ""), {})
        team_ids = [str(v) for v in (row.get("team_identity_candidate_ids") or []) if str(v)]
        process_counts = dict(row.get("process_family_episode_presence_counts") or {})
        support_state = str(row.get("review_support_state") or "")
        single_episode_only = support_state.startswith("SINGLE_EPISODE_")
        family_ref = str(row.get("source_process_variant_family_ref") or "")
        safe_context = safe_context_by_family.get(family_ref, {})
        actor_locator = _select_actor_locator(source_record)
        actor_ref = _focus_actor_ref(actor_locator)
        actor_profile = (
            player_profiles_by_actor.get(actor_ref, {})
            if actor_ref
            else {}
        )
        actor_metrics = (
            _player_profile_metric_values(actor_profile)
            if isinstance(actor_profile, dict)
            else {}
        )
        actor_label = (
            admitted_actor_labels.get(actor_ref)
            if actor_ref
            else None
        )
        actor_process_counts = (
            ((actor_profile.get("function_dimensions") or {}).get("PROCESS") or {}).get(
                "process_participation_counts"
            )
            if isinstance(actor_profile, dict)
            else {}
        ) or {}
        cards.append({
            "card_index": idx,
            "classification": "LIMITED_COMPARISON" if single_episode_only else "MAIN_MECHANISM_CANDIDATE",
            "source_mechanism_review_ref": row.get("source_mechanism_review_ref"),
            "source_process_variant_family_ref": family_ref or None,
            "source_first_supported_branch_divergence_refs": [
                str(v)
                for v in (safe_context.get("source_first_supported_branch_divergence_refs") or [])
                if str(v)
            ],
            "source_safe_finding_handoff_refs": [
                str(v)
                for v in (safe_context.get("safe_finding_handoff_refs") or [])
                if str(v)
            ],
            "team_identity_candidate_ids": team_ids,
            "team_labels": [teams.get(ref, ref) for ref in team_ids],
            "period_candidates": [str(v) for v in (row.get("period_candidates") or [])],
            "trace_grammar_tokens": [str(v) for v in (row.get("grammar_signature_tokens") or [])],
            "trace_human_tr": _grammar_human(list(row.get("grammar_signature_tokens") or []), "tr"),
            "process_context_binding_state": row.get("process_context_binding_state"),
            "single_process_family_candidate": row.get("single_process_family_candidate"),
            "process_family_episode_presence_counts": process_counts,
            "safe_finding_context": {
                "safe_finding_match_count": int(safe_context.get("safe_finding_match_count") or 0),
                "safe_finding_handoff_refs": [
                    str(v)
                    for v in (safe_context.get("safe_finding_handoff_refs") or [])
                    if str(v)
                ],
                "source_first_supported_branch_divergence_refs": [
                    str(v)
                    for v in (safe_context.get("source_first_supported_branch_divergence_refs") or [])
                    if str(v)
                ],
                "source_process_variant_family_ref": (
                    safe_context.get("source_process_variant_family_ref")
                ),
                "score_state_consensus": safe_context.get("score_state_consensus") is True,
                "score_state_candidate": safe_context.get("score_state_candidate"),
                "provider_process_family_consensus": (
                    safe_context.get("provider_process_family_consensus") is True
                ),
                "provider_process_family_candidates": [
                    str(v)
                    for v in (safe_context.get("provider_process_family_candidates") or [])
                    if str(v)
                ],
                "provider_process_context_partial_count": int(
                    safe_context.get("provider_process_context_partial_count") or 0
                ),
                "preoutcome_context_state_counts": dict(
                    safe_context.get("preoutcome_context_state_counts") or {}
                ),
                "shared_ancestor_overlap_handoff_count": int(
                    safe_context.get("shared_ancestor_overlap_handoff_count") or 0
                ),
                "no_shared_ancestor_within_tracked_scope_handoff_count": int(
                    safe_context.get("no_shared_ancestor_within_tracked_scope_handoff_count") or 0
                ),
                "ancestry_unresolved_handoff_count": int(
                    safe_context.get("ancestry_unresolved_handoff_count") or 0
                ),
                "shared_ancestor_ref_count": int(
                    safe_context.get("shared_ancestor_ref_count") or 0
                ),
                "bounded_ancestry_distinctness_is_independence_proof": False,
                "shared_ancestor_overlap_can_increase_support": False,
                "representative_support_sequence_refs": [
                    str(v)
                    for v in (safe_context.get("representative_support_sequence_refs") or [])
                    if str(v)
                ],
                "representative_counterexample_pair_refs": [
                    str(v)
                    for v in (safe_context.get("representative_counterexample_pair_refs") or [])
                    if str(v)
                ],
                "representative_counterexample_sequence_refs": [
                    str(v)
                    for v in (safe_context.get("representative_counterexample_sequence_refs") or [])
                    if str(v)
                ],
                "representative_support_sequence_locators": [
                    dict(v)
                    for v in (safe_context.get("representative_support_sequence_locators") or [])
                    if isinstance(v, dict)
                ],
                "representative_counterexample_sequence_locators": [
                    dict(v)
                    for v in (safe_context.get("representative_counterexample_sequence_locators") or [])
                    if isinstance(v, dict)
                ],
                "representative_links_create_independent_support": False,
                "emit_decision_count": int(safe_context.get("emit_decision_count") or 0),
                "claim_output_allowed_count": int(
                    safe_context.get("claim_output_allowed_count") or 0
                ),
                "context_is_preoutcome_only": True,
                "creates_new_evidence": False,
                "creates_independent_support": False,
                "can_change_shortlist_selection": False,
                "can_change_safe_finding_decision": False,
                "can_authorize_emit": False,
            },
            "player_context": {
                "actor_identity_candidate_id": actor_ref,
                "actor_label": actor_label,
                "actor_label_scope": (
                    "IDENTITY_OWNER_MATCH_LOCAL_OR_VALIDATED_HUMAN_LABEL"
                    if actor_label
                    else "IDENTITY_OWNER_LABEL_UNRESOLVED"
                ),
                "actor_label_is_global_cross_match_identity_truth": False,
                "actor_locator": actor_locator,
                "aggregate_metric_values": actor_metrics,
                "process_participation_counts": dict(actor_process_counts),
                "aggregate_context_is_mechanism_action_identity": False,
                "aggregate_context_is_player_quality_truth": False,
                "aggregate_context_is_causal_contribution_truth": False,
                "creates_new_evidence": False,
                "can_authorize_emit": False,
            },
            "context_review": _mechanism_context_review_payload(
                source_record,
                rich_payload,
                team_ids,
                row.get("single_process_family_candidate"),
                safe_context,
            ),
            "evidence_maturity_profile": dict(row.get("evidence_maturity_profile") or {}),
            "resolved_variant_n": int(row.get("resolved_variant_count") or 0),
            "positive_visible_variant_n": int(row.get("success_resolved_variant_count") or 0),
            "negative_visible_variant_n": int(row.get("failure_resolved_variant_count") or 0),
            "visible_episode_spread_n": int(row.get("visible_episode_spread_count") or 0),
            "occurrence_disjoint_support_cluster_n": int(row.get("occurrence_disjoint_support_cluster_count") or 0),
            "success_failure_supported_branch_divergence_n": int(row.get("success_failure_supported_branch_divergence_count") or 0),
            "first_visible_context_difference_layer_candidate": source_record.get("first_supported_context_difference_layer_candidate"),
            "first_visible_consequence_difference_layer_candidate": source_record.get("first_supported_consequence_difference_layer_candidate"),
            "mechanism_challenge_record_n": int(row.get("mechanism_challenge_record_count") or 0),
            "counterevidence_reason_codes": [
                str(v) for v in (row.get("mechanism_challenge_reason_codes") or []) if str(v)
            ],
            "counter_scenario_candidates": [
                str(v) for v in (row.get("mechanism_counter_scenario_candidates") or []) if str(v)
            ],
            "withdrawal_conditions": [
                str(v) for v in (row.get("mechanism_withdrawal_conditions") or []) if str(v)
            ],
            "graph_recommendations": [
                "TRACE_VARIANT_SMALL_MULTIPLES",
                "VISIBLE_OUTCOME_SPLIT_BAR",
                "CONTEXT_OUTCOME_CONTRAST_HEATMAP",
                "FIRST_VISIBLE_DIVERGENCE_PANEL",
            ],
            "graphability_state": "GRAPH_READY_WITH_REVIEW",
            "graph_context_lineage_state": (
                "SAFE_FINDING_CONTEXT_BOUND"
                if safe_context
                else "NO_SAFE_FINDING_CONTEXT_BOUND"
            ),
            "analyst_review_contract": {
                "what_visible": {
                    "trace_grammar_tokens": [
                        str(v) for v in (row.get("grammar_signature_tokens") or [])
                    ],
                    "process_context_binding_state": row.get("process_context_binding_state"),
                    "single_process_family_candidate": row.get("single_process_family_candidate"),
                    "resolved_variant_n": int(row.get("resolved_variant_count") or 0),
                    "positive_visible_variant_n": int(
                        row.get("success_resolved_variant_count") or 0
                    ),
                    "negative_visible_variant_n": int(
                        row.get("failure_resolved_variant_count") or 0
                    ),
                    "first_visible_context_difference_layer_candidate": source_record.get(
                        "first_supported_context_difference_layer_candidate"
                    ),
                    "first_visible_consequence_difference_layer_candidate": source_record.get(
                        "first_supported_consequence_difference_layer_candidate"
                    ),
                },
                "evidence_lineage": {
                    "source_mechanism_review_ref": row.get("source_mechanism_review_ref"),
                    "source_process_variant_family_ref": family_ref or None,
                    "source_first_supported_branch_divergence_refs": [
                        str(v)
                        for v in (safe_context.get("source_first_supported_branch_divergence_refs") or [])
                        if str(v)
                    ],
                    "source_safe_finding_handoff_refs": [
                        str(v)
                        for v in (safe_context.get("safe_finding_handoff_refs") or [])
                        if str(v)
                    ],
                    "lineage_creates_new_evidence": False,
                    "lineage_strengthens_claim": False,
                },
                "support": {
                    "visible_episode_spread_n": int(
                        row.get("visible_episode_spread_count") or 0
                    ),
                    "occurrence_disjoint_support_cluster_n": int(
                        row.get("occurrence_disjoint_support_cluster_count") or 0
                    ),
                    "success_failure_supported_branch_divergence_n": int(
                        row.get("success_failure_supported_branch_divergence_count") or 0
                    ),
                    "safe_finding_match_count": int(
                        safe_context.get("safe_finding_match_count") or 0
                    ),
                },
                "counterevidence": {
                    "reason_codes": [
                        str(v)
                        for v in (row.get("mechanism_challenge_reason_codes") or [])
                        if str(v)
                    ],
                    "counter_scenario_candidates": [
                        str(v)
                        for v in (row.get("mechanism_counter_scenario_candidates") or [])
                        if str(v)
                    ],
                },
                "uncertainty": {
                    "provider_process_context_partial_count": int(
                        safe_context.get("provider_process_context_partial_count") or 0
                    ),
                    "score_state_consensus": safe_context.get("score_state_consensus") is True,
                    "provider_process_family_consensus": (
                        safe_context.get("provider_process_family_consensus") is True
                    ),
                    "independent_support_proven": False,
                    "branch_context_completeness_promoted": False,
                    "causal_explanation_admitted": False,
                },
                "safe_meaning": "MATCH_LOCAL_VISIBLE_VARIANT_DIFFERENCE_FOR_ANALYST_REVIEW",
                "forbidden_inference": [
                    "CAUSALITY",
                    "TACTICAL_PLAN_TRUTH",
                    "SUPERIORITY_TRUTH",
                    "PHYSICAL_SHAPE_TRUTH",
                    "PLAYER_QUALITY_TRUTH",
                ],
                "withdrawal_conditions": [
                    str(v)
                    for v in (row.get("mechanism_withdrawal_conditions") or [])
                    if str(v)
                ],
                "analyst_action": [
                    "REVIEW_FIRST_VISIBLE_DIVERGENCE_ACROSS_COMPARABLE_VARIANTS",
                    "CHECK_COUNTEREVIDENCE_AND_PARTIAL_CONTEXT",
                    "INSPECT_PLAYER_CONTEXT_ONLY_AS_MATCH_LOCAL_CONTEXT",
                ],
                "creates_new_evidence": False,
                "creates_independent_support": False,
                "can_change_shortlist_selection": False,
                "can_change_safe_finding_decision": False,
                "can_authorize_emit": False,
            },
            "claim_ceiling": "MATCH_LOCAL_VISIBLE_VARIANT_MECHANISM_CANDIDATE_ONLY",
            "player_name_rendering_state": "IDENTITY_OWNER_MATCH_LOCAL_OR_VALIDATED_ONLY",
            "player_name_is_global_cross_match_identity_truth": False,
            "creates_new_evidence": False,
            "can_authorize_emit": False,
            "can_strengthen_claim_ceiling": False,
        })

    return {
        "module_id": "mechanism_cards_graph_ready_v1",
        "status": "REVIEW_REQUIRED" if cards else "NOT_EVALUATED",
        "shortlist_status": shortlist.get("status"),
        "card_count": len(cards),
        "main_mechanism_candidate_count": sum(
            row.get("classification") == "MAIN_MECHANISM_CANDIDATE" for row in cards
        ),
        "limited_comparison_count": sum(
            row.get("classification") == "LIMITED_COMPARISON" for row in cards
        ),
        "cards": cards,
        "analyst_relevance_state": shortlist.get("analyst_relevance_state"),
        "analyst_question_binding_state": shortlist.get("analyst_question_binding_state"),
        "analyst_question_ref": shortlist.get("analyst_question_ref"),
        "question_focus_dimensions": list(shortlist.get("question_focus_dimensions") or []),
        "question_conditioned_attention_order": list(shortlist.get("question_conditioned_attention_order") or []),
        "question_binding_changes_evidence": False,
        "question_binding_changes_support": False,
        "question_binding_changes_claim_ceiling": False,
        "question_binding_can_authorize_emit": False,
        "graphability_does_not_strengthen_evidence": True,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def _hp_clean_football_line(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None

    replacements = {
        "Sistem bu maçta ": "",
        "görünür oyun sürecini takım bağlamına bağlayabildi": "oyun süreci kaydedildi",
        "görünür oyun sürecini": "oyun sürecini",
        "görünür süreç": "oyun süreci",
        "Görünür süreç": "Oyun süreci",
        "görünür kayıp": "top kaybı",
        "görünür kazanım": "top kazanımı",
        "görünür geri kazanım": "top kazanımı",
        "şut bağlantılı son bölüm": "şutla biten hücum",
        "şut bağlantılı": "şutla biten",
        "recovery bağlantılı": "top kazanımıyla devam eden",
        "recovery": "top kazanımı",
        "follow-up": "devam aksiyonu",
        "same-time review": "aynı anda iki takım kaydı",
        "breakdown sonrası rakip takeover": "bozulan hücum sonrası rakibe geçiş",
        "rakibe geçiş": "rakibe geçen devam",
        "PROCESS=": "OYUN BAĞLAMI=",
        "TRACE=": "AKSİYON ZİNCİRİ=",
        "VARYANT=": "ÖRNEKLER=",
        "COUNTEREVIDENCE=": "KARŞI ÖRNEK=",
        "CLAIM=": "ANLAM=",
        "Aggregate fonksiyon bağlamı:": "Maç toplamları:",
        "progressive pass": "ilerletici pas",
        "Per-90": "90 dakika başına",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)

    forbidden_sentence_tokens = (
        "kanit notu", "kanıt notu", "okuma çerçevesi", "admitted", "claim ",
        "claim=", "claim scope", "current-run", "current invocation", "provider",
        "occurrence", "dependency", "runtime", "canonical_event_count",
        "true_action_count", "review-required", "review required", "review ",
        "evidence", "xlsx", "source-bound", "kaynak-bağlı", "emit",
        "construct", "m09", "layer", "candidate_only", "candidate only",
        "global/cross-match", "global identity", "production_release",
    )

    parts = []
    for sentence in text.split(". "):
        cleaned = sentence.strip()
        if not cleaned:
            continue
        low = cleaned.casefold()
        if any(token in low for token in forbidden_sentence_tokens):
            continue
        cleaned = cleaned.replace("görünür ", "").replace("Görünür ", "")
        cleaned = cleaned.replace("_CANDIDATE", "").replace("_", " ")
        cleaned = " ".join(cleaned.split())
        if cleaned:
            parts.append(cleaned.rstrip("."))

    if not parts:
        return None
    return ". ".join(parts) + "."


def _hp_take_clean(lines: list[str], *, limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in lines:
        cleaned = _hp_clean_football_line(raw)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
        if len(result) >= limit:
            break
    return result


def _build_hp_football_report_tr_v0(output_root: str | Path, full_spine: dict[str, Any]) -> str:
    root = Path(output_root)
    rich_current = _rich_surface_current(full_spine)
    rich = full_spine.get("rich_multiformat_analysis_lattice") if rich_current else {}
    rich = rich if isinstance(rich, dict) else {}
    identity = _load_json(root / IDENTITY_JSON) if _declared_current(full_spine, IDENTITY_JSON) else {}

    match_story = _hp_take_clean(
        _human_match_story_cards(rich, identity, "tr") if rich_current else [],
        limit=4,
    )
    team_profile = _hp_take_clean(
        _human_team_process_cards(rich, identity, "tr") if rich_current else [],
        limit=6,
    )
    circulation = _hp_take_clean(
        _human_circulation_fate_cards(rich, identity, "tr") if rich_current else [],
        limit=6,
    )
    route_breadth = _hp_take_clean(
        _human_process_route_breadth_cards(rich, identity, "tr") if rich_current else [],
        limit=4,
    )
    score_state = _hp_take_clean(
        _human_score_state_process_outcome_cards(rich, identity, "tr") if rich_current else [],
        limit=4,
    )
    loss_recovery = _hp_take_clean(
        _human_loss_recovery_score_state_cards(rich, identity, "tr") if rich_current else [],
        limit=6,
    )
    sequence_info = _hp_take_clean(
        _human_sequence_information_cards(rich, identity, "tr") if rich_current else [],
        limit=6,
    )
    process_variants = _hp_take_clean(
        _human_process_variant_board_cards(rich, identity, "tr") if rich_current else [],
        limit=6,
    )
    player_functions = _hp_take_clean(
        _human_player_function_cards(
            rich,
            {
                **identity,
                "__spatial_progression_evidence__": full_spine.get("spatial_progression_evidence") or {},
            },
            "tr",
        ) if rich_current else [],
        limit=6,
    )
    set_pieces = _hp_take_clean(
        _human_set_piece_process_cards(rich, identity, "tr") if rich_current else [],
        limit=4,
    )
    aerial = _hp_take_clean(
        _human_aerial_duel_cards(rich, identity, "tr") if rich_current else [],
        limit=4,
    )

    mechanism_cards = _human_mechanism_cards(root, full_spine, identity, "tr")
    mechanism_highlights = _hp_take_clean(
        _human_match_story_mechanism_highlights(mechanism_cards, "tr", limit=4),
        limit=4,
    )

    lines = [
        "HPFA MAÇ ANALİZİ",
        "=================",
        "",
        "MAÇIN ANA RESMİ",
    ]
    if match_story:
        lines.extend(f"- {line}" for line in match_story)
    elif team_profile:
        lines.extend(f"- {line}" for line in team_profile[:2])
    else:
        lines.append("- Bu maç için güvenli bir ana oyun resmi kurulamadı.")

    lines.extend(["", "TOPLA OYUN — İLERLEME VE ÜRETİM"])
    if circulation:
        lines.extend(f"- {line}" for line in circulation)
    elif team_profile:
        lines.extend(f"- {line}" for line in team_profile)
    else:
        lines.append("- Topla oyunun ilerleme ve üretim yolları bu maçta yeterince ayrıştırılamadı.")

    lines.extend(["", "GÖRÜNÜR SÜREÇ ROTALARI"])
    if route_breadth:
        lines.extend(f"- {line}" for line in route_breadth)
    else:
        lines.append("- Başlangıç ve bitiş bölgesi birlikte çözülebilen süreçlerde güvenli bir rota çeşitliliği özeti oluşmadı.")

    lines.extend(["", "TOP KAYBI VE KAZANIM SONRASI"])
    if loss_recovery:
        lines.extend(f"- {line}" for line in loss_recovery)
    else:
        lines.append("- Top kaybı ve kazanım sonrasındaki devamlar bu maçta güvenli biçimde ayrıştırılamadı.")

    lines.extend(["", "MAÇIN DEĞİŞEN YÜZÜ"])
    if score_state:
        lines.extend(f"- {line}" for line in score_state)
    else:
        lines.append("- Skor değiştikçe oyunun nasıl değiştiğini söylemek için yeterli maç-içi karşılaştırma oluşmadı.")

    lines.extend(["", "TEKRAR EDEN YOLLAR VE VARYANTLAR"])
    if mechanism_highlights:
        lines.extend(f"- {line}" for line in mechanism_highlights)
    elif sequence_info or process_variants:
        lines.extend(f"- {line}" for line in (sequence_info + process_variants)[:6])
    else:
        lines.append("- Aynı probleme verilen farklı çözümleri karşılaştıracak kadar güçlü tekrar eden yol bulunamadı.")

    lines.extend(["", "OYUNCU İŞLEVLERİ"])
    if player_functions:
        lines.extend(f"- {line}" for line in player_functions)
    else:
        lines.append("- Oyuncu işlevlerini takım süreçlerinden ayıracak kadar güçlü maç-içi bağlam oluşmadı.")

    lines.extend(["", "DURAN TOPLAR VE HAVA TOPLARI"])
    if set_pieces or aerial:
        lines.extend(f"- {line}" for line in (set_pieces + aerial)[:6])
    else:
        lines.append("- Duran top ve hava topu bölümünde ana maç hikâyesini değiştiren güçlü bir ayrışma görülmedi.")

    conclusion_pool = mechanism_highlights + match_story + team_profile
    conclusions = _hp_take_clean(conclusion_pool, limit=3)
    lines.extend(["", "SONUÇ — ANALİST NOTU"])
    if conclusions:
        lines.extend(f"- {line}" for line in conclusions)
    else:
        lines.append("- Bu maçta güçlü bir hüküm kurmaktan çok, tekrar izlenmesi gereken oyun ilişkileri öne çıkıyor.")

    lines.extend([
        "",
        "Bu raporun yetkisi bu maçta görülen futbol ilişkileridir. Kalıcı takım veya oyuncu özelliği için daha geniş ve karşılaştırılabilir örneklem gerekir.",
        "",
    ])
    return "\n".join(lines)


def _hp_profile_rows(rich: dict[str, Any]) -> list[dict[str, Any]]:
    c03 = (rich.get("constructs") or {}).get("C03") or {}
    rows: list[dict[str, Any]] = []
    for row in c03.get("team_process_profiles") or []:
        if not isinstance(row, dict):
            continue
        if row.get("process_family_candidate"):
            rows.append(row)
            continue
        team_ref = row.get("team_identity_candidate_id")
        for nested in row.get("process_family_profiles") or []:
            if isinstance(nested, dict):
                item = dict(nested)
                item.setdefault("team_identity_candidate_id", team_ref)
                rows.append(item)
    return rows


def _hp_match_score(rich: dict[str, Any]) -> str | None:
    context = rich.get("score_state_visible_process_outcome_context") or {}
    best: tuple[int, dict[str, Any]] | None = None
    for row in context.get("profiles") or []:
        state = row.get("score_state_candidate")
        if not isinstance(state, dict) or not state:
            continue
        total = sum(int(v or 0) for v in state.values())
        if best is None or total > best[0]:
            best = (total, state)
    if best is None:
        return None
    return " - ".join(f"{_display_label(k)} {int(v or 0)}" for k, v in best[1].items())


def _hp_time_label(second: Any) -> str:
    try:
        minute = max(0, int(float(second) // 60))
    except (TypeError, ValueError):
        return "maçın ilgili bölümü"
    return f"{minute}. dakika civarı"


def _hp_action_label(value: Any) -> str:
    key = str(value or "").strip().upper()
    return {
        "PASS": "pas",
        "DUEL": "ikili mücadele",
        "INTERCEPTION": "pas arası",
        "TURNOVER": "top kaybı",
        "CARRY": "top taşıma",
        "DRIBBLE": "dripling",
        "TACKLE": "müdahale",
        "SHOT": "şut",
        "FOUL": "faul",
        "CROSS": "orta",
        "RECOVERY": "top kazanımı",
        "RESTART": "duran top",
        "CLEARANCE": "uzaklaştırma",
        "GOALKEEPER_ACTION": "kaleci aksiyonu",
    }.get(key, key.replace("_", " ").casefold())


def _hp_period_label(values: Any) -> str:
    periods = {str(v) for v in (values or []) if str(v)}
    if periods == {"1"}:
        return "ilk yarıda"
    if periods == {"2"}:
        return "ikinci yarıda"
    return "maç boyunca"


def _tr_possessive(name: str) -> str:
    vowels = [c for c in name.casefold() if c in "aeıioöuü"]
    last = vowels[-1] if vowels else ""
    suffix = "ın" if last in "aı" else "in" if last in "ei" else "un" if last in "ou" else "ün"
    return f"{name}'{suffix}"


def build_hp_football_report_tr(
    output_root: str | Path,
    full_spine: dict[str, Any],
    *,
    analyst_question_payload: dict[str, Any] | None = None,
) -> str:
    root = Path(output_root)
    rich_current = _rich_surface_current(full_spine)
    rich = full_spine.get("rich_multiformat_analysis_lattice") if rich_current else {}
    rich = rich if isinstance(rich, dict) else {}
    identity = _load_json(root / IDENTITY_JSON) if _declared_current(full_spine, IDENTITY_JSON) else {}
    teams = _human_team_labels(identity)
    actors = _human_admitted_actor_labels(identity)
    profiles = _hp_profile_rows(rich)
    route_breadth = _hp_take_clean(
        _human_process_route_breadth_cards(rich, identity, "tr") if rich_current else [],
        limit=4,
    )
    specialist_cards = _hp_take_clean(
        _human_residual_specialist_cards(rich, identity, "tr") if rich_current else [],
        limit=10,
    )
    actor_concentration_cards = _hp_take_clean(
        _human_process_actor_concentration_cards(root, full_spine, identity, "tr"),
        limit=6,
    )
    fusion_relation_cards = _hp_take_clean(_human_fusion_relation_cards(full_spine, "tr"), limit=2)

    by_team: dict[str, dict[str, dict[str, Any]]] = {}
    for row in profiles:
        team_ref = str(row.get("team_identity_candidate_id") or "")
        family = str(row.get("process_family_candidate") or "")
        if team_ref and family:
            by_team.setdefault(team_ref, {})[family] = row

    lines = ["HPFA MAÇ ANALİZİ", "=================", "", "MAÇIN ANA RESMİ"]
    score = _hp_match_score(rich)
    if score:
        lines.append(f"- Skor: {score}.")

    team_refs = sorted(by_team, key=lambda ref: teams.get(ref, ref))
    positional_rows = []
    for ref in team_refs:
        row = by_team[ref].get("POSITIONAL_ATTACK_CANDIDATE")
        if row:
            positional_rows.append((ref, row))

    if len(positional_rows) >= 2:
        a_ref, a = positional_rows[0]
        b_ref, b = positional_rows[1]
        a_name, b_name = teams.get(a_ref, a_ref), teams.get(b_ref, b_ref)
        a_n, b_n = int(a.get("eligible_process_n") or 0), int(b.get("eligible_process_n") or 0)
        a_sh, b_sh = int(a.get("shot_ending_process_n") or 0), int(b.get("shot_ending_process_n") or 0)
        lines.append(
            f"- {a_name} yerleşik hücumda {a_n}, {b_name} {b_n} ayrı hücum akışı oluşturdu; "
            f"bunların {a_sh} ve {b_sh} tanesi şutla bitti. Bu nedenle maçın sonucu yalnız hücum hacmiyle açıklanmıyor."
        )
    elif positional_rows:
        ref, row = positional_rows[0]
        lines.append(
            f"- {teams.get(ref, ref)} için oyunun ana topla hücum yolu yerleşik hücumdu: "
            f"{int(row.get('eligible_process_n') or 0)} ayrı akışın {int(row.get('shot_ending_process_n') or 0)} tanesi şutla bitti."
        )
    else:
        lines.append("- Maçın ana topla oyun yolunu güvenli biçimde ayıracak kadar güçlü süreç bilgisi oluşmadı.")

    lines.extend(["", "TOPLA OYUN — İLERLEME VE ÜRETİM"])
    for ref in team_refs:
        name = teams.get(ref, ref)
        families = by_team[ref]
        pos = families.get("POSITIONAL_ATTACK_CANDIDATE") or {}
        counter = families.get("COUNTERATTACK_CANDIDATE") or {}
        set_piece = families.get("SET_PIECE_ATTACK_CANDIDATE") or {}
        pos_n, pos_sh = int(pos.get("eligible_process_n") or 0), int(pos.get("shot_ending_process_n") or 0)
        ctr_n, ctr_sh = int(counter.get("eligible_process_n") or 0), int(counter.get("shot_ending_process_n") or 0)
        sp_n, sp_sh = int(set_piece.get("eligible_process_n") or 0), int(set_piece.get("shot_ending_process_n") or 0)
        if pos_n or ctr_n or sp_n:
            lines.append(
                f"- {name}: yerleşik hücum {pos_n} kez görüldü ve {pos_sh} kez şutla bitti; "
                f"kontra atak {ctr_n} kez görüldü ve {ctr_sh} kez şutla bitti; "
                f"duran top hücumu {sp_n} kez görüldü ve {sp_sh} kez şutla bitti."
            )
            if ctr_n and ctr_sh == 0 and pos_sh > 0:
                lines.append(
                    f"- {_tr_possessive(name)} bu maçtaki şut üretimi kontra atak sayısından değil, daha çok yerleşik hücumların son bölümünden geldi."
                )

    lines.extend(["", "GÖRÜNÜR SÜREÇ ROTALARI"])
    if route_breadth:
        lines.extend(f"- {line}" for line in route_breadth)
    else:
        lines.append("- Başlangıç ve bitiş bölgesi birlikte çözülebilen süreçlerde güvenli bir rota çeşitliliği özeti oluşmadı.")

    lines.extend(["", "TOP KAYBI VE KAZANIM SONRASI"])
    loss = rich.get("loss_next_opponent_process_context") or {}
    recovery = rich.get("recovery_next_process_context") or {}
    loss_rows = [r for r in loss.get("rows") or [] if isinstance(r, dict)]
    rec_rows = [r for r in recovery.get("rows") or [] if isinstance(r, dict)]
    for ref in team_refs:
        name = teams.get(ref, ref)
        team_losses = [r for r in loss_rows if ref in (r.get("anchor_team_identity_candidate_ids") or [])]
        next_counts: Counter[str] = Counter()
        for row in team_losses:
            for fam in row.get("next_opponent_process_family_candidates") or []:
                next_counts[_football_family_key(fam)] += 1
        team_rec = [r for r in rec_rows if ref in (r.get("team_identity_candidate_ids") or [])]
        rec_counts: Counter[str] = Counter()
        for row in team_rec:
            for fam in row.get("next_visible_process_family_candidates") or []:
                rec_counts[_football_family_key(fam)] += 1
        loss_detail = ", ".join(
            f"{_football_family_label(fam, 'tr')} {n}" for fam, n in next_counts.most_common()
        ) or "tek bir sonraki hücum tipine güvenli biçimde bağlanamayan örnekler ağırlıkta"
        rec_detail = ", ".join(
            f"{_football_family_label(fam, 'tr')} {n}" for fam, n in rec_counts.most_common()
        ) or "tek bir sonraki hücum tipine güvenli biçimde bağlanamayan örnekler ağırlıkta"
        lines.append(
            f"- {name}: {len(team_losses)} top kaybı sonrasında rakibin ilk net hücum bağlantılarında {loss_detail}. "
            f"{len(team_rec)} top kazanımı sonrasında ise {rec_detail}."
        )
    lines.append("- Buradaki ana soru kayıp sayısı değil; kayıptan sonra rakibe hangi ilk çıkışın bırakıldığı ve takımın buna ne kadar çabuk yeniden temas edebildiğidir.")

    lines.extend(["", "MAÇIN DEĞİŞEN YÜZÜ"])
    mix = rich.get("time_window_process_mix_change_context") or {}
    comparisons = [r for r in mix.get("comparisons") or [] if isinstance(r, dict)]
    for ref in team_refs:
        rows = [r for r in comparisons if str(r.get("team_identity_candidate_id") or "") == ref]
        if not rows:
            continue
        row = max(rows, key=lambda r: float(r.get("composition_total_variation_distance_candidate") or 0))
        deltas = row.get("process_family_count_delta") or {}
        changes = []
        for fam, delta in sorted(deltas.items(), key=lambda item: -abs(int(item[1] or 0))):
            value = int(delta or 0)
            if value:
                direction = "arttı" if value > 0 else "azaldı"
                changes.append(f"{_football_family_label(fam, 'tr')} {abs(value)} akış {direction}")
        if changes:
            lines.append(
                f"- {teams.get(ref, ref)} için oyun bileşiminin en belirgin farklılaştığı bölüm {_hp_time_label(row.get('current_window_start_second_candidate'))}: "
                + "; ".join(changes[:3]) + "."
            )
    lines.append("- Bu değişim maçın farklı bölümlerinde kullanılan hücum yollarının farklılaştığını gösterir. Taktik değişiklik veya momentum yorumu için ek bağlam gerekir.")

    lines.extend(["", "TEKRAR EDEN YOLLAR VE VARYANTLAR"])
    feature = _load_json(root / FEATURE_DELTA_JSON)
    records = [r for r in feature.get("grammar_stable_variant_feature_delta_records") or [] if isinstance(r, dict)]
    mechanism_cards = (
        _human_mechanism_cards(
            root,
            full_spine,
            identity,
            "tr",
            analyst_question_payload=analyst_question_payload,
        )
        if records
        else []
    )
    mechanism_highlights = _hp_take_clean(
        _human_match_story_mechanism_highlights(mechanism_cards, "tr", limit=4),
        limit=4,
    )
    if mechanism_highlights:
        lines.extend(f"- {line}" for line in mechanism_highlights)

    records.sort(
        key=lambda r: (
            int(r.get("visible_episode_spread_count") or 0),
            int(r.get("resolved_variant_count") or 0),
        ),
        reverse=True,
    )
    rendered = len(mechanism_highlights)
    for row in records:
        team_ids = [str(v) for v in row.get("team_identity_candidate_ids") or [] if str(v)]
        if not team_ids:
            continue
        tokens = []
        for token in row.get("grammar_signature_tokens") or []:
            raw = str(token).replace("LAYER[", "").replace("]", "").replace("+", " + ")
            tokens.append(" / ".join(_hp_action_label(part.strip()) for part in raw.split("|")))
        if not tokens:
            continue
        team = teams.get(team_ids[0], team_ids[0])
        spread = int(row.get("visible_episode_spread_count") or 0)
        resolved = int(row.get("resolved_variant_count") or 0)
        if spread <= 0 or resolved <= 1:
            continue
        trace = " → ".join(tokens)
        lines.append(
            f"- {_tr_possessive(team)} {trace} bağlantısı {_hp_period_label(row.get('period_candidates'))} maçın {spread} ayrı bölümünde yeniden görüldü. "
            f"{resolved} karşılaştırılabilir örneğin sonuçları aynı olmadı; bu nedenle asıl inceleme noktası ilk aksiyon değil, bağlantının hangi koşulda devam edip hangi koşulda koptuğu."
        )
        rendered += 1
        if rendered >= 4:
            break
    if not rendered:
        lines.append("- Aynı futbol probleminin farklı sonuçlara gittiği yeterince güçlü tekrar eden bir bağlantı bulunmadı.")

    lines.extend(["", "OYUNCU İŞLEVLERİ"])
    player_surface = rich.get("player_score_state_process_participation") or {}
    function_review_by_actor = {
        str(row.get("actor_identity_candidate_id") or "").strip(): row
        for row in (player_surface.get("function_hypothesis_review_candidates") or [])
        if isinstance(row, dict)
        and str(row.get("actor_identity_candidate_id") or "").strip()
        and str(row.get("review_state") or "")
        == "MATCH_LOCAL_FUNCTION_CONTEXT_VARIATION_REVIEW_CANDIDATE"
        and row.get("creates_new_evidence") is False
        and row.get("can_authorize_player_value_claim") is False
    }
    aggregate: dict[str, dict[str, Any]] = {}
    for row in player_surface.get("profiles") or []:
        if not isinstance(row, dict):
            continue
        ref = str(row.get("actor_identity_candidate_id") or "")
        if not ref:
            continue
        item = aggregate.setdefault(ref, {
            "actor_ref": ref,
            "team_ref": str(row.get("team_identity_candidate_id") or ""),
            "label": actors.get(ref) or _display_label(row.get("actor_label_candidate") or ref),
            "families": Counter(),
            "shot": 0,
            "total": 0,
        })
        item["total"] += int(row.get("visible_process_participation_n") or 0)
        item["shot"] += int(row.get("shot_ending_process_participation_n") or 0)
        for fam, n in (row.get("process_family_counts") or {}).items():
            item["families"][str(fam)] += int(n or 0)
    top_players = []
    player_team_refs = sorted(
        {str(item.get("team_ref") or "") for item in aggregate.values() if str(item.get("team_ref") or "")},
        key=lambda ref: teams.get(ref, ref),
    )
    for team_ref in player_team_refs:
        team_rows = [
            item for item in aggregate.values()
            if item.get("team_ref") == team_ref
        ]
        team_rows.sort(key=lambda x: (x["shot"], x["total"]), reverse=True)
        top_players.extend(team_rows[:3])
    for item in top_players:
        fam_text = ", ".join(
            f"{_football_family_label(fam, 'tr')} {n}" for fam, n in item["families"].most_common(3)
        )
        lines.append(
            f"- {teams.get(item['team_ref'], item['team_ref'])} — {item['label']}: {item['total']} takım akışında yer aldı; "
            f"{item['shot']} şutla biten akışta göründü. En sık yer aldığı bağlamlar: {fam_text}."
        )
        review = function_review_by_actor.get(str(item.get("actor_ref") or "")) or {}
        if review:
            state_n = int(review.get("observed_score_state_context_n") or 0)
            family_n = int(review.get("observed_process_family_n") or 0)
            lines.append(
                f"- İşlev inceleme adayı — {item['label']}: {state_n} skor bağlamında {family_n} süreç ailesi; "
                "görünür süreç bileşimi bağlamlar arasında farklılaştı. Analist kontrolü: aynı oyuncunun süreç-aile dağılımını skor bağlamları arasında yeniden karşılaştır."
            )
    if top_players:
        lines.append("- Bu bölüm oyuncunun kalıcı rolünü değil, bu maçta takımın hangi oyun akışlarında daha sık göründüğünü anlatır.")

    lines.extend(["", "BAĞLI UZMAN YÜZEYLER"])
    if specialist_cards:
        lines.extend(f"- {line}" for line in specialist_cards)
    else:
        lines.append("- Bu çalışmada ek specialist-synthesis kartı oluşmadı.")
    if actor_concentration_cards:
        lines.extend(f"- {line}" for line in actor_concentration_cards)
    if fusion_relation_cards:
        lines.extend(f"- {line}" for line in fusion_relation_cards)

    lines.extend(["", "ANALİST KARARI — NEREYE BAKMALI?"])
    if positional_rows:
        lines.append("- Maç değerlendirmesinde hücum sayısını sonuçla eşitleme; önce hangi yerleşik hücumların şuta, hangilerinin top kaybına gittiğini karşılaştır.")
    if loss_rows:
        lines.append("- Rakip analizinde top kaybının kendisinden çok, kayıptan sonraki ilk pas ve ilk hücum bağlantısına odaklan; geçiş tehdidinin gerçek başlangıcı burada.")
    if records:
        lines.append("- Tekrarlayan pas bağlantılarını tek başına olumlu sinyal sayma; aynı başlangıcın devam eden ve kopan örneklerinde ilk ayrışan ilişkiyi bul.")
    if top_players:
        lines.append("- Oyuncu değerlendirmesinde toplam aksiyon yerine, oyuncunun şutla biten ve ilerleyen takım akışlarında hangi işleve bağlandığını yeniden izle.")

    lines.extend(["", "SONUÇ — ANALİST NOTU"])
    total_counter_shots = sum(int((by_team[ref].get("COUNTERATTACK_CANDIDATE") or {}).get("shot_ending_process_n") or 0) for ref in team_refs)
    total_pos_shots = sum(int((by_team[ref].get("POSITIONAL_ATTACK_CANDIDATE") or {}).get("shot_ending_process_n") or 0) for ref in team_refs)
    if total_pos_shots and total_counter_shots == 0:
        lines.append("- Bu maçın şut üretimini açıklamak için önce kontra atak sayısına değil, yerleşik hücumların nasıl son bölüme taşındığına bakmak gerekir.")
    if len(positional_rows) >= 2 and score:
        lines.append("- Skor ile yerleşik hücum hacmi aynı hikâyeyi anlatmıyor. Bu yüzden bir sonraki inceleme üretim miktarından çok şutların koşullarına, kalitesine ve bitiriciliğin oluştuğu sahnelere yönelmeli.")
    if rendered:
        lines.append("- Tekrarlayan bağlantılarda değerli soru 'kaç kez tekrarlandı?' değil, aynı başlangıcın başarılı ve başarısız örneklerini ilk kez hangi futbol ilişkisinin ayırdığıdır.")
    lines.append("- Tek maçtan kalıcı takım veya oyuncu özelliği çıkarılmamalı; burada anlatılanlar bu maçın futbol problemleridir.")
    lines.append("")
    return "\n".join(lines)




def _human_process_actor_concentration_cards(
    root: Path,
    full_spine: dict[str, Any],
    identity: dict[str, Any],
    language: str,
) -> list[str]:
    if not _declared_current(full_spine, PROCESS_ACTOR_CONCENTRATION_JSON):
        return []
    payload = _load_json(root / PROCESS_ACTOR_CONCENTRATION_JSON)
    if str(payload.get("status") or "") not in {"PASS", "REVIEW_REQUIRED"}:
        return []
    actors = _human_admitted_actor_labels(identity)
    teams = _human_team_labels(identity)
    cards: list[str] = []
    for row in payload.get("process_actor_concentration_profiles") or []:
        if not isinstance(row, dict):
            continue
        team_id = str(row.get("team_identity_candidate_id") or "").strip()
        family = str(row.get("process_family_candidate") or "").strip()
        observed_n = int(row.get("actor_observable_process_count") or 0)
        coverage_num = int(row.get("actor_observation_coverage_numerator") or 0)
        coverage_den = int(row.get("actor_observation_coverage_denominator") or 0)
        counts = {
            str(k): int(v or 0)
            for k, v in (row.get("actor_process_counts") or {}).items()
            if int(v or 0) > 0
        }
        dyads = {
            str(k): int(v or 0)
            for k, v in (row.get("dyad_process_counts") or {}).items()
            if int(v or 0) > 0
        }
        if not team_id or not family or observed_n <= 0 or not counts:
            continue
        top_actor_id, top_actor_n = max(counts.items(), key=lambda item: (item[1], item[0]))
        top_actor = actors.get(top_actor_id)
        if not top_actor:
            continue
        top_dyad_text = ""
        if dyads:
            dyad_id, dyad_n = max(dyads.items(), key=lambda item: (item[1], item[0]))
            parts = dyad_id.split("|")
            if len(parts) == 2 and parts[0] in actors and parts[1] in actors:
                top_dyad_text = f"{actors[parts[0]]} + {actors[parts[1]]} {dyad_n}"
        team = teams.get(team_id, team_id)
        family_label = _football_family_label(family, language)
        coverage = f"{coverage_num}/{coverage_den}" if coverage_den > 0 else str(observed_n)
        if language == "tr":
            text = (
                f"Oyuncu süreç yoğunlaşması — {team}, {family_label}: actor annotation coverage {coverage}; "
                f"{top_actor} {top_actor_n}/{observed_n} gözlenebilir süreçte yer aldı."
            )
            if top_dyad_text:
                text += f" En sık aynı süreçte birlikte görünme: {top_dyad_text}."
            text += (
                " Bu birlikte-görünmenin kapsamı aynı process instance içindeki gözlenebilir eş-katılımdır; pas ilişkisi, nedensel işbirliği, vazgeçilmezlik, kalıcı rol, taktik esneklik ve oyuncu değeri yorumları için ayrı evidence gerekir."
            )
        else:
            text = (
                f"Player process concentration — {team}, {family_label}: actor-annotation coverage {coverage}; "
                f"{top_actor} appeared in {top_actor_n}/{observed_n} observable processes."
            )
            if top_dyad_text:
                text += f" Most frequent same-process co-appearance: {top_dyad_text}."
            text += (
                " Co-appearance is scoped to observable co-participation within the same process instance; pass-relation, causal-collaboration, indispensability, persistent-role, tactical-flexibility, and player-value interpretations require separate evidence."
            )
        cards.append(text)
    return cards

def _human_residual_specialist_cards(
    rich: dict[str, Any],
    identity: dict[str, Any],
    language: str,
) -> list[str]:
    """Render current rich-lane specialist syntheses that otherwise have no human consumer."""
    teams = _human_team_labels(identity)
    cards: list[str] = []

    m01 = rich.get("m01_possession_construction_synthesis") or {}
    m02 = rich.get("m02_progression_territory_synthesis") or {}
    r01 = rich.get("r01_ball_progression_system_synthesis") or {}
    if str(r01.get("status") or "") in {"PASS", "REVIEW_REQUIRED"}:
        m01_by_team = {
            str(row.get("team_identity_candidate_id") or ""): row
            for row in (m01.get("profiles") or []) if isinstance(row, dict)
        }
        m02_by_team = {
            str(row.get("team_identity_candidate_id") or ""): row
            for row in (m02.get("profiles") or []) if isinstance(row, dict)
        }
        for row in r01.get("profiles") or []:
            if not isinstance(row, dict):
                continue
            team_id = str(row.get("team_identity_candidate_id") or "").strip()
            if not team_id:
                continue
            name = teams.get(team_id, team_id)
            construction = m01_by_team.get(team_id) or {}
            progression = m02_by_team.get(team_id) or {}
            sig_n = int(construction.get("eligible_process_signature_n") or progression.get("eligible_process_signature_n") or 0)
            circulation_n = int(construction.get("visible_circulation_process_n") or 0)
            gk_n = int(construction.get("goalkeeper_restart_context_n") or 0)
            axis_n = int(progression.get("provider_attack_axis_delta_admitted_process_n") or 0)
            end_counts = progression.get("visible_end_zone_candidate_counts") or {}
            end_text = ", ".join(f"{_display_label(k)} {int(v or 0)}" for k, v in sorted(end_counts.items())) or ("çözümlenmedi" if language == "tr" else "unresolved")
            if language == "tr":
                cards.append(
                    f"Kurulum/ilerleme bağlamı — {name}: {sig_n} süreç imzası; {circulation_n} görünür dolaşım süreci, "
                    f"{gk_n} kaleci yeniden başlatma bağlamı ve {axis_n} hücum-ekseni bağlamlı süreç. "
                    f"Görünür bitiş bölgesi adayları: {end_text}. Bu birleşik yüzey mevcut construction ve progression contextlerini tek inceleme kartında toplar."
                )
            else:
                cards.append(
                    f"Construction/progression context — {name}: {sig_n} admitted process signatures; {circulation_n} visible circulation processes, "
                    f"{gk_n} goalkeeper-restart contexts and {axis_n} provider-attack-axis admitted processes. "
                    f"Visible end-zone candidates: {end_text}. This combined surface binds existing construction and progression contexts into one review card."
                )

    m06 = rich.get("m06_transition_dynamics_synthesis") or {}
    if str(m06.get("status") or "") in {"PASS", "REVIEW_REQUIRED"}:
        for row in m06.get("profiles") or []:
            if not isinstance(row, dict):
                continue
            team_id = str(row.get("team_identity_candidate_id") or "").strip()
            if not team_id:
                continue
            name = teams.get(team_id, team_id)
            counter_n = int(row.get("counterattack_context_n") or 0)
            to_pos_n = int(row.get("counter_to_positional_successor_candidate_n") or 0)
            latency_n = int(row.get("counterattack_successor_latency_observed_n") or 0)
            lo = row.get("counterattack_successor_latency_min_candidate")
            hi = row.get("counterattack_successor_latency_max_candidate")
            if language == "tr":
                latency = f"{_human_number(lo)}–{_human_number(hi)} sn" if latency_n and lo is not None and hi is not None else "çözümlenmedi"
                cards.append(
                    f"Geçiş-devam bağlamı — {name}: {counter_n} kontra-atak bağlamının {to_pos_n} tanesinde sonraki tekil görünür süreç yerleşik hücum adayıydı; "
                    f"{latency_n} örnekte sonraki görünür sürece süre aralığı {latency}. Bu yüzey görünür ardışıklığı özetler; transition-phase, momentum ve taktik adaptasyon yorumları ayrı observation gerektirir."
                )
            else:
                latency = f"{_human_number(lo)}–{_human_number(hi)} s" if latency_n and lo is not None and hi is not None else "unresolved"
                cards.append(
                    f"Transition-continuation context — {name}: {to_pos_n} of {counter_n} counterattack contexts were followed by a single visible positional-attack candidate; "
                    f"the next-visible-process latency range across {latency_n} observed examples was {latency}. This surface summarizes visible succession; transition-phase, momentum and tactical-adaptation interpretations require separate observations."
                )

    m07 = rich.get("m07_defensive_process_visible_exposure_response_synthesis") or {}
    if str(m07.get("status") or "") in {"PASS", "REVIEW_REQUIRED"}:
        for row in m07.get("profiles") or []:
            if not isinstance(row, dict):
                continue
            team_id = str(row.get("team_identity_candidate_id") or "").strip()
            opp_id = str(row.get("opponent_team_identity_candidate_id") or "").strip()
            if not team_id:
                continue
            name = teams.get(team_id, team_id)
            opp = teams.get(opp_id, opp_id or ("rakip" if language == "tr" else "opponent"))
            proc_n = int(row.get("opponent_visible_process_n") or 0)
            shot_n = int(row.get("opponent_shot_ending_process_n") or 0)
            loss_n = int(row.get("opponent_visible_loss_process_n") or 0)
            if language == "tr":
                cards.append(
                    f"Savunma maruziyeti/yanıt bağlamı — {name}: {opp} için {proc_n} görünür süreç, {shot_n} şut-sonlanan süreç ve {loss_n} görünür kayıp süreci bağlandı. "
                    "Kapsam event/process-visible maruziyet ve yanıttır; organize savunma şekli, compactness, pressure geometry, forced-turnover ve savunma başarısı yorumları ayrı observation gerektirir."
                )
            else:
                cards.append(
                    f"Defensive exposure/response context — {name}: {opp} was linked to {proc_n} visible processes, {shot_n} shot-ending processes and {loss_n} visible-loss processes. "
                    "Scope is event/process-visible exposure and response; organized-defence shape, compactness, pressure geometry, forced-turnover and defensive-success interpretations require separate observations."
                )

    gk = rich.get("goalkeeper_restart_consequence_context") or {}
    if str(gk.get("status") or "") in {"PASS", "REVIEW_REQUIRED"}:
        by_team: dict[str, list[dict[str, Any]]] = {}
        for row in gk.get("rows") or []:
            if isinstance(row, dict):
                tid = str(row.get("team_identity_candidate_id") or "").strip()
                if tid:
                    by_team.setdefault(tid, []).append(row)
        for team_id, rows in sorted(by_team.items(), key=lambda item: teams.get(item[0], item[0])):
            name = teams.get(team_id, team_id)
            buckets = Counter(str(row.get("provider_distance_bucket_candidate") or "UNRESOLVED") for row in rows)
            success_n = sum(str(row.get("pass_outcome_candidate") or "") == "SUCCESS" for row in rows)
            next_families = Counter(
                str(fam)
                for row in rows
                for fam in (row.get("next_visible_process_family_candidates") or [])
                if str(fam)
            )
            bucket_text = ", ".join(f"{_display_label(k)} {v}" for k, v in sorted(buckets.items()))
            next_text = ", ".join(f"{_football_family_label(k, language)} {v}" for k, v in sorted(next_families.items())) or ("tekil bağ yok" if language == "tr" else "no single binding")
            if language == "tr":
                cards.append(
                    f"Kaleci yeniden başlatma bağlamı — {name}: {len(rows)} kale vuruşu başlangıç kaydı; mesafe sınıfları {bucket_text}; SUCCESS etiketi {success_n}/{len(rows)}; "
                    f"ilk görünür sonraki süreç bağları {next_text}. Mesafe sınıfının fiziksel mesafe veya teknik plan yorumuna yükselmesi için ayrı observation gerekir."
                )
            else:
                cards.append(
                    f"Goalkeeper-restart context — {name}: {len(rows)} admitted goal-kick occurrences; provider distance buckets {bucket_text}; SUCCESS label {success_n}/{len(rows)}; "
                    f"first-visible next-process bindings {next_text}. Provider buckets remain provider context rather than measured physical distance or tactical-plan truth."
                )

    game = rich.get("game_state_process_mix_context") or {}
    if str(game.get("status") or "") in {"PASS", "REVIEW_REQUIRED"}:
        by_team: dict[str, list[dict[str, Any]]] = {}
        for row in game.get("profiles") or []:
            if isinstance(row, dict):
                tid = str(row.get("team_identity_candidate_id") or "").strip()
                if tid:
                    by_team.setdefault(tid, []).append(row)
        for team_id, rows in sorted(by_team.items(), key=lambda item: teams.get(item[0], item[0])):
            name = teams.get(team_id, team_id)
            bits: list[str] = []
            for row in rows[:4]:
                score = _score_state_human(row.get("score_state_candidate"), language) or ("skor bağlamı" if language == "tr" else "score context")
                counts = row.get("process_family_counts") or {}
                mix = ", ".join(f"{_football_family_label(k, language)} {int(v or 0)}" for k, v in sorted(counts.items()) if int(v or 0) > 0) or ("0" if language == "tr" else "0")
                bits.append(f"{score}: {mix}")
            if bits:
                if language == "tr":
                    cards.append(f"Skor-durumu süreç karışımı — {name}: " + "; ".join(bits) + ". Payda ilgili skor segmentinin görünür zaman maruziyetidir; nedensel skor-durumu açıklaması için ayrı evidence gerekir.")
                else:
                    cards.append(f"Score-state process mix — {name}: " + "; ".join(bits) + ". The denominator is visible exposure time in the relevant score segment; score state is contextual rather than causal explanation.")

    return cards


def _human_fusion_relation_cards(full_spine: dict[str, Any], language: str) -> list[str]:
    fusion_records: list[dict[str, Any]] = []
    sidecar = full_spine.get("fusion_relation_review_records")
    if isinstance(sidecar, list) and sidecar:
        fusion_records = [row for row in sidecar if isinstance(row, dict)]
    else:
        chains = full_spine.get("intelligence_chains")
        if isinstance(chains, list):
            fusion_records = [
                fusion
                for chain in chains
                if isinstance(chain, dict)
                for fusion in [chain.get("fusion")]
                if isinstance(fusion, dict)
            ]
    if not fusion_records:
        return []
    relation_counts: Counter[str] = Counter()
    admitted_counter = unresolved_counter = independent = correlated = dependency_challenge = 0
    fusion_n = 0
    for fusion in fusion_records:
        fusion_n += 1
        relation_counts.update({str(k): int(v or 0) for k, v in (fusion.get("relation_counts") or {}).items()})
        admitted_counter += int(fusion.get("admitted_counterevidence_count") or 0)
        unresolved_counter += int(fusion.get("unresolved_counterevidence_count") or 0)
        independent += int(fusion.get("independent_support_count") or 0)
        correlated += int(fusion.get("correlated_or_unknown_support_count") or 0)
        dependency_challenge += int(fusion.get("dependency_challenge_count") or 0)
    if not fusion_n:
        return []
    rel = ", ".join(f"{k} {v}" for k, v in sorted(relation_counts.items()) if v) or "NONE"
    if language == "tr":
        return [
            f"Kanıt ilişki özeti: {fusion_n} birleştirme kaydı; ilişkiler {rel}; doğrulanmış karşı-örnek {admitted_counter}, çözülmemiş karşı-örnek {unresolved_counter}, "
            f"bağımlılık inceleme kaydı {dependency_challenge}, bağımsız destek {independent}, ilişkili veya bağımsızlığı belirsiz destek {correlated}. "
            "Ham referans sayısı bağımsız destek sayılmaz; karşı-örnek sınıfı yalnız karşılaştırma uygunluğu ve bağımlılık koşullarıyla yükselir."
        ]
    return [
        f"Evidence-relation summary: {fusion_n} fusion records; relations {rel}; admitted counterevidence {admitted_counter}, unresolved counterevidence {unresolved_counter}, "
        f"dependency challenges {dependency_challenge}, independent support {independent}, correlated/unknown support {correlated}. "
        "Nominal reference count is not used as independent-support count; counterevidence is promoted only through admitted comparison/dependency conditions."
    ]

def build_human_analyst_report_tr(
    output_root: str | Path,
    full_spine: dict[str, Any],
    *,
    analyst_question_payload: dict[str, Any] | None = None,
) -> str:
    root = Path(output_root)
    rich_current = _rich_surface_current(full_spine)
    rich = full_spine.get("rich_multiformat_analysis_lattice") if rich_current else {}
    rich = rich if isinstance(rich, dict) else {}
    identity = _load_json(root / IDENTITY_JSON) if _declared_current(full_spine, IDENTITY_JSON) else {}
    c02_cards = _human_c02_cards(rich, identity, "tr") if rich_current else []
    player_identity_context = dict(identity)
    player_identity_context["__spatial_progression_evidence__"] = (
        full_spine.get("spatial_progression_evidence") or {}
    )
    player_function_cards = (
        _human_player_function_cards(rich, player_identity_context, "tr")
        if rich_current else []
    )
    model_context_cards = _human_model_context_cards(rich, identity, "tr") if rich_current else []
    team_cards = _human_team_process_cards(rich, identity, "tr") if rich_current else []
    match_story_cards = _human_match_story_cards(rich, identity, "tr") if rich_current else []
    state_function_cards = _human_visible_state_function_lens(full_spine, "tr")
    score_state_cards = _human_score_state_process_outcome_cards(rich, identity, "tr") if rich_current else []
    loss_recovery_score_state_cards = _human_loss_recovery_score_state_cards(rich, identity, "tr") if rich_current else []
    circulation_cards = _human_circulation_fate_cards(rich, identity, "tr") if rich_current else []
    route_breadth_cards = _human_process_route_breadth_cards(rich, identity, "tr") if rich_current else []
    aerial_cards = _human_aerial_duel_cards(rich, identity, "tr") if rich_current else []
    set_piece_cards = _human_set_piece_process_cards(rich, identity, "tr") if rich_current else []
    contest_cards = _human_process_contest_cards(rich, identity, "tr") if rich_current else []
    opponent_interaction_cards = _human_opponent_interaction_cards(rich, identity, "tr") if rich_current else []
    sequence_cards = _human_sequence_information_cards(rich, identity, "tr") if rich_current else []
    process_variant_cards = _human_process_variant_board_cards(rich, identity, "tr") if rich_current else []
    specialist_cards = _human_residual_specialist_cards(rich, identity, "tr") if rich_current else []
    actor_concentration_cards = _human_process_actor_concentration_cards(root, full_spine, identity, "tr")
    fusion_relation_cards = _human_fusion_relation_cards(full_spine, "tr")
    mechanism_cards = _human_mechanism_cards(
        root,
        full_spine,
        identity,
        "tr",
        analyst_question_payload=analyst_question_payload,
    )
    mechanism_graph = build_graph_ready_mechanism_cards_payload(
        root,
        full_spine,
        analyst_question_payload=analyst_question_payload,
    )
    player_mechanism_link_cards = _human_player_mechanism_link_cards(
        mechanism_graph, rich, identity, "tr"
    )
    match_story_mechanism_highlights = _human_match_story_mechanism_highlights(
        mechanism_cards, "tr", limit=2
    )
    lines = [
        "HPFA MAÇ ANALİZİ — TÜRKÇE ANALİST RAPORU",
        "========================================",
        "",
        "Bu rapor futbol diliyle yazılmış analist yüzeyidir. Teknik kanıt ayrıntıları ayrı 'Kanıt notu' satırlarında tutulur.",
        "",
        "MAÇIN HİKÂYESİ — GÖRÜNÜR SÜREÇ ÖZETİ",
    ]
    if match_story_cards:
        lines.extend(f"- {line}" for line in match_story_cards)
    else:
        lines.append("- Bu maçta güvenli biçimde özetlenebilir altı-faz süreç hikâyesi yok.")
    if match_story_mechanism_highlights:
        lines.append("- Hikâyeyi destekleyen kaynak-bağlı inceleme noktaları:")
        lines.extend(f"  • {line}" for line in match_story_mechanism_highlights)
    if state_function_cards:
        lines.append("- Görünür durum-değişimi fonksiyon lensi:")
        lines.extend(f"  • {line}" for line in state_function_cards)
    lines.extend(["", "[1] MAÇIN GÖRÜNÜR SÜREÇ PROFİLİ"])
    if team_cards:
        lines.extend(f"- {line}" for line in team_cards)
    else:
        lines.append("- Bu maçta takım süreç profili güvenli biçimde üretilemedi.")
    lines.extend(["", "[2] SKOR BAĞLAMI → GÖRÜNÜR SÜREÇ / SONUÇ PROFİLİ"])
    if score_state_cards:
        lines.extend(f"- {line}" for line in score_state_cards)
    else:
        lines.append("- Skor-segmenti süreç/sonuç yüzeyi bu çalışmada rapor kapsamına alınamadı.")
    if loss_recovery_score_state_cards:
        lines.extend(f"- {line}" for line in loss_recovery_score_state_cards)
    lines.extend(["", "[3] DOLAŞIM → GÖRÜNÜR KADER"])
    if circulation_cards:
        lines.extend(f"- {line}" for line in circulation_cards)
    else:
        lines.append("- Bu maçta güvenli biçimde raporlanabilir dolaşım-kader yüzeyi yok.")
    lines.extend(["", "[3A] GÖRÜNÜR SÜREÇ ROTALARI"])
    if route_breadth_cards:
        lines.extend(f"- {line}" for line in route_breadth_cards)
    else:
        lines.append("- Bu maçta güvenli biçimde raporlanabilir görünür süreç rota-breadth yüzeyi yok.")
    lines.extend(["", "[4] HAVA TOPU → İLK GÖRÜNÜR DEVAM"])
    if aerial_cards:
        lines.extend(f"- {line}" for line in aerial_cards)
    else:
        lines.append("- Bu maçta güvenli biçimde raporlanabilir hava topu ilk-görünür-devam yüzeyi yok.")
    lines.extend(["", "[5] DURAN TOP HÜCUMU → GÖRÜNÜR SONUÇ"])
    if set_piece_cards:
        lines.extend(f"- {line}" for line in set_piece_cards)
    else:
        lines.append("- Bu maçta güvenli biçimde raporlanabilir duran top süreç-sonuç yüzeyi yok.")
    lines.extend(["", "[6] SEQUENCE / PROCESS INTELLIGENCE"])
    if sequence_cards:
        lines.extend(f"- {line}" for line in sequence_cards)
    else:
        lines.append("- Bu maçta sequence/process information profili üretilemedi.")
    lines.extend(["", "[7] SÜREÇ VARYANT PANOSU — TEKRAR / VARYANT / OYUNCU KENARLARI"])
    if process_variant_cards:
        lines.extend(f"- {line}" for line in process_variant_cards)
    else:
        lines.append("- Bu maçta güvenli biçimde raporlanabilir tekrarlayan süreç varyantı yok.")
    lines.extend(["", "[8] OYUNCU / İKİLİ × HÜCUM SONUCU"])
    if c02_cards:
        lines.extend(f"- {line}" for line in c02_cards)
    else:
        lines.append("- Bu maçta bu başlık için güvenli biçimde raporlanabilir current-run aday yok.")
    if model_context_cards:
        lines.extend(f"- {line}" for line in model_context_cards)
    lines.extend(["", "[9] PLAYER FUNCTIONS — MAÇ-İÇİ GÖRÜNÜR İŞLEV BAĞLAMI"])
    if player_function_cards:
        lines.extend(f"- {line}" for line in player_function_cards)
    else:
        lines.append("- Bu maçta güvenli biçimde raporlanabilir oyuncu fonksiyon profili yok.")
    if player_mechanism_link_cards:
        lines.append("- Kaynak-bağlı oyuncu ↔ mekanizma bağlantıları:")
        lines.extend(f"  • {line}" for line in player_mechanism_link_cards)
    lines.extend(["", "[10] 12 YÖNLÜ POSTMATCH — 6 FAZ × 2 TAKIM"])
    if contest_cards:
        lines.extend(f"- {line}" for line in contest_cards)
    else:
        lines.append("- Bu maçta iki takım için karşılaştırılabilir süreç çarpışma yüzeyi üretilemedi.")
    lines.extend(["", "[11] TEAM ↔ OPPONENT ETKİLEŞİMİ"])
    if opponent_interaction_cards:
        lines.extend(f"- {line}" for line in opponent_interaction_cards)
    else:
        lines.append("- Bu maçta M09 görünür takım-rakip etkileşim yüzeyi rapor kapsamına alınamadı.")
    lines.extend(["", "[11A] BAĞLI UZMAN YÜZEYLER — CURRENT PRODUCER → ANALİST"])
    if specialist_cards:
        lines.extend(f"- {line}" for line in specialist_cards)
    else:
        lines.append("- Bu çalışmada ek specialist-synthesis kartı oluşmadı.")
    if actor_concentration_cards:
        lines.append("- Oyuncu katılım yoğunlaşması / birlikte-görünme incelemesi:")
        lines.extend(f"  • {line}" for line in actor_concentration_cards)
    if fusion_relation_cards:
        lines.append("- Fusion / counterevidence / dependency özeti:")
        lines.extend(f"  • {line}" for line in fusion_relation_cards)

    lines.extend(["", "[12] MEKANİZMA KARTLARI — ANA ADAYLAR VE SINIRLI KARŞILAŞTIRMALAR"])
    if mechanism_cards:
        lines.extend(f"- {line}" for line in mechanism_cards)
    else:
        lines.append("- Bu maçta güvenli biçimde kısa listeye alınmış mekanizma adayı yok.")
    lines.extend([
        "",
        "[13] ANALİST OKUMA ÇERÇEVESİ",
        "- Oyuncu ve ikili yüzeyi, görünür süreç katılımı ile sonuç bağlantısını maç-içi association olarak sunar.",
        "- Hedef sonuç etiketi çözülmeyen süreçler unresolved outcome statüsünde izlenir.",
        "- Sıralama, analistin hangi örneklere önce bakacağını belirleyen maç-içi dikkat sırasıdır.",
        "- Tekrarlayan aksiyon grameri recurrence ve varyant incelemesi için kullanılır.",
        "- Fiziksel yapı ve geometri constructları, ilgili observation capability admit edildiğinde raporlanır.",
        "",
    ])
    return "\n".join(lines)


def build_human_analyst_report_en(
    output_root: str | Path,
    full_spine: dict[str, Any],
    *,
    analyst_question_payload: dict[str, Any] | None = None,
) -> str:
    root = Path(output_root)
    rich_current = _rich_surface_current(full_spine)
    rich = full_spine.get("rich_multiformat_analysis_lattice") if rich_current else {}
    rich = rich if isinstance(rich, dict) else {}
    identity = _load_json(root / IDENTITY_JSON) if _declared_current(full_spine, IDENTITY_JSON) else {}
    c02_cards = _human_c02_cards(rich, identity, "en") if rich_current else []
    player_identity_context = dict(identity)
    player_identity_context["__spatial_progression_evidence__"] = (
        full_spine.get("spatial_progression_evidence") or {}
    )
    player_function_cards = (
        _human_player_function_cards(rich, player_identity_context, "en")
        if rich_current else []
    )
    model_context_cards = _human_model_context_cards(rich, identity, "en") if rich_current else []
    team_cards = _human_team_process_cards(rich, identity, "en") if rich_current else []
    match_story_cards = _human_match_story_cards(rich, identity, "en") if rich_current else []
    state_function_cards = _human_visible_state_function_lens(full_spine, "en")
    score_state_cards = _human_score_state_process_outcome_cards(rich, identity, "en") if rich_current else []
    loss_recovery_score_state_cards = _human_loss_recovery_score_state_cards(rich, identity, "en") if rich_current else []
    circulation_cards = _human_circulation_fate_cards(rich, identity, "en") if rich_current else []
    route_breadth_cards = _human_process_route_breadth_cards(rich, identity, "en") if rich_current else []
    aerial_cards = _human_aerial_duel_cards(rich, identity, "en") if rich_current else []
    set_piece_cards = _human_set_piece_process_cards(rich, identity, "en") if rich_current else []
    contest_cards = _human_process_contest_cards(rich, identity, "en") if rich_current else []
    opponent_interaction_cards = _human_opponent_interaction_cards(rich, identity, "en") if rich_current else []
    sequence_cards = _human_sequence_information_cards(rich, identity, "en") if rich_current else []
    process_variant_cards = _human_process_variant_board_cards(rich, identity, "en") if rich_current else []
    specialist_cards = _human_residual_specialist_cards(rich, identity, "en") if rich_current else []
    actor_concentration_cards = _human_process_actor_concentration_cards(root, full_spine, identity, "en")
    fusion_relation_cards = _human_fusion_relation_cards(full_spine, "en")
    mechanism_cards = _human_mechanism_cards(
        root,
        full_spine,
        identity,
        "en",
        analyst_question_payload=analyst_question_payload,
    )
    mechanism_graph = build_graph_ready_mechanism_cards_payload(
        root,
        full_spine,
        analyst_question_payload=analyst_question_payload,
    )
    player_mechanism_link_cards = _human_player_mechanism_link_cards(
        mechanism_graph, rich, identity, "en"
    )
    match_story_mechanism_highlights = _human_match_story_mechanism_highlights(
        mechanism_cards, "en", limit=2
    )
    lines = [
        "HPFA MATCH ANALYSIS — ENGLISH ANALYST REPORT",
        "===========================================",
        "",
        "This is the analyst-facing football report. Technical evidence limits are kept in separate 'Evidence note' lines.",
        "",
        "MATCH STORY — VISIBLE PROCESS SUMMARY",
    ]
    if match_story_cards:
        lines.extend(f"- {line}" for line in match_story_cards)
    else:
        lines.append("- No safely reportable six-phase process story is available for this match.")
    if match_story_mechanism_highlights:
        lines.append("- Source-bound review points supporting the story:")
        lines.extend(f"  • {line}" for line in match_story_mechanism_highlights)
    if state_function_cards:
        lines.append("- Visible state-change function lens:")
        lines.extend(f"  • {line}" for line in state_function_cards)
    lines.extend(["", "[1] VISIBLE MATCH PROCESS PROFILE"])
    if team_cards:
        lines.extend(f"- {line}" for line in team_cards)
    else:
        lines.append("- No safe current-run team process profile is available.")
    lines.extend(["", "[2] SCORE CONTEXT → VISIBLE PROCESS / OUTCOME PROFILE"])
    if score_state_cards:
        lines.extend(f"- {line}" for line in score_state_cards)
    else:
        lines.append("- Score-segment process/outcome context was not admitted into this report run.")
    if loss_recovery_score_state_cards:
        lines.extend(f"- {line}" for line in loss_recovery_score_state_cards)
    lines.extend(["", "[3] CIRCULATION → VISIBLE FATE"])
    if circulation_cards:
        lines.extend(f"- {line}" for line in circulation_cards)
    else:
        lines.append("- No safely reportable circulation-fate surface is available for this match.")
    lines.extend(["", "[3A] VISIBLE PROCESS ROUTES"])
    if route_breadth_cards:
        lines.extend(f"- {line}" for line in route_breadth_cards)
    else:
        lines.append("- No safely reportable visible process route-breadth surface is available for this match.")
    lines.extend(["", "[4] AERIAL DUEL → FIRST VISIBLE CONTINUATION"])
    if aerial_cards:
        lines.extend(f"- {line}" for line in aerial_cards)
    else:
        lines.append("- No safely reportable aerial-duel first-visible-continuation surface is available for this match.")
    lines.extend(["", "[5] ATTACKING SET PIECE → VISIBLE OUTCOME"])
    if set_piece_cards:
        lines.extend(f"- {line}" for line in set_piece_cards)
    else:
        lines.append("- No safely reportable set-piece process/outcome surface is available for this match.")
    lines.extend(["", "[6] SEQUENCE / PROCESS INTELLIGENCE"])
    if sequence_cards:
        lines.extend(f"- {line}" for line in sequence_cards)
    else:
        lines.append("- No sequence/process information profile is available for this run.")
    lines.extend(["", "[7] PROCESS VARIANT BOARD — RECURRENCE / VARIANT / PLAYER EDGES"])
    if process_variant_cards:
        lines.extend(f"- {line}" for line in process_variant_cards)
    else:
        lines.append("- No safely reportable recurring process variant is available for this match.")
    lines.extend(["", "[8] PLAYER / PAIR × ATTACK OUTCOME"])
    if c02_cards:
        lines.extend(f"- {line}" for line in c02_cards)
    else:
        lines.append("- No current-run candidate can be reported safely under this heading.")
    if model_context_cards:
        lines.extend(f"- {line}" for line in model_context_cards)
    lines.extend(["", "[9] PLAYER FUNCTIONS — MATCH-LOCAL VISIBLE FUNCTION CONTEXT"])
    if player_function_cards:
        lines.extend(f"- {line}" for line in player_function_cards)
    else:
        lines.append("- No safely reportable player-function profile is available for this match.")
    if player_mechanism_link_cards:
        lines.append("- Source-bound player ↔ mechanism links:")
        lines.extend(f"  • {line}" for line in player_mechanism_link_cards)
    lines.extend(["", "[10] 12-DIRECTION POSTMATCH — 6 PHASES × 2 TEAMS"])
    if contest_cards:
        lines.extend(f"- {line}" for line in contest_cards)
    else:
        lines.append("- No comparable two-team process contest surface is available for this run.")
    lines.extend(["", "[11] TEAM ↔ OPPONENT INTERACTION"])
    if opponent_interaction_cards:
        lines.extend(f"- {line}" for line in opponent_interaction_cards)
    else:
        lines.append("- The M09 visible team-opponent interaction surface was not admitted into this report run.")
    lines.extend(["", "[11A] CONNECTED SPECIALIST SURFACES — CURRENT PRODUCER → ANALYST"])
    if specialist_cards:
        lines.extend(f"- {line}" for line in specialist_cards)
    else:
        lines.append("- No additional specialist-synthesis card is available in this run.")
    if actor_concentration_cards:
        lines.append("- Player participation concentration / co-appearance review:")
        lines.extend(f"  • {line}" for line in actor_concentration_cards)
    if fusion_relation_cards:
        lines.append("- Fusion / counterevidence / dependency summary:")
        lines.extend(f"  • {line}" for line in fusion_relation_cards)

    lines.extend(["", "[12] MECHANISM CARDS — MAIN CANDIDATES AND LIMITED COMPARISONS"])
    if mechanism_cards:
        lines.extend(f"- {line}" for line in mechanism_cards)
    else:
        lines.append("- No mechanism candidate was safely shortlisted in this run.")
    lines.extend([
        "",
        "[13] ANALYST READING FRAME",
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
    actor_labels = _human_admitted_actor_labels(identity)
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
        lines.extend(f"- {item}" for item in _representative_entities(rich, identity))

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
            actor_ids = [
                str(value).strip()
                for value in (candidate.get("actor_identity_candidate_ids") or [])
                if str(value).strip()
            ]
            resolved_names = [actor_labels.get(actor_id) for actor_id in actor_ids]
            if not actor_ids or any(not name for name in resolved_names):
                continue
            names = " + ".join(str(name) for name in resolved_names)
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
                "Bu kayıt, admitted process/occurrence incelemesine öncelik veren maç-içi görünür association adayıdır; kapsamı match-local review priority olarak tanımlıdır. "
                "Oyuncu adı identity owner içindeki kabul edilmiş maç-içi etiketten gelir; global/cross-match kimlik claim'i üretilmez."
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
            entity_label = _human_match_local_entity_label(rich, identity, representative)
            if not entity_label:
                continue
            lines.append(
                f"- XLSX BILESIM ADAYI: {family_id}; entity={entity_label}; "
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
    analyst_question_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(output_root).expanduser().resolve(strict=False)
    root.mkdir(parents=True, exist_ok=True)
    _ = before_state

    report_path = root / ANALYST_REPORT
    report_tr_path = root / ANALYST_REPORT_TR
    report_en_path = root / ANALYST_REPORT_EN
    mechanism_graph_path = root / MECHANISM_CARDS_GRAPH_JSON
    manifest_path = root / BUNDLE_MANIFEST
    zip_path = root / BUNDLE_ZIP
    football_delivery_zip_path = root / FOOTBALL_DELIVERY_ZIP
    temp_zip_path = root / f".{BUNDLE_ZIP}.tmp"
    if temp_zip_path.is_file():
        temp_zip_path.unlink()

    report_text = build_analyst_report(root, full_spine)
    report_tr_text = build_hp_football_report_tr(
        root,
        full_spine,
        analyst_question_payload=analyst_question_payload,
    )
    report_en_text = build_human_analyst_report_en(
        root,
        full_spine,
        analyst_question_payload=analyst_question_payload,
    )
    report_path.write_text(report_text, encoding="utf-8")
    report_tr_path.write_text(report_tr_text, encoding="utf-8")
    report_en_path.write_text(report_en_text, encoding="utf-8")

    with zipfile.ZipFile(
        football_delivery_zip_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        archive.write(report_tr_path, arcname=ANALYST_REPORT_TR)

    mechanism_graph_payload = build_graph_ready_mechanism_cards_payload(
        root,
        full_spine,
        analyst_question_payload=analyst_question_payload,
    )
    mechanism_graph_path.write_text(
        json.dumps(mechanism_graph_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    presentation_view_path = root / PRESENTATION_VIEW_MODEL_JSON
    professional_html_path = root / PROFESSIONAL_REPORT_HTML
    analyst_output_claim_payload = (
        _load_json(root / ANALYST_OUTPUT_CLAIM_JSON)
        if _declared_current(full_spine, ANALYST_OUTPUT_CLAIM_JSON)
        else {}
    )
    safe_finding_payload = (
        _load_json(root / SAFE_FINDING_ADMISSION_JSON)
        if _declared_current(full_spine, SAFE_FINDING_ADMISSION_JSON)
        else {}
    )
    identity_payload = (
        _load_json(root / IDENTITY_JSON)
        if _declared_current(full_spine, IDENTITY_JSON)
        else {}
    )
    presentation_view = build_presentation_view_model(
        full_spine,
        analyst_report_tr=report_tr_text,
        analyst_report_en=report_en_text,
        mechanism_graph_payload=mechanism_graph_payload,
        analyst_output_claim_payload=analyst_output_claim_payload,
        safe_finding_payload=safe_finding_payload,
        identity_payload=identity_payload,
    )
    presentation_view_path.write_text(
        json.dumps(presentation_view, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    professional_html_path.write_text(
        render_professional_html(presentation_view, language="tr"),
        encoding="utf-8",
    )

    candidates = _declared_current_artifacts(root, full_spine)
    for presentation_path in (mechanism_graph_path, presentation_view_path, professional_html_path):
        if presentation_path.is_file() and presentation_path not in candidates:
            candidates.append(presentation_path)
    candidates.sort(key=lambda item: item.name.casefold())
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
        "analyst_question_binding": {
            "analyst_question_id": (
                str((analyst_question_payload or {}).get("analyst_question_id") or "").strip() or None
            ),
            "question_source": (
                str((analyst_question_payload or {}).get("question_source") or "").strip() or None
            ),
            "question_focus_dimensions": sorted({
                str(value or "").strip().upper()
                for value in ((analyst_question_payload or {}).get("question_focus_dimensions") or [])
                if str(value or "").strip()
            }),
            "binding_state": mechanism_graph_payload.get("analyst_question_binding_state"),
            "question_binding_changes_evidence": False,
            "question_binding_changes_support": False,
            "question_binding_changes_claim_ceiling": False,
            "question_binding_can_authorize_emit": False,
        },
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
        "mechanism_cards_graph_ready": str(mechanism_graph_path),
        "presentation_view_model": str(presentation_view_path),
        "professional_report_html": str(professional_html_path),
        "bundle_manifest": str(manifest_path),
        "bundle_zip": str(zip_path),
        "football_delivery_zip": str(football_delivery_zip_path),
        "bundle_file_count": len(candidates) + 1,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
