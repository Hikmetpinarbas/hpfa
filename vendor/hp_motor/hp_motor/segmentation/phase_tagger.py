#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Any, Optional

from .set_piece_state import tag_set_piece_state

P1 = "P1_BUILDUP"
P2 = "P2_PROGRESSION"
P3 = "P3_FINALIZATION"
P4 = "P4_NEG_TRANSITION"
P5 = "P5_ORG_DEFENSE"
P6 = "P6_POS_TRANSITION"

# Heuristic dictionaries (lite core)
FINAL_ACTIONS = {"shot", "goal", "miss", "save"}
DEF_ACTIONS = {"tackle", "interception", "clearance", "block", "pressure", "foul", "duel"}

TURNOVER_OUTCOMES = {"incomplete", "fail", "failed", "lost", "turnover", "out"}
SUCCESS_OUTCOMES = {"complete", "success", "won"}

def _norm(s: Any) -> str:
    if s is None:
        return ""
    x = str(s).strip().lower()
    x = (x.replace("ı","i").replace("ğ","g").replace("ü","u").replace("ş","s").replace("ö","o").replace("ç","c"))
    x = x.replace("-", "_").replace(" ", "_")
    return x

def _to_float(v: Any) -> Optional[float]:
    try:
        if v is None:
            return None
        return float(v)
    except Exception:
        return None

def _norm_x(x: Optional[float]) -> Optional[float]:
    """
    Normalize to 0-100 if likely 0-120/0-105 scale.
    """
    if x is None:
        return None
    if x > 105:
        return (x / 120.0) * 100.0
    return x

def _zone_phase(x: Optional[float]) -> Optional[str]:
    if x is None:
        return None
    x = _norm_x(x)
    if x is None:
        return None
    if x <= 35:
        return P1
    if x <= 70:
        return P2
    return P3

def _event_phase(event_type: str, outcome: str) -> Optional[str]:
    et = _norm(event_type)
    oc = _norm(outcome)

    # set-piece: keep phase based on action/zone; set_piece_state handled separately

    # explicit final actions
    if any(k in et for k in FINAL_ACTIONS):
        return P3

    # defensive actions
    if any(k in et for k in DEF_ACTIONS):
        return P5

    # turnover via outcome
    if any(k in oc for k in TURNOVER_OUTCOMES):
        # if event is pass/ball_loss etc: treat as neg transition trigger
        if "pass" in et or "carry" in et or "dribble" in et or "touch" in et or "loss" in et:
            return P4

    return None

def tag_phases(df):
    """
    Adds/normalizes:
      - set_piece_state (SP_*)
      - phase_id (P1..P6)
    Deterministic rules for fixture schema:
      uses: minute, second, possession_id, team_id, event_type, outcome, start_x/end_x
    """
    df = tag_set_piece_state(df)

    # polars path (optional) – if polars not installed, skip
    try:
        import polars as pl  # type: ignore
        if isinstance(df, pl.DataFrame):
            cols = set(df.columns)

            # normalize existing
            if "phase_id" in cols:
                return df

            # require minimal columns
            required = {"event_type", "minute", "second"}
            if not required.issubset(cols):
                return df.with_columns(pl.lit(None).cast(pl.Utf8).alias("phase_id"))

            # build time in seconds
            df = df.with_columns((pl.col("minute") * 60 + pl.col("second")).alias("_t"))

            # possession change (if available)
            if "possession_id" in cols and "team_id" in cols:
                df = df.with_columns([
                    pl.col("possession_id").shift(1).alias("_prev_poss"),
                    pl.col("team_id").shift(1).alias("_prev_team"),
                    pl.col("_t").shift(1).alias("_prev_t"),
                ])
                df = df.with_columns(
                    ((pl.col("possession_id") != pl.col("_prev_poss")) & pl.col("_prev_poss").is_not_null()).alias("_poss_changed")
                )
                df = df.with_columns(
                    (pl.col("_t") - pl.col("_prev_t")).fill_null(9999).alias("_dt")
                )
            else:
                df = df.with_columns([
                    pl.lit(False).alias("_poss_changed"),
                    pl.lit(9999).alias("_dt")
                ])

            # base phase inference
            def infer_row(r):
                et = r.get("event_type")
                oc = r.get("outcome")
                sx = r.get("start_x")
                ex = r.get("end_x")
                poss_changed = bool(r.get("_poss_changed"))
                dt = r.get("_dt") or 9999

                # 1) quick event-based
                ep = _event_phase(et, oc)

                # 2) possession change => positive transition window
                if poss_changed and dt <= 8:
                    return P6

                # 3) neg transition trigger
                if ep == P4:
                    return P4

                # 4) defensive action
                if ep == P5:
                    return P5

                # 5) final action
                if ep == P3:
                    return P3

                # 6) zone-based
                x = _to_float(ex) if ex is not None else _to_float(sx)
                return _zone_phase(x)

            df = df.with_columns(
                pl.struct(df.columns).map_elements(infer_row, return_dtype=pl.Utf8).alias("phase_id")
            )

            # cleanup helper cols (keep optional if you want)
            df = df.drop([c for c in ["_t","_prev_poss","_prev_team","_prev_t","_poss_changed","_dt"] if c in df.columns])
            return df
    except Exception:
        pass

    # pandas fallback (your current environment supports this)
    try:
        import pandas as pd  # type: ignore
        if isinstance(df, pd.DataFrame):
            if "phase_id" in df.columns:
                return df

            # minimal columns check
            if not {"event_type", "minute", "second"}.issubset(set(df.columns)):
                df["phase_id"] = None
                return df

            df["_t"] = df["minute"].astype(float) * 60.0 + df["second"].astype(float)

            if "possession_id" in df.columns and "team_id" in df.columns:
                df["_prev_poss"] = df["possession_id"].shift(1)
                df["_prev_t"] = df["_t"].shift(1)
                df["_poss_changed"] = (df["possession_id"] != df["_prev_poss"]) & df["_prev_poss"].notna()
                df["_dt"] = (df["_t"] - df["_prev_t"]).fillna(9999)
            else:
                df["_poss_changed"] = False
                df["_dt"] = 9999

            def infer(r):
                et = r.get("event_type", None)
                oc = r.get("outcome", None)
                sx = r.get("start_x", None)
                ex = r.get("end_x", None)
                poss_changed = bool(r.get("_poss_changed", False))
                dt = r.get("_dt", 9999)

                ep = _event_phase(et, oc)

                if poss_changed and dt <= 8:
                    return P6
                if ep == P4:
                    return P4
                if ep == P5:
                    return P5
                if ep == P3:
                    return P3

                x = _to_float(ex) if ex is not None else _to_float(sx)
                return _zone_phase(x)

            df["phase_id"] = df.apply(infer, axis=1)

            # cleanup
            for c in ["_t","_prev_poss","_prev_t","_poss_changed","_dt"]:
                if c in df.columns:
                    del df[c]
            return df
    except Exception:
        pass

    return df
