#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
from pathlib import Path
import pandas as pd
import numpy as np

PITCH_L = 105.0
PITCH_W = 68.0

SRC = Path("data/raw/city_gs.csv")
OUT_DIR = Path("artifacts/city_gs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def _norm_tr(s: str) -> str:
    if s is None:
        return ""
    x = str(s).strip().lower()
    x = (x.replace("ı","i").replace("ğ","g").replace("ü","u").replace("ş","s").replace("ö","o").replace("ç","c"))
    x = x.replace("-", "_").replace(" ", "_")
    return x

def _guess_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = {_norm_tr(c): c for c in df.columns}
    for cand in candidates:
        k = _norm_tr(cand)
        if k in cols:
            return cols[k]
    # “contains” heuristics
    for cand in candidates:
        k = _norm_tr(cand)
        for nk, orig in cols.items():
            if k and k in nk:
                return orig
    return None

def _scale_xy(v: float, max_target: float) -> float:
    # 0-1 -> meters, 0-100 -> meters, already meters -> keep
    if pd.isna(v):
        return np.nan
    try:
        x = float(v)
    except Exception:
        return np.nan
    if 0.0 <= x <= 1.0:
        return x * max_target
    if 0.0 <= x <= 100.0:
        return x * max_target / 100.0
    return x

def main():
    if not SRC.exists():
        raise SystemExit(f"missing: {SRC} (kopyalama adımını kontrol et)")

    df = pd.read_csv(SRC)

    # ---- map core columns (best-effort) ----
    c_min = _guess_col(df, ["minute", "min"])
    c_sec = _guess_col(df, ["second", "sec"])
    c_team = _guess_col(df, ["team", "team_id", "teamname", "team_name"])
    c_type = _guess_col(df, ["event_type", "type", "action", "event"])
    c_out  = _guess_col(df, ["outcome", "result"])
    c_poss = _guess_col(df, ["possession_id", "possession", "poss_id"])

    # xy naming varies
    c_x  = _guess_col(df, ["x", "start_x", "pos_x"])
    c_y  = _guess_col(df, ["y", "start_y", "pos_y"])
    c_ex = _guess_col(df, ["end_x", "to_x", "x_end", "endpos_x"])
    c_ey = _guess_col(df, ["end_y", "to_y", "y_end", "endpos_y"])

    # enforce minimal time columns
    if c_min is None:
        raise SystemExit("minute column not found. (probe çıktısını gönder; kolon adını map ederim)")
    if c_sec is None:
        df["_second_tmp"] = 0
        c_sec = "_second_tmp"

    out = pd.DataFrame()
    out["minute"] = pd.to_numeric(df[c_min], errors="coerce").fillna(0).astype(int)
    out["second"] = pd.to_numeric(df[c_sec], errors="coerce").fillna(0).astype(int)
    out["t_sec"] = out["minute"] * 60 + out["second"]

    out["team_id"] = df[c_team] if c_team else None
    out["event_type"] = df[c_type] if c_type else None
    out["outcome"] = df[c_out] if c_out else None
    out["possession_id"] = df[c_poss] if c_poss else None

    # coords -> 105x68
    if c_x:  out["start_x"] = df[c_x].apply(lambda v: _scale_xy(v, PITCH_L))
    else:    out["start_x"] = np.nan
    if c_y:  out["start_y"] = df[c_y].apply(lambda v: _scale_xy(v, PITCH_W))
    else:    out["start_y"] = np.nan
    if c_ex: out["end_x"]   = df[c_ex].apply(lambda v: _scale_xy(v, PITCH_L))
    else:    out["end_x"]   = np.nan
    if c_ey: out["end_y"]   = df[c_ey].apply(lambda v: _scale_xy(v, PITCH_W))
    else:    out["end_y"]   = np.nan

    # ---- phase tagging (your module) ----
    try:
        from hp_motor.segmentation.phase_tagger import tag_phases
        out2 = tag_phases(out.copy())
        out = out2
    except Exception as e:
        print("WARN: phase_tagger not applied:", e)

    # save
    out_path = OUT_DIR / "city_gs_events_tagged.csv"
    out.to_csv(out_path, index=False)
    print("WROTE:", out_path, "rows=", len(out), "cols=", len(out.columns))

    # ---- quick momentum proxy (event intensity, 1-min bins) ----
    # NOTE: real i12 momentum is proprietary; we approximate with weighted actions
    et = out["event_type"].astype(str).str.lower()
    w = np.zeros(len(out), dtype=float)
    w += et.str.contains("shot|goal").astype(float) * 3.0
    w += et.str.contains("cross").astype(float) * 1.2
    w += et.str.contains("dribble|carry").astype(float) * 0.8
    w += et.str.contains("pass").astype(float) * 0.2
    w += et.str.contains("tackle|interception|clearance|block").astype(float) * 0.7

    out["_w"] = w
    out["_minbin"] = (out["t_sec"] // 60).astype(int)

    # if team_id exists, compute both; else total
    if "team_id" in out.columns and out["team_id"].notna().any():
        g = out.groupby(["_minbin","team_id"], dropna=False)["_w"].sum().reset_index()
        pivot = g.pivot(index="_minbin", columns="team_id", values="_w").fillna(0.0)
        mom = pivot
    else:
        mom = out.groupby("_minbin")["_w"].sum().to_frame("total")

    mom_path = OUT_DIR / "city_gs_momentum_proxy.csv"
    mom.to_csv(mom_path)
    print("WROTE:", mom_path)

    # plot (matplotlib only)
    try:
        import matplotlib.pyplot as plt
        fig_path = OUT_DIR / "city_gs_momentum_proxy.png"
        plt.figure()
        if mom.shape[1] == 1:
            plt.plot(mom.index, mom.iloc[:,0])
        else:
            for col in mom.columns:
                plt.plot(mom.index, mom[col], label=str(col))
            plt.legend()
        plt.xlabel("minute")
        plt.ylabel("momentum_proxy")
        plt.title("City–GS momentum proxy (weighted event intensity)")
        plt.tight_layout()
        plt.savefig(fig_path, dpi=160)
        plt.close()
        print("WROTE:", fig_path)
    except Exception as e:
        print("WARN: plot skipped:", e)

if __name__ == "__main__":
    main()
