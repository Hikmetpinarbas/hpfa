from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional


def _num(value: Any) -> Optional[float]:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except Exception:
        return None


def period_scope(row: Dict[str, Any]) -> str:
    half = str(row.get("half") or row.get("period") or "").strip()
    start = _num(row.get("start") or row.get("time_seconds"))

    if half == "1":
        if start is not None and start > 45 * 60:
            return "first_half_stoppage"
        return "first_half"

    if half == "2":
        if start is not None and start > 90 * 60:
            return "second_half_stoppage"
        return "second_half"

    return "unknown_period"


def attach_context(
    rows: Iterable[Dict[str, Any]],
    *,
    match_id: str = "ACTIVE_MATCH",
    coordinate_scale: str = "105x68",
    home_team: str = "",
    away_team: str = "",
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []

    current_score_home = 0
    current_score_away = 0
    red_cards_home = 0
    red_cards_away = 0
    yellow_cards_home = 0
    yellow_cards_away = 0
    substitutions_home = 0
    substitutions_away = 0

    for idx, row in enumerate(rows):
        action = str(row.get("action") or row.get("event_type") or row.get("code") or "").lower()
        team = str(row.get("team") or row.get("team_id") or "")

        is_home = bool(home_team and home_team in team)
        is_away = bool(away_team and away_team in team)

        if "goal" in action and "goal kick" not in action and "own goal" not in action:
            if is_home:
                current_score_home += 1
            elif is_away:
                current_score_away += 1

        if "red card" in action:
            if is_home:
                red_cards_home += 1
            elif is_away:
                red_cards_away += 1

        if "yellow card" in action:
            if is_home:
                yellow_cards_home += 1
            elif is_away:
                yellow_cards_away += 1

        if "substitution" in action or "substitute" in action:
            if is_home:
                substitutions_home += 1
            elif is_away:
                substitutions_away += 1

        enriched = dict(row)
        enriched.update({
            "match_id": match_id,
            "surface_row_id": row.get("ID") or row.get("id") or idx + 1,
            "surface_row_index": idx,
            "coordinate_scale": coordinate_scale,
            "period_scope": period_scope(row),
            "score_state": f"{current_score_home}-{current_score_away}",
            "goal_state": {
                "home_goals": current_score_home,
                "away_goals": current_score_away,
            },
            "yellow_card_state": {
                "home_yellow_cards": yellow_cards_home,
                "away_yellow_cards": yellow_cards_away,
            },
            "red_card_state": {
                "home_red_cards": red_cards_home,
                "away_red_cards": red_cards_away,
            },
            "numerical_state": f"{11 - red_cards_home}v{11 - red_cards_away}",
            "substitution_state": {
                "home_substitutions": substitutions_home,
                "away_substitutions": substitutions_away,
            },
            "home_away_state": "home" if is_home else ("away" if is_away else "unknown"),
            "claim_safety": "EVIDENCE_ONLY",
        })
        out.append(enriched)

    return out
