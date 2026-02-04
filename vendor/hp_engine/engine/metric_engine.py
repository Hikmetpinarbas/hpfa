from __future__ import annotations

from typing import Any, Dict, List, Optional


class MetricEngine:
    """
    HP Engine v3 - Minimal Metric Engine (Core Set v1)

    Important:
    - master_orchestrator calls: compute_fn(events, team="team")
    - So every compute_* MUST accept (events, team="team", **kwargs)
    - We do NOT silently drop data. If missing -> return None and let PopperGate/SOT handle status.
    """

    # -----------------------------
    # Helpers
    # -----------------------------
    def _team_of(self, e: Dict[str, Any]) -> Optional[str]:
        t = e.get("team")
        if t is None:
            return None
        return str(t).strip().lower()

    def _type_of(self, e: Dict[str, Any]) -> Optional[str]:
        t = e.get("type")
        if t is None:
            return None
        return str(t).strip().lower()

    def _x_of(self, e: Dict[str, Any]) -> Optional[float]:
        x = e.get("x")
        if x is None:
            return None
        try:
            return float(x)
        except Exception:
            return None

    # -----------------------------
    # Metrics
    # -----------------------------
    def compute_ppda(self, events: List[Dict[str, Any]], team: str = "team", **kwargs) -> Optional[float]:
        """
        PPDA (proxy, event-only):
        opponent_passes / team_defensive_actions

        Notes:
        - This is a degraded/approx PPDA unless your provider has explicit zone + defensive third definitions.
        - We keep it consistent with current event schema: team labels: "team" and "opponent".
        """
        team = str(team).strip().lower()
        opp = "opponent" if team == "team" else "team"

        opp_passes = 0
        def_actions = 0

        for e in events:
            eteam = self._team_of(e)
            etype = self._type_of(e)

            if eteam == opp and etype == "pass":
                opp_passes += 1

            if eteam == team and etype in ("tackle", "interception", "block", "challenge", "foul"):
                def_actions += 1

        if def_actions <= 0:
            return None

        return round(opp_passes / def_actions, 2)

    def compute_field_tilt(self, events: List[Dict[str, Any]], team: str = "team", **kwargs) -> Optional[float]:
        """
        Field Tilt (proxy, event-only):
        team_final_third_passes / (team_final_third_passes + opponent_final_third_passes)

        Assumption:
        - Canonical pitch is 105x68.
        - "Final third" proxy: x >= 70 (i.e., 2/3 of 105)
        - Works if x is already in meters (SOT should handle transform); if not, still a consistent proxy.
        """
        team = str(team).strip().lower()
        opp = "opponent" if team == "team" else "team"

        team_p = 0
        opp_p = 0

        for e in events:
            eteam = self._team_of(e)
            etype = self._type_of(e)

            if etype != "pass":
                continue

            x = self._x_of(e)
            if x is None:
                continue

            # final third threshold (proxy)
            if x >= 70.0:
                if eteam == team:
                    team_p += 1
                elif eteam == opp:
                    opp_p += 1

        denom = team_p + opp_p
        if denom <= 0:
            return None

        return round(team_p / denom, 4)

    def compute_pressing_intensity(self, events: List[Dict[str, Any]], team: str = "team", **kwargs) -> Optional[float]:
        """
        Pressing Intensity (proxy):
        team_defensive_actions_per_minute

        If you later add timestamps with match clock in seconds, we can compute per 10-min windows etc.
        For now:
        - Use count of defensive actions normalized by approximate match minutes if present.
        - If no time info exists: return raw count (still explicit, not silent).
        """
        team = str(team).strip().lower()

        def_actions = 0
        min_time = None
        max_time = None

        for e in events:
            eteam = self._team_of(e)
            etype = self._type_of(e)
            if eteam == team and etype in ("tackle", "interception", "block", "challenge", "foul", "pressure"):
                def_actions += 1

            # optional time support
            t = e.get("t")
            if t is not None:
                try:
                    tv = float(t)
                    if min_time is None or tv < min_time:
                        min_time = tv
                    if max_time is None or tv > max_time:
                        max_time = tv
                except Exception:
                    pass

        # If we have time range in seconds, normalize per minute
        if min_time is not None and max_time is not None and max_time > min_time:
            minutes = (max_time - min_time) / 60.0
            if minutes > 0:
                return round(def_actions / minutes, 3)

        # No timebase: return count as explicit proxy
        return float(def_actions)
