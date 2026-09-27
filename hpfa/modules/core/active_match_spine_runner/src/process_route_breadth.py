from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any


MODULE_ID = "visible_process_route_breadth_profile_v1"
CLAIM_CEILING = "MATCH_LOCAL_VISIBLE_ROUTE_BREADTH_PROFILE_CANDIDATE_ONLY"


def build_visible_process_route_breadth_profile(
    process_development_signatures: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize visible start→end route breadth from admitted process signatures.

    A route is eligible only when one visible start-zone candidate and one visible
    end-zone candidate are available. Counts describe match-local observed route
    breadth; they do not establish tactical flexibility, unpredictability, superiority,
    physical trajectory, line-break truth or coach intention.
    """
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in process_development_signatures or []:
        if not isinstance(row, dict):
            continue
        team_id = str(row.get("team_identity_candidate_id") or "").strip()
        family = str(row.get("process_family_candidate") or "").strip() or "UNKNOWN"
        if team_id:
            grouped[(team_id, family)].append(row)

    profiles: list[dict[str, Any]] = []
    for (team_id, family), rows in sorted(grouped.items()):
        route_counts: Counter[str] = Counter()
        ambiguous_n = 0
        for row in rows:
            starts = sorted({
                str(value).strip()
                for value in (row.get("process_start_zone_candidates") or [])
                if str(value).strip()
            })
            ends = sorted({
                str(value).strip()
                for value in (row.get("process_end_zone_candidates") or [])
                if str(value).strip()
            })
            if len(starts) != 1 or len(ends) != 1:
                ambiguous_n += 1
                continue
            route_counts[f"{starts[0]}->{ends[0]}"] += 1

        eligible_route_n = sum(route_counts.values())
        unique_route_n = len(route_counts)
        recurring_route_n = sum(count >= 2 for count in route_counts.values())
        singleton_route_n = sum(count == 1 for count in route_counts.values())
        top_route = None
        top_count = 0
        if route_counts:
            top_route, top_count = sorted(
                route_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )[0]

        profiles.append({
            "team_identity_candidate_id": team_id,
            "process_family_candidate": family,
            "eligible_process_n": len(rows),
            "eligible_unambiguous_route_process_n": eligible_route_n,
            "ambiguous_or_unresolved_route_process_n": ambiguous_n,
            "visible_route_candidate_counts": dict(sorted(route_counts.items())),
            "unique_visible_route_candidate_n": unique_route_n,
            "recurring_visible_route_candidate_n": recurring_route_n,
            "singleton_visible_route_candidate_n": singleton_route_n,
            "top_visible_route_candidate": top_route,
            "top_visible_route_process_n": top_count,
            "top_visible_route_share_candidate": (
                round(top_count / eligible_route_n, 6)
                if eligible_route_n
                else None
            ),
            "route_coverage_share_candidate": (
                round(eligible_route_n / len(rows), 6)
                if rows
                else None
            ),
            "denominator_basis": "MATCH_LOCAL_ADMITTED_PROCESS_SIGNATURES",
            "route_identity_basis": "SINGLE_VISIBLE_START_ZONE_TO_SINGLE_VISIBLE_END_ZONE",
            "route_is_physical_trajectory_truth": False,
            "route_is_line_break_truth": False,
            "route_breadth_is_tactical_flexibility_truth": False,
            "route_breadth_is_unpredictability_truth": False,
            "route_breadth_is_superiority_truth": False,
            "coach_intention_truth": False,
            "creates_independent_support": False,
            "claim_ceiling": CLAIM_CEILING,
        })

    return {
        "module_id": MODULE_ID,
        "status": "PASS" if profiles else "NOT_AVAILABLE",
        "binding_state": "VISIBLE_START_END_ROUTE_BREADTH_PROFILE",
        "profile_count": len(profiles),
        "profiles": profiles,
        "hard_block_hits": [],
        "review_hits": [],
        "claim_ceiling": CLAIM_CEILING,
        "route_is_physical_trajectory_truth": False,
        "route_is_line_break_truth": False,
        "route_breadth_is_tactical_flexibility_truth": False,
        "route_breadth_is_unpredictability_truth": False,
        "route_breadth_is_superiority_truth": False,
        "coach_intention_truth": False,
        "creates_independent_support": False,
    }
