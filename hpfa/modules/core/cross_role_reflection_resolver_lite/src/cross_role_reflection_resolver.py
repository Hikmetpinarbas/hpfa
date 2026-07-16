from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from typing import Any

MODULE_ID = "cross_role_reflection_resolver_lite_v1"

REFLECTION_ROUTES = {
    "TEAM_ACTION_REFLECTION_SURFACE",
    "GOALKEEPER_OPPONENT_ACTION_REFLECTION",
}

FAMILY_PREFIXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("RESTART", ("goal_kick", "goal_kicks", "corner", "corners", "throw_in", "throw_ins", "free_kick", "kick_off")),
    ("PASS", ("pass", "passes", "cross", "crosses", "assist")),
    ("SHOT", ("shot", "shots", "woodwork")),
    ("RECOVERY", ("ball_recovery", "ball_recoveries", "loose_ball_recovery", "loose_ball_recoveries")),
    ("INTERCEPTION", ("interception", "interceptions")),
    ("DUEL", ("tackle", "tackles", "challenge", "challenges", "aerial_challenge", "aerial_challenges", "duel", "duels")),
    ("CARRY_DRIBBLE", ("carry", "carries", "dribble", "dribbles", "take_on", "take_ons")),
    ("BALL_LOSS", ("lost_ball", "lost_balls", "ball_loss", "ball_losses", "dispossessed", "miscontrol")),
    ("FOUL", ("foul", "fouls", "handball")),
    ("SAVE_GK_ACTION", ("save", "saves", "claim", "claims", "punch", "punches", "sweeping_action")),
)

NON_EVENT_PREFIXES = (
    "involvement_in_", "participation", "attack_with_shot", "positional_attack",
    "counterattack", "counter_attack", "successful_pressure", "high_threat_loss",
    "mistake_leading_to", "chance_creation", "supersave", "super_save",
)


def _clean(value: Any) -> str:
    return " ".join("" if value is None else str(value).split()).strip()


def _number(value: Any) -> str:
    text = _clean(value)
    if not text:
        return ""
    try:
        return f"{float(text):.6f}"
    except ValueError:
        return text


def _starts(label: str, prefixes: tuple[str, ...]) -> bool:
    return any(label == prefix or label.startswith(prefix + "_") for prefix in prefixes)


def _family_hints(labels: list[str], route: str) -> list[str]:
    hints: set[str] = set()
    for label in labels:
        if not label or _starts(label, NON_EVENT_PREFIXES):
            continue
        if route == "GOALKEEPER_OPPONENT_ACTION_REFLECTION" and _starts(label, ("shot", "shots")):
            hints.add("SHOT")
            continue
        for family, prefixes in FAMILY_PREFIXES:
            if _starts(label, prefixes):
                hints.add(family)
                break
    return sorted(hints)


def _spatiotemporal_signature(action_group_key: list[Any], family: str) -> tuple[str, ...]:
    return (
        _clean(action_group_key[0]), _clean(action_group_key[4]), _clean(action_group_key[5]),
        _number(action_group_key[6]), _number(action_group_key[7]), _number(action_group_key[8]),
        _number(action_group_key[9]), family,
    )


def _stable_id(prefix: str, values: tuple[str, ...]) -> str:
    return prefix + hashlib.sha256("|".join(values).encode("utf-8")).hexdigest()[:24]


def resolve_cross_role_reflections(classifier_payload: dict[str, Any]) -> dict[str, Any]:
    labels_by_id = {
        item.get("event_label_candidate_id"): item
        for item in classifier_payload.get("event_label_candidates", [])
        if item.get("event_label_candidate_id")
    }
    primary_index: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for candidate in classifier_payload.get("base_event_surface_candidates", []):
        key = candidate.get("action_group_key") or []
        family = _clean(candidate.get("base_event_family"))
        route = _clean(candidate.get("source_semantic_route"))
        if len(key) != 10 or not family or route != "PLAYER_PRIMARY_ACTION_SURFACE":
            continue
        primary_index[_spatiotemporal_signature(key, family)].append(candidate["base_event_candidate_id"])

    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []
    route_counts: Counter[str] = Counter()
    for relation in classifier_payload.get("cross_role_reflection_relations", []):
        key = relation.get("action_group_key") or []
        route = _clean(relation.get("source_semantic_route"))
        if route not in REFLECTION_ROUTES or len(key) != 10:
            unresolved.append({**relation, "resolution_status": "BLOCKED_INVALID_REFLECTION_CONTRACT"})
            continue
        labels = [_clean(labels_by_id.get(label_id, {}).get("normalized_label")).lower() for label_id in relation.get("event_label_candidate_ids", [])]
        families = _family_hints(labels, route)
        matches: set[str] = set()
        for family in families:
            matches.update(primary_index.get(_spatiotemporal_signature(key, family), []))
        route_counts[route] += 1
        base = {**relation, "reflected_family_hints": families, "candidate_primary_event_ids": sorted(matches)}
        if len(matches) == 1:
            target = next(iter(matches))
            resolved.append({
                **base,
                "resolved_relation_id": _stable_id("crl_", (relation["reflection_relation_id"], target)),
                "linked_primary_event_candidate_id": target,
                "resolution_status": "RESOLVED_EXACT_SPATIOTEMPORAL_FAMILY_LINK",
                "canonical_admission_status": "BLOCKED_CANONICAL_IDENTITY_GATE",
            })
        elif len(matches) > 1:
            ambiguous.append({**base, "resolution_status": "REVIEW_REQUIRED_MULTIPLE_PRIMARY_MATCHES"})
        else:
            unresolved.append({**base, "resolution_status": "UNRESOLVED_NO_EXACT_PRIMARY_MATCH"})

    decision_state = "PASS_EXACT_REFLECTION_LINKS_FAIL_CLOSED"
    if ambiguous:
        decision_state = "REVIEW_REQUIRED_AMBIGUOUS_REFLECTION_LINKS"
    elif unresolved:
        decision_state = "REVIEW_REQUIRED_UNRESOLVED_REFLECTION_LINKS"
    return {
        "module_id": MODULE_ID,
        "runtime_code_head_sha": classifier_payload.get("runtime_code_head_sha"),
        "decision_state": decision_state,
        "input_reflection_relation_count": len(classifier_payload.get("cross_role_reflection_relations", [])),
        "resolved_reflection_links": resolved,
        "resolved_reflection_link_count": len(resolved),
        "ambiguous_reflection_links": ambiguous,
        "ambiguous_reflection_link_count": len(ambiguous),
        "unresolved_reflection_links": unresolved,
        "unresolved_reflection_link_count": len(unresolved),
        "reflection_route_counts": dict(sorted(route_counts.items())),
        "link_policy": "EXACT_MATCH_PERIOD_TIME_LOCATION_TEAM_AND_FAMILY_ONLY",
        "identity_bound_event_count": 0,
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
        "technical_limits": [
            "A resolved link joins a reflection surface to a provisional primary surface candidate only.",
            "No nearest-neighbour, temporal tolerance, actor inference, or opponent inference is permitted in Lite V1.",
            "Ambiguous and unmatched reflections remain fail-closed.",
        ],
    }
