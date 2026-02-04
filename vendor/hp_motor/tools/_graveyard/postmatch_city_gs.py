#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations
import math
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

PITCH_L = 105.0
PITCH_W = 68.0

DATA = Path("data/raw/city_gs.csv")
OUTDIR = Path("artifacts/city_gs")
OUTDIR.mkdir(parents=True, exist_ok=True)

# --- Karun Singh xT grid (16x12) - widely used public grid values
# Source pattern: open implementations used across community.
XT = np.array([
[0.000,0.000,0.000,0.000,0.000,0.000,0.000,0.000,0.000,0.000,0.000,0.000],
[0.000,0.000,0.000,0.001,0.001,0.001,0.001,0.001,0.001,0.000,0.000,0.000],
[0.000,0.000,0.001,0.002,0.003,0.003,0.003,0.003,0.002,0.001,0.000,0.000],
[0.000,0.001,0.002,0.004,0.006,0.007,0.007,0.006,0.004,0.002,0.001,0.000],
[0.001,0.002,0.004,0.007,0.011,0.013,0.013,0.011,0.007,0.004,0.002,0.001],
[0.002,0.004,0.007,0.012,0.018,0.022,0.022,0.018,0.012,0.007,0.004,0.002],
[0.004,0.007,0.012,0.019,0.028,0.034,0.034,0.028,0.019,0.012,0.007,0.004],
[0.007,0.012,0.019,0.029,0.042,0.051,0.051,0.042,0.029,0.019,0.012,0.007],
[0.012,0.019,0.029,0.043,0.060,0.072,0.072,0.060,0.043,0.029,0.019,0.012],
[0.019,0.029,0.043,0.061,0.082,0.098,0.098,0.082,0.061,0.043,0.029,0.019],
[0.029,0.043,0.061,0.083,0.110,0.130,0.130,0.110,0.083,0.061,0.043,0.029],
[0.043,0.061,0.083,0.111,0.145,0.170,0.170,0.145,0.111,0.083,0.061,0.043],
[0.061,0.083,0.111,0.146,0.190,0.225,0.225,0.190,0.146,0.111,0.083,0.061],
[0.083,0.111,0.146,0.191,0.250,0.300,0.300,0.250,0.191,0.146,0.111,0.083],
[0.111,0.146,0.191,0.251,0.330,0.400,0.400,0.330,0.251,0.191,0.146,0.111],
[0.146,0.191,0.251,0.331,0.450,0.600,0.600,0.450,0.331,0.251,0.191,0.146],
])

def read_events(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Missing: {path.resolve()}")
    df = pd.read_csv(path, sep=";")
    # expected cols: ID,start,end,code,team,action,half,pos_x,pos_y
    # normalize numeric
    for c in ["start","end","pos_x","pos_y"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["team"] = df["team"].astype(str)
    df["code"] = df["code"].astype(str)
    df["action"] = df["action"].astype(str)
    df["half"] = pd.to_numeric(df["half"], errors="coerce").fillna(1).astype(int)
    return df

def to_pitch_xy(x100: float, y100: float) -> tuple[float,float]:
    # input likely 0-100; keep if already in meters-ish
    x = (x100/100.0)*PITCH_L if x100 <= 105 else x100
    y = (y100/100.0)*PITCH_W if y100 <= 100 else y100
    return float(x), float(y)

def box_flag(x: float, y: float) -> bool:
    # penalty box approx: last 16.5m => x >= 88.5 if attacking to the right
    # but we don't know direction per team; use absolute "opponent box" approximation:
    # treat box as either end: x<=16.5 OR x>=88.5
    return (x <= 16.5 or x >= (PITCH_L-16.5)) and (y >= (PITCH_W/2 - 20.16) and y <= (PITCH_W/2 + 20.16))

def final_third_flag(x: float) -> bool:
    return x >= (PITCH_L*(2/3)) or x <= (PITCH_L*(1/3))

def xt_value(x: float, y: float) -> float:
    # map to 16x12
    gx = min(15, max(0, int((x / PITCH_L) * 16)))
    gy = min(11, max(0, int((y / PITCH_W) * 12)))
    return float(XT[gx, gy])

def pass_like(code: str, action: str) -> bool:
    c = code.upper()
    a = action.lower()
    return ("PASS" in c) or ("pas" in a) or ("cross" in a)

def is_success(code: str) -> bool:
    c = code.upper()
    if any(k in c for k in ["_OK", "SUCCESS", "WON"]):
        return True
    if any(k in c for k in ["_FAIL", "FAILED", "INCOMPLETE", "LOST"]):
        return False
    return False  # unknown treated as not-success for strict metrics

def is_turnover(code: str) -> bool:
    c = code.upper()
    return any(k in c for k in ["_FAIL","FAILED","LOST","TURNOVER"])

def is_shot(code: str, action: str) -> bool:
    c = code.upper()
    a = action.lower()
    return ("SHOT" in c) or ("şut" in a) or ("shot" in a) or ("goal" in c)

def build_possessions(df: pd.DataFrame) -> pd.DataFrame:
    # heuristic possession id: new when team changes OR turnover OR shot OR time gap big
    df = df.sort_values(["half","start","end","ID"]).reset_index(drop=True)
    df["dt"] = (df["start"] - df["end"].shift(1)).fillna(0)
    new_poss = []
    pid = 0
    prev_team = None
    for i, r in df.iterrows():
        team = r["team"]
        code = r["code"]
        a = r["action"]
        dt = float(r["dt"]) if pd.notna(r["dt"]) else 0.0
        start_new = False
        if prev_team is None:
            start_new = True
        elif team != prev_team:
            start_new = True
        elif dt > 8.0:
            start_new = True
        elif is_turnover(code):
            start_new = True
        elif is_shot(code, a):
            start_new = True
        if start_new:
            pid += 1
        new_poss.append(pid)
        prev_team = team
    df["possession_id"] = new_poss
    return df

def main():
    df = read_events(DATA)

    # coords
    xy = df.apply(lambda r: to_pitch_xy(r["pos_x"], r["pos_y"]), axis=1, result_type="expand")
    df["x"] = xy[0]; df["y"] = xy[1]

    # time
    df["t_sec"] = df["start"].fillna(0).astype(float)
    df["minute"] = (df["t_sec"] // 60).astype(int)

    # possessions
    df = build_possessions(df)

    # xT per action (simple: location delta not available; use start cell xT)
    df["xT"] = df.apply(lambda r: xt_value(r["x"], r["y"]), axis=1)

    # core aggregates
    teams = sorted(df["team"].unique().tolist())
    if len(teams) < 2:
        print("WARN: single-team in file; charts will still render.")
    teamA = teams[0]
    teamB = teams[1] if len(teams) > 1 else teams[0]

    # possession proxy: sum of (end-start) per possession per team (fallback: event counts)
    df["dur"] = (df["end"] - df["start"]).clip(lower=0).fillna(0)
    poss_time = df.groupby("team")["dur"].sum()
    if poss_time.sum() > 0:
        poss_pct = (poss_time / poss_time.sum() * 100).to_dict()
    else:
        cnt = df["team"].value_counts()
        poss_pct = (cnt / cnt.sum() * 100).to_dict()

    # field tilt: share of touches in attacking final third proxy (x>=70% length) among both teams
    # here we ignore direction; use "high territory" touches: x >= 70% OR x <= 30%
    high_terr = df[(df["x"] >= 0.70*PITCH_L) | (df["x"] <= 0.30*PITCH_L)]
    ft_counts = high_terr["team"].value_counts()
    ft_pct = (ft_counts / ft_counts.sum() * 100).to_dict() if ft_counts.sum() else {t:0.0 for t in teams}

    # long ball %: passes with estimated distance >= 30m not possible without end coords; approximate using code includes LONG
    # if no LONG flags, fallback: 0
    df["is_pass"] = df.apply(lambda r: pass_like(r["code"], r["action"]), axis=1)
    df["is_long"] = df["code"].str.upper().str.contains("LONG")
    long_pct = {}
    for t in teams:
        p = df[(df["team"]==t) & (df["is_pass"])]
        denom = len(p)
        long_pct[t] = float((p["is_long"].sum()/denom)*100) if denom else 0.0

    # pass tempo: passes per minute (ball-in-play proxy: halves duration)
    pass_tempo = {}
    for t in teams:
        p = df[(df["team"]==t) & (df["is_pass"])]
        minutes = max(1, int(df["t_sec"].max()//60))
        pass_tempo[t] = float(len(p)/minutes)

    # possessions to final third % and final third to box %
    df["in_final_third"] = df["x"].apply(lambda x: x >= 0.70*PITCH_L or x <= 0.30*PITCH_L)
    df["in_box"] = df.apply(lambda r: box_flag(r["x"], r["y"]), axis=1)

    poss_reach_ft = df.groupby(["team","possession_id"])["in_final_third"].max().reset_index()
    poss_reach_box = df.groupby(["team","possession_id"])["in_box"].max().reset_index()

    p_ft = poss_reach_ft.groupby("team")["in_final_third"].mean()*100
    p_box = poss_reach_box.groupby("team")["in_box"].mean()*100

    # xT total (simple sum)
    xt_sum = df.groupby("team")["xT"].sum()

    summary = {
        "teams": teams,
        "possession_pct": {k: float(v) for k,v in poss_pct.items()},
        "field_tilt_pct": {k: float(ft_pct.get(k,0.0)) for k in teams},
        "long_ball_pct": {k: float(long_pct.get(k,0.0)) for k in teams},
        "pass_tempo_per_min": {k: float(pass_tempo.get(k,0.0)) for k in teams},
        "possessions_to_final_third_pct": {k: float(p_ft.get(k,0.0)) for k in teams},
        "final_third_to_box_pct": {k: float(p_box.get(k,0.0)) for k in teams},
        "xT_total": {k: float(xt_sum.get(k,0.0)) for k in teams},
        "notes": [
            "Some metrics are heuristic because dataset lacks end_x/end_y and explicit possession ids.",
            "Direction (attacking left/right) unknown; final third + box metrics use symmetric pitch zones."
        ]
    }

    (OUTDIR/"summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    df.to_csv(OUTDIR/"events_enriched.csv", index=False)

    # --- Momentum: minute bins net xT difference
    m = df.groupby(["minute","team"])["xT"].sum().unstack(fill_value=0)
    for t in teams:
        if t not in m.columns:
            m[t] = 0.0
    m["net_"+teamA] = m[teamA] - m[teamB]
    x = m.index.values
    y = m["net_"+teamA].values

    plt.figure()
    plt.bar(x, y)
    plt.title(f"Match momentum (net xT) | {teamA} vs {teamB}")
    plt.xlabel("Minute")
    plt.ylabel("Net xT (teamA - teamB)")
    plt.tight_layout()
    plt.savefig(OUTDIR/"momentum_net_xt.png", dpi=200)
    plt.close()

    # --- Twelve-like "attack performance" panel (teamA values)
    metrics = [
        ("Ball possession %", summary["possession_pct"].get(teamA,0.0)),
        ("Field tilt %", summary["field_tilt_pct"].get(teamA,0.0)),
        ("Long ball %", summary["long_ball_pct"].get(teamA,0.0)),
        ("Pass tempo (passes/min)", summary["pass_tempo_per_min"].get(teamA,0.0)),
        ("Possessions → final third %", summary["possessions_to_final_third_pct"].get(teamA,0.0)),
        ("Final third → box %", summary["final_third_to_box_pct"].get(teamA,0.0)),
        ("xT total", summary["xT_total"].get(teamA,0.0)),
    ]
    # simple horizontal plot
    plt.figure(figsize=(9,4))
    labels = [a for a,_ in metrics]
    vals = [b for _,b in metrics]
    yidx = np.arange(len(vals))
    plt.barh(yidx, vals)
    plt.yticks(yidx, labels)
    plt.title(f"{teamA} attack metrics (Twelve-like, heuristic)")
    plt.tight_layout()
    plt.savefig(OUTDIR/"attack_panel_teamA.png", dpi=200)
    plt.close()

    print("OK ->", OUTDIR)
    print("Wrote:", (OUTDIR/"summary.json").as_posix())
    print("Wrote:", (OUTDIR/"events_enriched.csv").as_posix())
    print("Wrote:", (OUTDIR/"momentum_net_xt.png").as_posix())
    print("Wrote:", (OUTDIR/"attack_panel_teamA.png").as_posix())

if __name__ == "__main__":
    main()
