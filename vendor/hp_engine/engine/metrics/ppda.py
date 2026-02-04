from __future__ import annotations
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np

DEF_ACTION_TYPES_DEFAULT = {"tackle","interception","ball_recovery","challenge_won","foul_won","pressure","block"}

def _minute(ts_s: float) -> float:
    return ts_s / 60.0

def _bin_index(minute: float, bins):
    for i in range(len(bins)-1):
        if bins[i] <= minute < bins[i+1]:
            return f"{bins[i]}-{bins[i+1]}"
    return f"{bins[-2]}-{bins[-1]}+"

def calc_ppda_v1(events: pd.DataFrame, spec: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    bins = spec.get("temporal", {}).get("bins_minutes", [0,15,30,45,60,75,90,120])
    zone_x = 0.60 * 105.0

    df = events.copy()
    df["x"] = pd.to_numeric(df["x"], errors="coerce")
    df["timestamp_s"] = pd.to_numeric(df["timestamp_s"], errors="coerce")

    in_zone = df["x"] >= zone_x
    is_pass = df["event_type"].str.contains("pass", na=False)
    pass_in_zone = df[is_pass & in_zone]

    def_types = set(DEF_ACTION_TYPES_DEFAULT)
    present_types = set(df["event_type"].dropna().unique().tolist())
    coverage = len(def_types.intersection(present_types)) / max(1, len(def_types))
    status = "FULL" if coverage >= 0.40 else "DEGRADED"

    is_def = df["event_type"].isin(def_types)
    def_in_zone = df[is_def & in_zone]

    teams = sorted([t for t in df["team_id"].dropna().unique().tolist()])
    out = {"match": {}, "bins": {}}

    df_min = df["timestamp_s"].apply(lambda x: _minute(x) if pd.notna(x) else np.nan)
    df["_bin"] = df_min.apply(lambda m: _bin_index(m, bins) if pd.notna(m) else "NA")

    for team in teams:
        opp_passes = pass_in_zone[pass_in_zone["team_id"] != team]
        team_def = def_in_zone[def_in_zone["team_id"] == team]
        opp_n = int(len(opp_passes))
        def_n = int(len(team_def))
        ppda = (opp_n / def_n) if def_n > 0 else float("inf")
        out["match"][team] = {"ppda": ppda, "opp_passes_in_zone": opp_n, "def_actions_in_zone": def_n}

    for b in sorted(df["_bin"].dropna().unique().tolist()):
        if b == "NA":
            continue
        out["bins"][b] = {}
        for team in teams:
            opp_passes_b = pass_in_zone[(pass_in_zone["_bin"]==b) & (pass_in_zone["team_id"] != team)]
            team_def_b = def_in_zone[(def_in_zone["_bin"]==b) & (def_in_zone["team_id"] == team)]
            opp_n = int(len(opp_passes_b))
            def_n = int(len(team_def_b))
            ppda = (opp_n / def_n) if def_n > 0 else float("inf")
            out["bins"][b][team] = {"ppda": ppda, "opp_passes_in_zone": opp_n, "def_actions_in_zone": def_n}

    meta = {
        "status": status,
        "zone_definition": f"x >= {zone_x:.1f}m (opponent 60% zone)",
        "def_action_types_used": sorted(list(def_types)),
        "def_type_coverage_ratio": float(coverage),
        "notes": ["Event-only PPDA. Tracking-based pressure models not used."]
    }
    return out, meta