import os
import pandas as pd
import matplotlib.pyplot as plt

from tools._shared import load_polarity_dict
DICT_PATH = "tools/dicts_city_gs.json"

SRC = "data/processed/city_gs_events_core.csv"
OUT_DIR = "artifacts/momentum"
BIN_MIN = 5.0  # minutes

POSITIVE = {
    "paslar adresi bulanlar",
    "playing in set-piece attacks",
    "successful pass",
    "goal",
    "shot on target",
}

NEGATIVE = {
    "incomplete passes forward",
    "incomplete passes",
    "isabetsiz paslar",
}

def score_action(label, POS, NEG):
    if not isinstance(label, str):
        return 0
    l = label.strip().lower()
    if l in POS:
        return 1
    if l in NEG:
        return -1
    return 0
    l = label.lower()
    for p in POSITIVE:
        if p in l:
            return 1
    for n in NEGATIVE:
        if n in l:
            return -1
    return 0

def main():
    POS, NEG, NEU, META = load_polarity_dict(DICT_PATH)
    df = pd.read_csv(SRC)

    # basic guards
    assert "t_start" in df.columns
    assert "team_name" in df.columns
    assert "action_label" in df.columns

    df["score"] = df["action_label"].apply(lambda x: score_action(x, POS, NEG))

    # time binning
    df["bin"] = (df["t_start"] // BIN_MIN) * BIN_MIN

    # aggregate
    agg = (
        df.groupby(["team_name", "bin"], dropna=True)["score"]
        .sum()
        .reset_index()
        .sort_values(["team_name", "bin"])
    )

    # save csv
    csv_out = os.path.join(OUT_DIR, "city_gs_momentum_5min.csv")
    agg.to_csv(csv_out, index=False)

    # plot
    plt.figure(figsize=(10,4))
    for team, g in agg.groupby("team_name"):
        plt.plot(g["bin"], g["score"], marker="o", label=team)

    plt.axhline(0, linewidth=1)
    plt.xlabel("Minute")
    plt.ylabel("Momentum score")
    plt.title("Manchester City – Galatasaray | Momentum (5-min bins)")
    plt.legend()
    plt.tight_layout()

    png_out = os.path.join(OUT_DIR, "city_gs_momentum_5min.png")
    plt.savefig(png_out, dpi=150)
    plt.close()

    print("[momentum] src:", SRC)
    print("[momentum] out_csv:", csv_out)
    print("[momentum] out_png:", png_out)
    print("[momentum] rows:", agg.shape[0])
    print("[momentum] teams:", agg["team_name"].unique().tolist())

if __name__ == "__main__":
    main()
