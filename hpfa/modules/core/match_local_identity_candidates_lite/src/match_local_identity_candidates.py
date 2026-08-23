from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "match_local_identity_candidates_lite_v1"
INPUT_MODULE_ID = "evidence_atom_inventory_lite_v1"
CANONICAL_EVENT_COUNT = "UNKNOWN"
CLAIM_CEILING = "MATCH_LOCAL_IDENTITY_CANDIDATE_ONLY"

ALLOWED_SOURCE_ROLES = {
    "GOALKEEPER_SURFACE_CANDIDATE",
    "PLAYER_SURFACE_CANDIDATE",
    "TEAM_SURFACE_CANDIDATE",
}
ACTOR_SOURCE_ROLES = {
    "GOALKEEPER_SURFACE_CANDIDATE",
    "PLAYER_SURFACE_CANDIDATE",
}
BOUND_STATES = {
    "TEAM_IDENTITY_CANDIDATE_BOUND",
    "ACTOR_IDENTITY_CANDIDATE_BOUND",
    "IDENTITY_NOT_APPLICABLE",
}
OUTPUTS = {
    "json": "match_local_identity_candidates_lite_v1.json",
    "summary": "match_local_identity_candidates_lite_v1.txt",
    "analyst": "match_local_identity_candidates_analyst_audit_v1.txt",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _clean(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", text)).strip("_")


def _digest(*values: Any) -> str:
    raw = json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value) is not None


def validate_output_root(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def _exact_subject_prefix(code_raw: Any, raw_label: Any) -> str | None:
    code = _clean(code_raw)
    label = _clean(raw_label)
    if not code or not label:
        return None
    suffix = " - " + label
    if not code.endswith(suffix):
        return None
    prefix = code[: -len(suffix)].strip()
    return prefix or None


def _parse_team_subject(value: Any) -> dict[str, str | None]:
    raw = _clean(value)
    if not raw:
        return {
            "team_subject_raw_candidate": None,
            "team_name_raw_candidate": None,
            "team_provider_id_candidate": None,
            "team_normalized_key": None,
            "team_subject_parse_status": "TEAM_SUBJECT_MISSING",
        }
    match = re.fullmatch(r"(?P<name>.*?)(?:\s+\((?P<provider_id>[0-9]+)\))?", raw)
    if not match or not _clean(match.group("name")):
        return {
            "team_subject_raw_candidate": raw,
            "team_name_raw_candidate": None,
            "team_provider_id_candidate": None,
            "team_normalized_key": None,
            "team_subject_parse_status": "TEAM_SUBJECT_PARSE_REVIEW_REQUIRED",
        }
    name = _clean(match.group("name"))
    provider_id = _clean(match.group("provider_id")) or None
    return {
        "team_subject_raw_candidate": raw,
        "team_name_raw_candidate": name,
        "team_provider_id_candidate": provider_id,
        "team_normalized_key": _normalize(name) or None,
        "team_subject_parse_status": "TEAM_SUBJECT_PARSED_CANDIDATE",
    }


def _parse_actor_subject(value: Any) -> dict[str, str | None]:
    raw = _clean(value)
    if not raw:
        return {
            "actor_subject_raw_candidate": None,
            "actor_name_raw_candidate": None,
            "actor_provider_id_candidate": None,
            "jersey_number_candidate": None,
            "actor_normalized_key": None,
            "actor_subject_parse_status": "ACTOR_SUBJECT_MISSING",
        }
    match = re.fullmatch(
        r"(?:(?P<jersey>[0-9]+)\.\s+)?(?P<name>.*?)(?:\s+\((?P<provider_id>[0-9]+)\))?",
        raw,
    )
    if not match or not _clean(match.group("name")):
        return {
            "actor_subject_raw_candidate": raw,
            "actor_name_raw_candidate": None,
            "actor_provider_id_candidate": None,
            "jersey_number_candidate": None,
            "actor_normalized_key": None,
            "actor_subject_parse_status": "ACTOR_SUBJECT_PARSE_REVIEW_REQUIRED",
        }
    name = _clean(match.group("name"))
    return {
        "actor_subject_raw_candidate": raw,
        "actor_name_raw_candidate": name,
        "actor_provider_id_candidate": _clean(match.group("provider_id")) or None,
        "jersey_number_candidate": _clean(match.group("jersey")) or None,
        "actor_normalized_key": _normalize(name) or None,
        "actor_subject_parse_status": "ACTOR_SUBJECT_PARSED_CANDIDATE",
    }


def _validate_atom(atom: dict[str, Any], index: int, binding_id: str) -> list[str]:
    blocks: list[str] = []
    if not _clean(atom.get("evidence_atom_id")):
        blocks.append(f"evidence_atom_id_missing:{index}")
    if atom.get("match_surface_binding_id") != binding_id:
        blocks.append(f"match_surface_binding_mismatch:{index}")
    if atom.get("source_role") not in ALLOWED_SOURCE_ROLES:
        blocks.append(f"source_role_rejected:{index}")
    if atom.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
        blocks.append(f"canonical_event_claimed:{index}")
    if atom.get("validated_event_identity") is True or atom.get("physical_action_identity_truth") is True:
        blocks.append(f"event_or_physical_identity_claimed:{index}")
    if atom.get("event_instance_allowed") is True or atom.get("cross_role_fusion_allowed") is True:
        blocks.append(f"event_or_cross_role_admission_open:{index}")
    if atom.get("independent_source_vote_allowed") is True or int(atom.get("independent_support_vote_count") or 0) != 0:
        blocks.append(f"independent_support_vote_claimed:{index}")

    lineage = atom.get("source_lineage_records")
    if not isinstance(lineage, list) or not lineage:
        blocks.append(f"source_lineage_records_missing:{index}")
        return blocks
    observed_formats: set[str] = set()
    for j, record in enumerate(lineage):
        if not isinstance(record, dict):
            blocks.append(f"source_lineage_record_invalid:{index}:{j}")
            continue
        fmt = _clean(record.get("source_format")).casefold()
        if fmt not in {"csv", "xml"}:
            blocks.append(f"source_lineage_format_rejected:{index}:{fmt or 'UNKNOWN'}")
        observed_formats.add(fmt)
        if not _valid_sha256(record.get("source_sha256")):
            blocks.append(f"source_lineage_sha_invalid:{index}:{j}")
        if record.get("source_row_index_is_order_truth") is True:
            blocks.append(f"source_row_index_promoted_to_order_truth:{index}:{j}")
    if not observed_formats.issubset({"csv", "xml"}):
        blocks.append(f"non_event_surface_lineage_present:{index}")
    return blocks


def _prepare_atom(atom: dict[str, Any]) -> dict[str, Any]:
    source_role = str(atom.get("source_role") or "")
    is_admin = bool(atom.get("identity_not_applicable")) or atom.get("atom_class") == "ADMINISTRATIVE_ATOM"
    team = _parse_team_subject(atom.get("team_raw_candidate"))
    actor_prefix = (
        _exact_subject_prefix(atom.get("code_raw"), atom.get("raw_label"))
        if source_role in ACTOR_SOURCE_ROLES and not is_admin
        else None
    )
    actor = _parse_actor_subject(actor_prefix)
    return {
        "atom": atom,
        "source_role": source_role,
        "identity_applicable": not is_admin,
        **team,
        **actor,
    }


def build_match_local_identity_candidates(evidence_payload: dict[str, Any]) -> dict[str, Any]:
    blocks: list[str] = []
    reviews: list[str] = []
    if evidence_payload.get("module_id") != INPUT_MODULE_ID:
        blocks.append("evidence_atom_module_id_mismatch")
    if evidence_payload.get("canonical_event_count") != CANONICAL_EVENT_COUNT:
        blocks.append("canonical_event_count_claimed_by_input")
    if evidence_payload.get("production_release") is True:
        blocks.append("unexpected_production_claim_by_input")
    if evidence_payload.get("hard_block_hits"):
        blocks.append("evidence_atom_hard_blocks_present")
    if evidence_payload.get("event_instance_allowed") is True:
        blocks.append("event_instance_admission_open_by_input")
    if evidence_payload.get("cross_role_fusion_allowed") is True:
        blocks.append("cross_role_fusion_open_by_input")

    binding_id = _clean(evidence_payload.get("match_surface_binding_id"))
    if not binding_id:
        blocks.append("match_surface_binding_missing")
    atoms = evidence_payload.get("evidence_atoms") or []
    if not isinstance(atoms, list) or not atoms:
        blocks.append("evidence_atom_inventory_empty_or_invalid")
        atoms = []
    if evidence_payload.get("evidence_atom_count") != len(atoms):
        blocks.append("evidence_atom_count_mismatch")

    seen: set[str] = set()
    for index, atom in enumerate(atoms):
        if not isinstance(atom, dict):
            blocks.append(f"evidence_atom_record_invalid:{index}")
            continue
        blocks.extend(_validate_atom(atom, index, binding_id))
        atom_id = _clean(atom.get("evidence_atom_id"))
        if atom_id in seen:
            blocks.append(f"duplicate_evidence_atom_id:{atom_id}")
        seen.add(atom_id)
    blocks = sorted(set(blocks))
    prepared = [_prepare_atom(atom) for atom in atoms if isinstance(atom, dict)] if not blocks else []

    team_aliases: dict[str, set[str]] = defaultdict(set)
    team_provider_ids: dict[str, set[str]] = defaultdict(set)
    team_atom_ids: dict[str, set[str]] = defaultdict(set)
    provider_team_to_keys: dict[str, set[str]] = defaultdict(set)
    for row in prepared:
        if not row["identity_applicable"]:
            continue
        key = row.get("team_normalized_key")
        if not key:
            continue
        key = str(key)
        team_aliases[key].add(str(row.get("team_subject_raw_candidate")))
        provider_id = row.get("team_provider_id_candidate")
        if provider_id:
            team_provider_ids[key].add(str(provider_id))
            provider_team_to_keys[str(provider_id)].add(key)
        team_atom_ids[key].add(str(row["atom"].get("evidence_atom_id")))

    provider_team_conflicts = {pid for pid, keys in provider_team_to_keys.items() if len(keys) > 1}
    team_candidates: list[dict[str, Any]] = []
    team_by_key: dict[str, dict[str, Any]] = {}
    for key in sorted(team_aliases):
        provider_ids = sorted(team_provider_ids.get(key, set()))
        state = (
            "TEAM_PROVIDER_ID_CONFLICT_REVIEW_REQUIRED"
            if len(provider_ids) > 1 or any(pid in provider_team_conflicts for pid in provider_ids)
            else "TEAM_IDENTITY_CANDIDATE_BOUND"
        )
        provider_seed = provider_ids[0] if len(provider_ids) == 1 else "NO_SINGLE_PROVIDER_ID"
        candidate = {
            "team_identity_candidate_id": "teamc_" + _digest(binding_id, key, provider_seed)[:24],
            "match_surface_binding_id": binding_id,
            "team_normalized_key": key,
            "team_aliases_raw": sorted(team_aliases[key]),
            "team_provider_id_candidates": provider_ids,
            "supporting_evidence_atom_ids": sorted(team_atom_ids[key]),
            "decision_state": state,
            "identity_scope": "MATCH_LOCAL_CANDIDATE_ONLY",
            "validated_team_identity": False,
            "global_identity_claim_allowed": False,
        }
        team_candidates.append(candidate)
        team_by_key[key] = candidate

    actor_aliases: dict[tuple[str, str], set[str]] = defaultdict(set)
    actor_provider_ids: dict[tuple[str, str], set[str]] = defaultdict(set)
    actor_jerseys: dict[tuple[str, str], set[str]] = defaultdict(set)
    actor_atom_ids: dict[tuple[str, str], set[str]] = defaultdict(set)
    provider_actor_to_teams: dict[str, set[str]] = defaultdict(set)
    for row in prepared:
        if not row["identity_applicable"] or row["source_role"] not in ACTOR_SOURCE_ROLES:
            continue
        team_key = row.get("team_normalized_key")
        actor_key = row.get("actor_normalized_key")
        if not team_key or not actor_key:
            continue
        key = (str(team_key), str(actor_key))
        actor_aliases[key].add(str(row.get("actor_subject_raw_candidate")))
        pid = row.get("actor_provider_id_candidate")
        if pid:
            actor_provider_ids[key].add(str(pid))
            provider_actor_to_teams[str(pid)].add(str(team_key))
        jersey = row.get("jersey_number_candidate")
        if jersey:
            actor_jerseys[key].add(str(jersey))
        actor_atom_ids[key].add(str(row["atom"].get("evidence_atom_id")))

    cross_team_actor_conflicts = {pid for pid, teams in provider_actor_to_teams.items() if len(teams) > 1}
    actor_candidates: list[dict[str, Any]] = []
    actor_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for key in sorted(actor_aliases):
        team_key, actor_key = key
        pids = sorted(actor_provider_ids.get(key, set()))
        jerseys = sorted(actor_jerseys.get(key, set()))
        team_candidate = team_by_key.get(team_key)
        if team_candidate is None or team_candidate["decision_state"] != "TEAM_IDENTITY_CANDIDATE_BOUND":
            state = "TEAM_PROVIDER_ID_CONFLICT_REVIEW_REQUIRED"
        elif len(pids) > 1:
            state = "ACTOR_PROVIDER_ID_CONFLICT_REVIEW_REQUIRED"
        elif any(pid in cross_team_actor_conflicts for pid in pids):
            state = "CROSS_TEAM_PROVIDER_ID_CONFLICT_REVIEW_REQUIRED"
        elif len(jerseys) > 1:
            state = "AMBIGUOUS_ALIAS_REVIEW_REQUIRED"
        else:
            state = "ACTOR_IDENTITY_CANDIDATE_BOUND"
        provider_seed = pids[0] if len(pids) == 1 else "NO_SINGLE_PROVIDER_ID"
        team_id = team_candidate.get("team_identity_candidate_id") if team_candidate else "TEAM_MISSING"
        candidate = {
            "actor_identity_candidate_id": "actorc_" + _digest(binding_id, team_id, actor_key, provider_seed)[:24],
            "match_surface_binding_id": binding_id,
            "team_identity_candidate_id": team_id if team_candidate else None,
            "team_normalized_key": team_key,
            "actor_normalized_key": actor_key,
            "actor_aliases_raw": sorted(actor_aliases[key]),
            "actor_provider_id_candidates": pids,
            "jersey_number_candidates": jerseys,
            "supporting_evidence_atom_ids": sorted(actor_atom_ids[key]),
            "decision_state": state,
            "identity_scope": "MATCH_LOCAL_CANDIDATE_ONLY",
            "validated_player_identity": False,
            "global_identity_claim_allowed": False,
        }
        actor_candidates.append(candidate)
        actor_by_key[key] = candidate

    bindings: list[dict[str, Any]] = []
    for row in prepared:
        atom = row["atom"]
        source_role = row["source_role"]
        team_key = row.get("team_normalized_key")
        actor_key = row.get("actor_normalized_key")
        team_candidate = team_by_key.get(str(team_key)) if team_key else None
        actor_candidate = actor_by_key.get((str(team_key), str(actor_key))) if team_key and actor_key else None
        if not row["identity_applicable"]:
            state = "IDENTITY_NOT_APPLICABLE"
        elif row.get("team_subject_parse_status") == "TEAM_SUBJECT_PARSE_REVIEW_REQUIRED":
            state = "SOURCE_SUBJECT_PARSE_REVIEW_REQUIRED"
        elif not team_key:
            state = "TEAM_CANDIDATE_MISSING"
        elif team_candidate and team_candidate["decision_state"] != "TEAM_IDENTITY_CANDIDATE_BOUND":
            state = team_candidate["decision_state"]
        elif source_role == "TEAM_SURFACE_CANDIDATE":
            state = "TEAM_IDENTITY_CANDIDATE_BOUND"
        elif source_role in ACTOR_SOURCE_ROLES:
            if row.get("actor_subject_parse_status") == "ACTOR_SUBJECT_PARSE_REVIEW_REQUIRED":
                state = "SOURCE_SUBJECT_PARSE_REVIEW_REQUIRED"
            elif not actor_key:
                state = "ACTOR_CANDIDATE_MISSING"
            elif actor_candidate:
                state = actor_candidate["decision_state"]
            else:
                state = "ACTOR_CANDIDATE_MISSING"
        else:
            state = "SOURCE_SUBJECT_PARSE_REVIEW_REQUIRED"
        bindings.append({
            "evidence_atom_id": atom.get("evidence_atom_id"),
            "match_surface_binding_id": binding_id,
            "source_role": source_role,
            "atom_class": atom.get("atom_class"),
            "atom_status": atom.get("atom_status"),
            "upstream_review_hits": list(atom.get("review_hits") or []),
            "team_identity_candidate_id": team_candidate.get("team_identity_candidate_id") if team_candidate else None,
            "actor_identity_candidate_id": actor_candidate.get("actor_identity_candidate_id") if actor_candidate else None,
            "team_subject_raw_candidate": row.get("team_subject_raw_candidate"),
            "team_name_raw_candidate": row.get("team_name_raw_candidate"),
            "team_provider_id_candidate": row.get("team_provider_id_candidate"),
            "actor_subject_raw_candidate": row.get("actor_subject_raw_candidate"),
            "actor_name_raw_candidate": row.get("actor_name_raw_candidate"),
            "actor_provider_id_candidate": row.get("actor_provider_id_candidate"),
            "jersey_number_candidate": row.get("jersey_number_candidate"),
            "decision_state": state,
            "identity_scope": "MATCH_LOCAL_CANDIDATE_ONLY",
            "validated_team_identity": False,
            "validated_player_identity": False,
            "validated_event_identity": False,
            "event_instance_allowed": False,
            "cross_role_fusion_allowed": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    state_counts = Counter(item["decision_state"] for item in bindings)
    review_count = sum(item["decision_state"] not in BOUND_STATES for item in bindings)
    if str(evidence_payload.get("status") or evidence_payload.get("module_status") or "UNKNOWN") == "REVIEW_REQUIRED":
        reviews.append("evidence_atom_upstream_review_preserved")
    if review_count:
        reviews.append("match_local_identity_candidate_review_required")
    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")

    team_bound = state_counts.get("TEAM_IDENTITY_CANDIDATE_BOUND", 0)
    actor_bound = state_counts.get("ACTOR_IDENTITY_CANDIDATE_BOUND", 0)
    return {
        "module_id": MODULE_ID,
        "status": status,
        "module_status": status,
        "runtime_evidence_status": "NOT_EVALUATED",
        "release_status": "NOT_PRODUCTION",
        "match_surface_binding_id": binding_id or None,
        "team_identity_candidates": team_candidates,
        "actor_identity_candidates": actor_candidates,
        "identity_bindings": bindings,
        "evidence_atom_count": len(atoms),
        "identity_binding_record_count": len(bindings),
        "identity_candidate_bound_atom_count": team_bound + actor_bound,
        "team_candidate_bound_atom_count": team_bound,
        "actor_candidate_bound_atom_count": actor_bound,
        "identity_not_applicable_atom_count": state_counts.get("IDENTITY_NOT_APPLICABLE", 0),
        "identity_review_required_atom_count": review_count,
        "team_identity_candidate_count": len(team_candidates),
        "actor_identity_candidate_count": len(actor_candidates),
        "decision_state_counts": dict(sorted(state_counts.items())),
        "hard_block_hits": blocks,
        "review_hits": reviews,
        "active_match_evidence_pass": False,
        "identity_scope": "MATCH_LOCAL_CANDIDATE_ONLY",
        "identity_truth_admitted": False,
        "global_roster_identity_admitted": False,
        "cross_match_identity_admitted": False,
        "validated_team_identity": False,
        "validated_player_identity": False,
        "validated_event_identity": False,
        "physical_action_identity_truth": False,
        "base_event_admission_allowed": False,
        "action_bundle_candidate_count": 0,
        "event_instance_count": 0,
        "event_instance_allowed": False,
        "cross_role_fusion_allowed": False,
        "independent_source_vote_allowed": False,
        "metric_value_output_allowed": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "true_action_count": "UNKNOWN",
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
    }


def render_summary(payload: dict[str, Any]) -> str:
    keys = (
        "status", "evidence_atom_count", "team_identity_candidate_count",
        "actor_identity_candidate_count", "identity_candidate_bound_atom_count",
        "identity_not_applicable_atom_count", "identity_review_required_atom_count",
    )
    lines = ["HPFA MATCH-LOCAL IDENTITY CANDIDATES LITE V1"]
    lines.extend(f"{key}={payload.get(key)}" for key in keys)
    lines.extend([
        f"hard_block_hits={payload.get('hard_block_hits')}",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
        "",
    ])
    return "\n".join(lines)


def render_analyst(payload: dict[str, Any]) -> str:
    return "\n".join([
        "HPFA Match-Local Identity Analyst Audit V1",
        "===========================================",
        f"team identity candidates={payload.get('team_identity_candidate_count')}",
        f"actor identity candidates={payload.get('actor_identity_candidate_count')}",
        f"bound evidence atoms={payload.get('identity_candidate_bound_atom_count')}",
        f"identity not applicable atoms={payload.get('identity_not_applicable_atom_count')}",
        f"identity review-required atoms={payload.get('identity_review_required_atom_count')}",
        "",
        "Safe meaning:",
        "Visible Evidence Atoms are linked to match-local team/actor candidates only when exact visible subject evidence supports the link.",
        "TEAM surfaces receive team-only bindings; PLAYER and GOALKEEPER surfaces may receive actor bindings.",
        "Administrative atoms remain identity-not-applicable; upstream semantic review is preserved separately from identity parsing.",
        "No binding is global roster identity, canonical event identity or physical action truth.",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
        "",
    ])


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> dict[str, Path]:
    out = validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = {key: out / name for key, name in OUTPUTS.items()}
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    paths["summary"].write_text(render_summary(payload), encoding="utf-8")
    paths["analyst"].write_text(render_analyst(payload), encoding="utf-8")
    return paths
