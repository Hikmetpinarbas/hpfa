#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
from pathlib import Path
import pandas as pd

PITCH_L = 105.0
PITCH_W = 68.0

SRC = Path("data/raw/city_gs.csv")
MAP_JSON = Path("data/ref/sportsbase_metrics_hp_v1.json")

OUT_DIR = Path("artifacts/city_gs")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_match_csv(p: Path) -> pd.DataFrame:
    # Twelve export: çoğu zaman ; ile ayrılmış oluyor
    df = pd.read_csv(p, sep=";", quotechar='"', encoding="utf-8", engine="python")
    # kolon isimlerini normalize et
    df.columns = [c.strip() for c in df.columns]

    # temel alanlar
    need = ["team", "action", "t_start", "t_end", "pos_x", "pos_y"]
    miss = [c for c in need if c not in df.columns]
    if miss:
        raise SystemExit(f"[ERR] Missing columns in CSV: {miss}\nHave: {df.columns.tolist()}")

    # sayısallaştır
    for c in ["t_start","t_end","pos_x","pos_y"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # saniye -> dakika bin (momentum için)
    df["t_mid"] = (df["t_start"].fillna(0) + df["t_end"].fillna(df["t_start"].fillna(0))) / 2.0
    df["minute_bin"] = (df["t_mid"] // 60).astype("Int64")

    # saha koordinatı: eğer 0-100 ise 105x68'e çek
    # basit kontrol: max<=100 ise ölçekle
    if df["pos_x"].max(skipna=True) <= 100.0:
        df["x"] = df["pos_x"] * (PITCH_L/100.0)
    else:
        df["x"] = df["pos_x"]

    if df["pos_y"].max(skipna=True) <= 100.0:
        df["y"] = df["pos_y"] * (PITCH_W/100.0)
    else:
        df["y"] = df["pos_y"]

    return df

def load_mapping(map_json: Path):
    j = json.loads(map_json.read_text(encoding="utf-8"))
    # metrics listesi: name -> phase_id/phase_name
    metrics = j.get("metrics", [])
    m = {}
    for it in metrics:
        # json yapısı farklı olabilir, güvenli al
        name = (it.get("candidate_name") or it.get("name") or it.get("metric") or "").strip()
        if not name:
            continue
        m[name.lower()] = {
            "phase_id": it.get("phase_id"),
            "phase_name": it.get("phase_name"),
            "polarity": it.get("polarity"),
            "unit": it.get("unit"),
        }
    phases = {p.get("id"): p.get("name") for p in j.get("phases", []) if isinstance(p, dict)}
    return m, phases

def main():
    if not SRC.exists():
        raise SystemExit(f"[ERR] Missing file: {SRC} (kopyalamadın)")

    df = load_match_csv(SRC)

    mapping = None
    phases = None
    if MAP_JSON.exists():
        mapping, phases = load_mapping(MAP_JSON)
    else:
        mapping, phases = {}, {}

    # --- phase tag ---
    def phase_of(action: str):
        if not isinstance(action, str):
            return None
        x = mapping.get(action.lower())
        if not x:
            return None
        pid = x.get("phase_id")
        pname = x.get("phase_name") or (phases.get(pid) if pid is not None else None)
        return pname

    df["phase"] = df["action"].apply(phase_of)
    df["phase"] = df["phase"].fillna("UNMAPPED")

    # --- momentum proxy ---
    # Twelve momentum tam olarak bilinmiyor; ilk prototip:
    # dakika bazında "tehlike" = (box içi aksiyon + şut + duran top şut) ağırlıklı sayım
    # action metinlerine göre kaba ağırlık
    a = df["action"].astype(str).str.lower()
    df["w"] = 1.0
    df.loc[a.str.contains("shot|şut", regex=True), "w"] += 2.0
    df.loc[a.str.contains("box|ceza sah", regex=True), "w"] += 1.5
    df.loc[a.str.contains("xg|xt", regex=True), "w"] += 2.0
    df.loc[a.str.contains("set|duran|free-kick|corner|korner", regex=True), "w"] += 0.5

    mom = (
        df.dropna(subset=["minute_bin"])
          .groupby(["minute_bin","team"], as_index=False)["w"].sum()
          .pivot(index="minute_bin", columns="team", values="w")
          .fillna(0.0)
          .sort_index()
    )
    # iki takım bul
    teams = list(mom.columns)
    if len(teams) >= 2:
        mom["momentum_diff"] = mom[teams[0]] - mom[teams[1]]
        mom["team_pos"] = teams[0]
        mom["team_neg"] = teams[1]
    else:
        mom["momentum_diff"] = 0.0

    # --- phase totals by team ---
    phase_tot = (
        df.groupby(["team","phase"], as_index=False)
          .size()
          .rename(columns={"size":"n"})
          .sort_values(["team","n"], ascending=[True,False])
    )

    # export
    df.to_csv(OUT_DIR/"events_clean.csv", index=False, encoding="utf-8")
    mom.reset_index().to_csv(OUT_DIR/"momentum_by_minute.csv", index=False, encoding="utf-8")
    phase_tot.to_csv(OUT_DIR/"phase_counts.csv", index=False, encoding="utf-8")

    print("[OK] wrote:")
    print(" -", OUT_DIR/"events_clean.csv")
    print(" -", OUT_DIR/"momentum_by_minute.csv")
    print(" -", OUT_DIR/"phase_counts.csv")

    # optional plot
    try:
        import matplotlib.pyplot as plt
        fig = plt.figure()
        x = mom.index.to_numpy()
        y = mom["momentum_diff"].to_numpy()
        plt.bar(x, y)
        plt.axhline(0, linewidth=1)
        plt.title("Match momentum (proxy) | minute bins")
        plt.xlabel("Minute")
        plt.ylabel("Momentum diff")
        fig.savefig(OUT_DIR/"momentum.png", dpi=160, bbox_inches="tight")
        plt.close(fig)
        print(" -", OUT_DIR/"momentum.png")
    except Exception as e:
        print("[WARN] plot skipped:", e)

if __name__ == "__main__":
    main()
