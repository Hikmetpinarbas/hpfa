from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MODULE_ID = "base_event_label_semantic_classifier_lite_v1"
OUTPUT_JSON = "base_event_label_match_test_v1.json"
OUTPUT_TXT = "base_event_label_match_test_v1.txt"

BASE_EVENT_FAMILIES = {
    "PASS": ("pass", "passes", "cross", "crosses", "assist"),
    "SHOT": ("shot", "shots", "goal", "goals", "woodwork"),
    "RECOVERY": ("ball_recovery", "ball_recoveries", "loose_ball_recovery", "loose_ball_recoveries"),
    "INTERCEPTION": ("interception", "interceptions"),
    "TACKLE": ("tackle", "tackles"),
    "DUEL": ("challenge", "challenges", "aerial_challenge", "aerial_challenges", "duel", "duels"),
    "CARRY_DRIBBLE": ("carry", "carries", "dribble", "dribbles", "take_on", "take_ons"),
    "BALL_LOSS": ("lost_ball", "lost_balls", "ball_loss", "ball_losses", "dispossessed", "miscontrol"),
    "FOUL": ("foul", "fouls", "handball"),
    "RESTART": ("goal_kick", "goal_kicks", "corner", "corners", "throw_in", "throw_ins", "free_kick", "kick_off"),
    "SAVE_GK_ACTION": ("save", "saves", "shots_saved", "claim", "claims", "punch", "punches", "sweeping_action"),
}

OUTCOME_TOKENS = (
    "accurate", "inaccurate", "successful", "unsuccessful", "won", "lost",
    "on_target", "off_target", "blocked", "saved", "goal",
)
QUALIFIER_TOKENS = (
    "forward", "backward", "progressive", "long", "short", "medium",
    "penalty_box", "final_third", "cross", "through_ball",
)
CONTEXT_TOKENS = (
    "positional_attack", "counterattack", "counter_attack", "set_piece",
    "transition", "open_play", "attack_with_shot",
)
PARTICIPATION_TOKENS = ("involvement_in_", "participation")
DERIVED_CLASS_TOKENS = (
    "successful_pressure", "high_threat_loss", "mistake_leading_to",
    "chance_creation", "supersave", "super_save",
)


def _raw(value: Any) -> str:
    return "" if value is None else str(value)


def _clean(value: Any) -> str:
    return " ".join(_raw(value).split()).strip()


def _number_text(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    try:
        return f"{float(text):.6f}"
    except ValueError:
        return text


def _label(atom: dict[str, Any]) -> str:
    return _clean(atom.get("normalized_label")).lower()


def _contains_token(label: str, token: str) -> bool:
    return label == token or label.startswith(token + "_") or label.endswith("_" + token) or ("_" + token + "_") in label


def infer_base_event_families(label: str) -> list[str]:
    found: list[str] = []
    for family, tokens in BASE_EVENT_FAMILIES.items():
        if any(_contains_token(label, token) for token in tokens):
            found.append(family)
    if "PASS" in found and "SHOT" in found and "shot" in label and "pass" in label:
        found.remove("SHOT")
    return found


def infer_semantic_roles(label: str, atom_class: str) -> list[str]:
    if atom_class == "MATCH_BOUNDARY_ATOM":
        return ["MATCH_BOUNDARY"]
    if atom_class == "AGGREGATE_OUTCOME_ATOM":
        return ["AGGREGATE_OUTCOME"]
    roles: list[str] = []
    if infer_base_event_families(label):
        roles.append("BASE_EVENT_SIGNAL")
    if any(token in label for token in PARTICIPATION_TOKENS):
        roles.append("EVENT_PARTICIPATION_LABEL")
    if any(token in label for token in DERIVED_CLASS_TOKENS):
        roles.append("DERIVED_EVENT_CLASS")
    if any(token in label for token in CONTEXT_TOKENS):
        roles.append("EVENT_CONTEXT_LABEL")
    if any(_contains_token(label, token) for token in OUTCOME_TOKENS):
        roles.append("EVENT_OUTCOME_LABEL")
    if any(token in label for token in QUALIFIER_TOKENS):
        roles.append("EVENT_QUALIFIER_LABEL")
    return roles or ["UNRESOLVED_EVENT_LABEL"]


def _actor_token(atom: dict[str, Any]) -> str:
    player = _clean(atom.get("player_raw"))
    if player:
        return player
    code = _clean(atom.get("code_raw"))
    if " - " in code:
        return code.rsplit(" - ", 1)[0].strip()
    team = _clean(atom.get("team_raw"))
    if team:
        return team
    return code or "UNKNOWN_ACTOR"


def _trace_key(atom: dict[str, Any]) -> tuple[str, ...]:
    return (
        _clean(atom.get("match_binding_id")),
        _clean(atom.get("source_role")),
        _clean(atom.get("source_event_id_raw")),
        _number_text(atom.get("start_seconds_candidate")),
        _number_text(atom.get("end_seconds_candidate")),
        _clean(atom.get("code_raw")),
        _clean(atom.get("team_raw")),
        _clean(atom.get("player_raw")),
        _number_text(atom.get("x_meters")),
        _number_text(atom.get("y_meters")),
        _label(atom),
    )


def _action_group_key(trace: dict[str, Any]) -> tuple[str, ...]:
    representative = trace["atoms"][0]
    return (
        _clean(representative.get("match_binding_id")),
        _clean(representative.get("source_role")),
        _actor_token(representative),
        _clean(representative.get("team_raw")),
        _number_text(representative.get("start_seconds_candidate")),
        _number_text(representative.get("end_seconds_candidate")),
        _number_text(representative.get("x_meters")),
        _number_text(representative.get("y_meters")),
    )


def _stable_id(prefix: str, values: tuple[str, ...]) -> str:
    return prefix + hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()[:24]


def build_match_test(evidence_payload: dict[str, Any]) -> dict[str, Any]:
    atoms = evidence_payload.get("evidence_atoms") or []
    traces_by_key: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)

    aggregate_atoms = 0
    boundary_atoms = 0
    explanatory_atoms = 0
    for atom in atoms:
        atom_class = _clean(atom.get("atom_class"))
        if atom_class == "AGGREGATE_OUTCOME_ATOM":
            aggregate_atoms += 1
            continue
        if atom_class == "MATCH_BOUNDARY_ATOM":
            boundary_atoms += 1
            continue
        if atom_class != "EXPLANATORY_EVIDENCE_ATOM":
            continue
        explanatory_atoms += 1
        traces_by_key[_trace_key(atom)].append(atom)

    trace_units: list[dict[str, Any]] = []
    csv_xml_conformant = 0
    one_sided_trace_units = 0
    for key, grouped_atoms in traces_by_key.items():
        formats = sorted({_clean(atom.get("source_format")).lower() for atom in grouped_atoms if _clean(atom.get("source_format"))})
        if formats == ["csv", "xml"]:
            conformance = "CSV_XML_CONFORMANT"
            csv_xml_conformant += 1
        else:
            conformance = "ONE_SIDED_VISIBLE_TRACE"
            one_sided_trace_units += 1
        trace_units.append(
            {
                "trace_unit_id": _stable_id("tu_", key),
                "trace_key": list(key),
                "atoms": grouped_atoms,
                "source_formats": formats,
                "conformance_status": conformance,
            }
        )

    groups_by_key: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for trace in trace_units:
        groups_by_key[_action_group_key(trace)].append(trace)

    base_candidates: list[dict[str, Any]] = []
    label_candidates: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    label_role_counts: Counter[str] = Counter()
    base_family_counts: Counter[str] = Counter()
    attached_label_count = 0
    label_only_group_count = 0

    for group_key, traces in groups_by_key.items():
        family_set: set[str] = set()
        group_labels: list[dict[str, Any]] = []
        for trace in traces:
            atom = trace["atoms"][0]
            label = _label(atom)
            families = infer_base_event_families(label)
            family_set.update(families)
            roles = infer_semantic_roles(label, _clean(atom.get("atom_class")))
            label_role_counts.update(roles)
            label_entry = {
                "event_label_candidate_id": _stable_id("el_", tuple(trace["trace_key"])),
                "normalized_label": label,
                "raw_labels": sorted({_raw(source_atom.get("raw_label")) for source_atom in trace["atoms"]}),
                "semantic_roles": roles,
                "base_event_family_signals": families,
                "label_origin": "PROVIDER_SURFACE",
                "definition_version": "UNKNOWN",
                "validation_status": "REVIEW_REQUIRED_DEFINITION_AUDIT",
                "source_trace_unit_id": trace["trace_unit_id"],
            }
            group_labels.append(label_entry)
            label_candidates.append(label_entry)

        if len(family_set) == 1:
            family = next(iter(family_set))
            candidate_id = _stable_id("be_", group_key + (family,))
            attached_label_count += len(group_labels)
            base_family_counts[family] += 1
            base_candidates.append(
                {
                    "base_event_candidate_id": candidate_id,
                    "base_event_family": family,
                    "action_group_key": list(group_key),
                    "source_trace_unit_ids": [trace["trace_unit_id"] for trace in traces],
                    "event_label_candidate_ids": [entry["event_label_candidate_id"] for entry in group_labels],
                    "surface_candidate_status": "BASE_EVENT_SURFACE_CANDIDATE",
                    "identity_gate_status": "UNRESOLVED",
                    "canonical_admission_status": "BLOCKED_IDENTITY_AND_RELATION_GATES",
                    "claim_ceiling": "BASE_EVENT_CANDIDATE_ONLY",
                }
            )
        elif len(family_set) > 1:
            conflicts.append(
                {
                    "action_group_key": list(group_key),
                    "base_event_family_signals": sorted(family_set),
                    "status": "REVIEW_REQUIRED_MULTIPLE_BASE_EVENT_FAMILIES",
                }
            )
        else:
            label_only_group_count += 1

    decision_state = "REVIEW_REQUIRED_SEMANTIC_CONFLICTS" if conflicts else "PASS_BASE_EVENT_LABEL_MAIN_RULE_MATCH_TEST"
    return {
        "module_id": MODULE_ID,
        "decision_state": decision_state,
        "main_rule": "BASE_EVENT_AND_LABEL_ARE_DISTINCT_BUT_LINKED",
        "evidence_atom_count": len(atoms),
        "explanatory_atom_count": explanatory_atoms,
        "aggregate_outcome_atom_count": aggregate_atoms,
        "match_boundary_atom_count": boundary_atoms,
        "surface_trace_unit_count": len(trace_units),
        "csv_xml_conformant_trace_unit_count": csv_xml_conformant,
        "one_sided_trace_unit_count": one_sided_trace_units,
        "base_event_surface_candidates": base_candidates,
        "base_event_surface_candidate_count": len(base_candidates),
        "base_event_family_counts": dict(sorted(base_family_counts.items())),
        "event_label_candidates": label_candidates,
        "event_label_candidate_count": len(label_candidates),
        "event_label_role_counts": dict(sorted(label_role_counts.items())),
        "attached_event_label_count": attached_label_count,
        "label_only_action_group_count": label_only_group_count,
        "semantic_conflicts": conflicts,
        "semantic_conflict_count": len(conflicts),
        "identity_bound_event_count": 0,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "technical_limits": [
            "Base-event candidates are surface candidates, not canonical events.",
            "Provider labels remain review-required until operational definitions and audit evidence are registered.",
            "Identity, cross-role reflection, action linking, sequence, phase and pattern gates remain downstream.",
        ],
    }


def _reject_nested_phone_output(output_dir: Path) -> None:
    if output_dir.name != "HPFA" or "HPFA" in output_dir.parts[:-1]:
        raise ValueError("nested_phone_output_directory_rejected")


def write_outputs(evidence_json: str | Path, out_dir: str | Path) -> dict[str, Any]:
    output_dir = Path(out_dir)
    _reject_nested_phone_output(output_dir)
    payload = json.loads(Path(evidence_json).read_text(encoding="utf-8"))
    result = build_match_test(payload)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / OUTPUT_JSON).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "HPFA BASE EVENT + EVENT LABEL MATCH TEST V1",
        f"decision_state={result['decision_state']}",
        f"surface_trace_unit_count={result['surface_trace_unit_count']}",
        f"csv_xml_conformant_trace_unit_count={result['csv_xml_conformant_trace_unit_count']}",
        f"base_event_surface_candidate_count={result['base_event_surface_candidate_count']}",
        f"base_event_family_counts={result['base_event_family_counts']}",
        f"event_label_candidate_count={result['event_label_candidate_count']}",
        f"event_label_role_counts={result['event_label_role_counts']}",
        f"semantic_conflict_count={result['semantic_conflict_count']}",
        "identity_bound_event_count=0",
        "canonical_event_count=UNKNOWN",
        "production_release=false",
    ]
    (output_dir / OUTPUT_TXT).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-json", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    result = write_outputs(args.evidence_json, args.out)
    print(json.dumps({
        "decision_state": result["decision_state"],
        "surface_trace_unit_count": result["surface_trace_unit_count"],
        "base_event_surface_candidate_count": result["base_event_surface_candidate_count"],
        "base_event_family_counts": result["base_event_family_counts"],
        "event_label_candidate_count": result["event_label_candidate_count"],
        "event_label_role_counts": result["event_label_role_counts"],
        "semantic_conflict_count": result["semantic_conflict_count"],
        "canonical_event_count": result["canonical_event_count"],
        "production_release": result["production_release"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
