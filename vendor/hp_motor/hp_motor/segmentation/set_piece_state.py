#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Any, Optional

SP_IDS = {
    "corner": "SP_CORNER",
    "korner": "SP_CORNER",
    "free_kick": "SP_FREEKICK",
    "freekick": "SP_FREEKICK",
    "serbest": "SP_FREEKICK",
    "throw_in": "SP_THROWIN",
    "throwin": "SP_THROWIN",
    "tac": "SP_THROWIN",
    "kick_off": "SP_KICKOFF",
    "kickoff": "SP_KICKOFF",
    "baslama": "SP_KICKOFF",
    "penalty": "SP_PENALTY",
    "penalti": "SP_PENALTY",
}

def _norm(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    x = str(s).strip().lower()
    x = (x.replace("ı","i").replace("ğ","g").replace("ü","u").replace("ş","s").replace("ö","o").replace("ç","c"))
    x = x.replace("-", "_").replace(" ", "_")
    return x or None

def _map_any(v: Any) -> Optional[str]:
    k = _norm(v)
    if not k:
        return None
    if k in SP_IDS:
        return SP_IDS[k]
    for key, sp in SP_IDS.items():
        if key in k:
            return sp
    return None

def tag_set_piece_state(df):
    """
    Adds/normalizes column: set_piece_state (string or null)
    Preferred: infer from event_type/type if explicit set-piece column absent.
    """
    # polars
    try:
        import polars as pl  # type: ignore
        if isinstance(df, pl.DataFrame):
            cols = set(df.columns)
            # prefer explicit columns if exist
            for src in ["set_piece_state", "set_piece", "restart_type", "event_restart"]:
                if src in cols:
                    return df.with_columns(
                        pl.col(src).cast(pl.Utf8).map_elements(_map_any, return_dtype=pl.Utf8).alias("set_piece_state")
                    )
            # else infer from event_type/type
            src = "event_type" if "event_type" in cols else ("type" if "type" in cols else None)
            if not src:
                return df.with_columns(pl.lit(None).cast(pl.Utf8).alias("set_piece_state"))
            return df.with_columns(
                pl.col(src).cast(pl.Utf8).map_elements(_map_any, return_dtype=pl.Utf8).alias("set_piece_state")
            )
    except Exception:
        pass

    # pandas
    try:
        import pandas as pd  # type: ignore
        if isinstance(df, pd.DataFrame):
            cols = set(df.columns)
            for src in ["set_piece_state", "set_piece", "restart_type", "event_restart"]:
                if src in cols:
                    df["set_piece_state"] = df[src].apply(_map_any)
                    return df
            src = "event_type" if "event_type" in cols else ("type" if "type" in cols else None)
            if not src:
                df["set_piece_state"] = None
                return df
            df["set_piece_state"] = df[src].apply(_map_any)
            return df
    except Exception:
        pass

    return df
