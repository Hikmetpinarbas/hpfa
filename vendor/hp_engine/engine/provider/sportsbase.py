from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
import pandas as pd
import numpy as np

@dataclass
class ProviderMapResult:
    canonical_df: pd.DataFrame
    mapping_used: Dict[str, str]

def _pick(df: pd.DataFrame, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None

def to_canonical_events(df: pd.DataFrame) -> ProviderMapResult:
    """Map SportsBase-like event exports to HP canonical schema.
    Permissive mapping; missing fields become NaN (no silent row drops).
    """
    mapping_used: Dict[str, str] = {}

    col_match = _pick(df, ["match_id","MatchId","match","matchId"])
    col_team  = _pick(df, ["team_id","TeamId","team","teamId","team_name","Team"])
    col_player= _pick(df, ["player_id","PlayerId","player","playerId","player_name","Player"])
    col_type  = _pick(df, ["event_type","type","EventType","action","Action","event","tag"])
    col_ts_s  = _pick(df, ["timestamp_s","timestamp","time_s","sec","seconds","start_s","StartSecond","start"])
    col_period= _pick(df, ["period","half","Period","Half"])
    col_x     = _pick(df, ["x","pos_x","PosX","start_x","StartX","X","location_x"])
    col_y     = _pick(df, ["y","pos_y","PosY","start_y","StartY","Y","location_y"])
    col_xe    = _pick(df, ["x_end","end_x","EndX","to_x","dest_x","location_x_end"])
    col_ye    = _pick(df, ["y_end","end_y","EndY","to_y","dest_y","location_y_end"])
    col_out   = _pick(df, ["outcome","result","Outcome","success","is_success","successful"])

    def map_col(target, src):
        if src is not None:
            mapping_used[target] = src

    map_col("match_id", col_match)
    map_col("team_id", col_team)
    map_col("player_id", col_player)
    map_col("event_type", col_type)
    map_col("timestamp_s", col_ts_s)
    map_col("period", col_period)
    map_col("x", col_x)
    map_col("y", col_y)
    map_col("x_end", col_xe)
    map_col("y_end", col_ye)
    map_col("outcome", col_out)

    out_df = pd.DataFrame()
    for tgt, src in mapping_used.items():
        out_df[tgt] = df[src]

    for c in ["match_id","team_id","player_id","event_type","timestamp_s","period","x","y","x_end","y_end","outcome"]:
        if c not in out_df.columns:
            out_df[c] = np.nan

    def parse_ts(v):
        if pd.isna(v):
            return np.nan
        if isinstance(v, (int,float,np.integer,np.floating)):
            return float(v)
        s = str(v).strip()
        if s.isdigit():
            return float(s)
        parts = s.split(":")
        try:
            if len(parts)==2:
                m, sec = int(parts[0]), float(parts[1])
                return 60*m + sec
            if len(parts)==3:
                h, m, sec = int(parts[0]), int(parts[1]), float(parts[2])
                return 3600*h + 60*m + sec
        except:
            return np.nan
        return np.nan

    out_df["timestamp_s"] = out_df["timestamp_s"].apply(parse_ts)

    # If coordinates look like 0-100 scale, map to 105x68
    try:
        x_max = pd.to_numeric(out_df["x"], errors="coerce").dropna().max()
        y_max = pd.to_numeric(out_df["y"], errors="coerce").dropna().max()
    except Exception:
        x_max, y_max = np.nan, np.nan

    if pd.notna(x_max) and pd.notna(y_max) and x_max <= 100.5 and y_max <= 100.5:
        out_df["x"] = pd.to_numeric(out_df["x"], errors="coerce") * 105.0 / 100.0
        out_df["y"] = pd.to_numeric(out_df["y"], errors="coerce") * 68.0 / 100.0
        if out_df["x_end"].notna().any():
            out_df["x_end"] = pd.to_numeric(out_df["x_end"], errors="coerce") * 105.0 / 100.0
        if out_df["y_end"].notna().any():
            out_df["y_end"] = pd.to_numeric(out_df["y_end"], errors="coerce") * 68.0 / 100.0

    def norm_out(v):
        if pd.isna(v):
            return np.nan
        if isinstance(v, (int,float,np.integer,np.floating)):
            if v in (0,1):
                return bool(int(v))
            return np.nan
        s = str(v).strip().lower()
        if s in ("success","successful","true","1","yes","y","won"):
            return True
        if s in ("fail","failed","false","0","no","n","lost"):
            return False
        return np.nan

    out_df["outcome"] = out_df["outcome"].apply(norm_out)
    out_df["event_type"] = out_df["event_type"].astype(str).str.strip().str.lower()

    return ProviderMapResult(canonical_df=out_df, mapping_used=mapping_used)