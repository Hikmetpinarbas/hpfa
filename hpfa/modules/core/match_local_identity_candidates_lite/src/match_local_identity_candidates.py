from __future__ import annotations

import argparse
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
IDENTITY_NOT_APPLICABLE_CLASSES = {"ADMINISTRATIVE_ATOM"}
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


def validate_out(path: str | Path) -> Path:
    output = Path(path).expanduser().resolve(strict=False)
    if "HPFA" in output.parts and output.name != "HPFA":
        raise ValueError("nested_phone_output_directory_rejected")
    return output


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("evidence_atom_output_unreadable_or_malformed") from exc
    if not isinstance(payload, dict):
        raise ValueError("evidence_atom_output_not_object")
    return payload


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
    provider_id = _clean(match.group("provider_id")) or None
    jersey = _clean(match.group("jersey")) or None
    return {
        "actor_subject_raw_candidate": raw,
        "actor_name_raw_candidate": name,
        "actor_provider_id_candidate": provider_id,
        "jersey_number_candidate": jersey,
        "actor_normalized_key": _normalize(name) or None,
        "actor_subject_parse_status": "ACTOR_SUBJECT_PARSED_CANDIDATE",
    }


def _validate_atom(atom: dict[str, Any], index: int, expected_binding: str) -> list[str]:
    blocks: list[str] = []
    if not _clean(atom.get("evidence_atom_id")):
        blocks.append(f"evidence_atom_id_missing:{index}")
    if atom.get("match_surface_binding_id") != expected_binding:
        blocks.append(f"match_surface_binding_mismatch:{index}")
    if atom.get("source_role") not in ALLOWED_SOURCE_ROLES:
        blocks.append(f"source_role_rejected:{index}")
    source_paths = atom.get("source_relative_paths") or []
    source_shas = atom.get("source_sha256_lineage") or []
    runtime_shas = atom.get("runtime_rehashed_sha256") or {}
    if not isinstance(source_paths, list) or len(source_paths) != 2 or not all(_clean(item) for item in source_paths):
        blocks.append(f"source_paths_invalid:{index}")
    if not isinstance(source_shas, list) or len(source_shas) != 2 or not all(_valid_sha256(item) for item in source_shas):
        blocks.append(f"source_sha_lineage_invalid:{index}")
    if not isinstance(runtime_shas, dict) or not _valid_sha256(runtime_shas.get("csv")) or not _valid_sha256(runtime_shas.get("xml")):
        blocks.append(f"runtime_sha_lineage_invalid:{index}")
    if isinstance(source_shas, list) and len(source_shas) == 2 and isinstance(runtime_shas, dict):
        if str(source_shas[0]).casefold() != str(runtime_shas.get("csv") or "").casefold():
            blocks.append(f"csv_sha_mismatch:{index}")
        if str(source_shas[1]).casefold() != str(runtime_shas.get("xml") or "").casefold():
            blocks.append(f"xml_sha_mismatch:{index}")
    if atom.get("canonical_event_count") not in {None, CANONICAL_EVENT_COUNT}:
        blocks.append(f"canonical_event_claimed:{index}")
    if atom.get("validated_event_identity") is True:
        blocks.append(f"validated_event_identity_claimed:{index}")
    return blocks


def _build_prepared_atoms(atoms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for atom in atoms:
        source_role = str(atom.get("source_role") or "")
        atom_class = str(atom.get("atom_class") or "")
        team = _parse_team_subject(atom.get("team_raw_candidate"))
        actor_prefix = (
            _exact_subject_prefix(atom.get("code_raw"), atom.get("raw_label"))
            if source_role in ACTOR_SOURCE_ROLES
            else None
        )
        actor = _parse_actor_subject(actor_prefix)
        identity_applicable = atom_class not in IDENTITY_NOT_APPLICABLE_CLASSES
        prepared.append(
            {
                "atom": atom,
                "source_role": source_role,
                "atom_class": atom_class,
                "identity_applicable": identity_applicable,
                **team,
                **actor,
            }
        )
    return prepared


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

    binding_id = _clean(evidence_payload.get("match_surface_binding_id"))
    if not binding_id:
        blocks.append("match_surface_binding_missing")

    atoms = evidence_payload.get("evidence_atoms") or []
    if not isinstance(atoms, list) or not atoms:
        blocks.append("evidence_atom_inventory_empty_or_invalid")
        atoms = []
    expected_count = evidence_payload.get("evidence_atom_count")
    if expected_count != len(atoms):
        blocks.append("evidence_atom_count_mismatch")

    seen_atom_ids: set[str] = set()
    for index, atom in enumerate(atoms):
        if not isinstance(atom, dict):
            blocks.append(f"evidence_atom_record_invalid:{index}")
            continue
        blocks.extend(_validate_atom(atom, index, binding_id))
        atom_id = _clean(atom.get("evidence_atom_id"))
        if atom_id in seen_atom_ids:
            blocks.append(f"duplicate_evidence_atom_id:{atom_id}")
        seen_atom_ids.add(atom_id)

    prepared = _build_prepared_atoms([atom for atom in atoms if isinstance(atom, dict)]) if not blocks else []

    team_aliases: dict[str, set[str]] = defaultdict(set)
    team_provider_ids: dict[str, set[str]] = defaultdict(set)
    team_atom_ids: dict[str, set[str]] = defaultdict(set)
    provider_team_to_keys: dict[str, set[str]] = defaultdict(set)

    for row in prepared:
        if not row["identity_applicable"]:
            continue
        team_key = row.get("team_normalized_key")
        if not team_key:
            continue
        team_aliases[team_key].add(str(row.get("team_subject_raw_candidate")))
        provider_id = row.get("team_provider_id_candidate")
        if provider_id:
            team_provider_ids[team_key].add(str(provider_id))
            provider_team_to_keys[str(provider_id)].add(str(team_key))
        team_atom_ids[team_key].add(str(row["atom"].get("evidence_atom_id")))

    team_candidates: list[dict[str, Any]] = []
    team_by_key: dict[str, dict[str, Any]] = {}
    provider_team_conflicts = {
        provider_id
        for provider_id, keys in provider_team_to_keys.items()
        if len(keys) > 1
    }
    for team_key in sorted(team_aliases):
        aliases = sorted(team_aliases[team_key])
        provider_ids = sorted(team_provider_ids.get(team_key, set()))
        if len(provider_ids) > 1:
            state = "TEAM_PROVIDER_ID_CONFLICT_REVIEW_REQUIRED"
        elif any(provider_id in provider_team_conflicts for provider_id in provider_ids):
            state = "TEAM_PROVIDER_ID_CONFLICT_REVIEW_REQUIRED"
        else:
            state = "TEAM_IDENTITY_CANDIDATE_BOUND"
        provider_seed = provider_ids[0] if len(provider_ids) == 1 else "NO_SINGLE_PROVIDER_ID"
        candidate = {
            "team_identity_candidate_id": "teamc_" + _digest(binding_id, team_key, provider_seed)[:24],
            "match_surface_binding_id": binding_id,
            "team_normalized_key": team_key,
            "team_aliases_raw": aliases,
            "team_provider_id_candidates": provider_ids,
            "supporting_evidence_atom_ids": sorted(team_atom_ids.get(team_key, set())),
            "decision_state": state,
            "identity_scope": "MATCH_LOCAL_CANDIDATE_ONLY",
            "validated_team_identity": False,
            "global_identity_claim_allowed": False,
        }
        team_candidates.append(candidate)
        team_by_key[team_key] = candidate

    actor_aliases: dict[tuple[str, str], set[str]] = defaultdict(set)
    actor_provider_ids: dict[tuple[str, str], set[str]] = defaultdict(set)
    actor_jerseys: dict[tuple[str, str], set[str]] = defaultdict(set)
    actor_atom_ids: dict[tuple[str, str], set[str]] = defaultdict(set)
    provider_actor_to_team_keys: dict[str, set[str]] = defaultdict(set)

    for row in prepared:
        if not row["identity_applicable"] or row["source_role"] not in ACTOR_SOURCE_ROLES:
            continue
        team_key = row.get("team_normalized_key")
        actor_key = row.get("actor_normalized_key")
        if not team_key or not actor_key:
            continue
        key = (str(team_key), str(actor_key))
        actor_aliases[key].add(str(row.get("actor_subject_raw_candidate")))
        provider_id = row.get("actor_provider_id_candidate")
        if provider_id:
            actor_provider_ids[key].add(str(provider_id))
            provider_actor_to_team_keys[str(provider_id)].add(str(team_key))
        jersey = row.get("jersey_number_candidate")
        if jersey:
            actor_jerseys[key].add(str(jersey))
        actor_atom_ids[key].add(str(row["atom"].get("evidence_atom_id")))

    cross_team_provider_conflicts = {
        provider_id
        for provider_id, team_keys in provider_actor_to_team_keys.items()
        if len(team_keys) > 1
    }
    actor_candidates: list[dict[str, Any]] = []
    actor_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for key in sorted(actor_aliases):
        team_key, actor_key = key
        aliases = sorted(actor_aliases[key])
        provider_ids = sorted(actor_provider_ids.get(key, set()))
        jerseys = sorted(actor_jerseys.get(key, set()))
        team_candidate = team_by_key.get(team_key)
        if team_candidate is None or team_candidate["decision_state"] != "TEAM_IDENTITY_CANDIDATE_BOUND":
            state = "TEAM_PROVIDER_ID_CONFLICT_REVIEW_REQUIRED"
        elif len(provider_ids) > 1:
            state = "ACTOR_PROVIDER_ID_CONFLICT_REVIEW_REQUIRED"
        elif any(provider_id in cross_team_provider_conflicts for provider_id in provider_ids):
            state = "CROSS_TEAM_PROVIDER_ID_CONFLICT_REVIEW_REQUIRED"
        elif len(jerseys) > 1:
            state = "AMBIGUOUS_ALIAS_REVIEW_REQUIRED"
        else:
            state = "ACTOR_IDENTITY_CANDIDATE_BOUND"
        provider_seed = provider_ids[0] if len(provider_ids) == 1 else "NO_SINGLE_PROVIDER_ID"
        team_candidate_id = team_candidate.get("team_identity_candidate_id") if team_candidate else "TEAM_MISSING"
        candidate = {
            "actor_identity_candidate_id": "actorc_"
            + _digest(binding_id, team_candidate_id, actor_key, provider_seed)[:24],
            "match_surface_binding_id": binding_id,
            "team_identity_candidate_id": team_candidate_id if team_candidate else None,
            "team_normalized_key": team_key,
            "actor_normalized_key": actor_key,
            "actor_aliases_raw": aliases,
            "actor_provider_id_candidates": provider_ids,
            "jersey_number_candidates": jerseys,
            "supporting_evidence_atom_ids": sorted(actor_atom_ids.get(key, set())),
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
        atom_id = atom.get("evidence_atom_id")
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
            elif actor_candidate and actor_candidate["decision_state"] == "ACTOR_IDENTITY_CANDIDATE_BOUND":
                state = "ACTOR_IDENTITY_CANDIDATE_BOUND"
            elif actor_candidate:
                state = actor_candidate["decision_state"]
            else:
                state = "ACTOR_CANDIDATE_MISSING"
        else:
            state = "SOURCE_SUBJECT_PARSE_REVIEW_REQUIRED"

        bindings.append(
            {
                "evidence_atom_id": atom_id,
                "match_surface_binding_id": binding_id,
                "source_role": source_role,
                "atom_class": row["atom_class"],
                "team_identity_candidate_id": (
                    team_candidate.get("team_identity_candidate_id") if team_candidate else None
                ),
                "actor_identity_candidate_id": (
                    actor_candidate.get("actor_identity_candidate_id") if actor_candidate else None
                ),
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
                "claim_ceiling": CLAIM_CEILING,
            }
        )

    state_counts = Counter(binding["decision_state"] for binding in bindings)
    review_count = sum(binding["decision_state"] not in BOUND_STATES for binding in bindings)
    not_applicable_count = state_counts.get("IDENTITY_NOT_APPLICABLE", 0)
    team_bound_count = state_counts.get("TEAM_IDENTITY_CANDIDATE_BOUND", 0)
    actor_bound_count = state_counts.get("ACTOR_IDENTITY_CANDIDATE_BOUND", 0)
    identity_bound_count = team_bound_count + actor_bound_count

    input_status = str(evidence_payload.get("module_status") or evidence_payload.get("status") or "UNKNOWN")
    if input_status == "FAIL_CLOSED":
        blocks.append("evidence_atom_input_fail_closed")
    elif input_status == "REVIEW_REQUIRED":
        reviews.append("evidence_atom_upstream_review_required")
    elif input_status != "PASS":
        reviews.append(f"evidence_atom_upstream_status_review:{input_status}")
    if review_count:
        reviews.append("match_local_identity_candidate_review_required")

    blocks = sorted(set(blocks))
    reviews = sorted(set(reviews))
    status = "FAIL_CLOSED" if blocks else ("REVIEW_REQUIRED" if reviews else "PASS")

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
        "identity_candidate_bound_atom_count": identity_bound_count,
        "team_candidate_bound_atom_count": team_bound_count,
        "actor_candidate_bound_atom_count": actor_bound_count,
        "identity_not_applicable_atom_count": not_applicable_count,
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
        "base_event_admission_allowed": False,
        "action_bundle_candidate_count": 0,
        "event_instance_count": 0,
        "metric_value_output_allowed": False,
        "comparison_allowed": False,
        "claim_allowed": False,
        "sequence_truth": False,
        "possession_truth": False,
        "phase_truth": False,
        "tactical_truth": False,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "production_release": False,
        "claim_ceiling": CLAIM_CEILING,
        "analyst_evidence": {
            "safe_statement": (
                "Visible evidence atoms were linked to match-local team and actor identity candidates where exact source subjects were available. "
                "The bindings are candidate-only and do not establish global person, team or event identity."
            )
        },
    }


def render_summary(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            "HPFA MATCH-LOCAL IDENTITY CANDIDATES LITE V1",
            f"status={payload.get('status')}",
            f"evidence_atom_count={payload.get('evidence_atom_count')}",
            f"team_identity_candidate_count={payload.get('team_identity_candidate_count')}",
            f"actor_identity_candidate_count={payload.get('actor_identity_candidate_count')}",
            f"identity_candidate_bound_atom_count={payload.get('identity_candidate_bound_atom_count')}",
            f"identity_not_applicable_atom_count={payload.get('identity_not_applicable_atom_count')}",
            f"identity_review_required_atom_count={payload.get('identity_review_required_atom_count')}",
            f"hard_block_hits={payload.get('hard_block_hits')}",
            "canonical_event_count=UNKNOWN",
            "production_release=false",
            "",
        ]
    )


def write_outputs(payload: dict[str, Any], out_dir: str | Path) -> None:
    out = validate_out(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / OUTPUTS["json"]).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / OUTPUTS["summary"]).write_text(render_summary(payload), encoding="utf-8")
    statement = (payload.get("analyst_evidence") or {}).get("safe_statement", "")
    (out / OUTPUTS["analyst"]).write_text(
        statement + "\ncanonical_event_count=UNKNOWN\nproduction_release=false\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-atom", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    payload = build_match_local_identity_candidates(load_json(args.evidence_atom))
    write_outputs(payload, args.out)
    print(
        json.dumps(
            {
                key: payload.get(key)
                for key in (
                    "status",
                    "evidence_atom_count",
                    "team_identity_candidate_count",
                    "actor_identity_candidate_count",
                    "identity_candidate_bound_atom_count",
                    "identity_not_applicable_atom_count",
                    "identity_review_required_atom_count",
                    "canonical_event_count",
                    "production_release",
                )
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 2 if payload["status"] == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
