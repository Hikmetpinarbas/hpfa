import os
import pandas as pd
import matplotlib.pyplot as plt

from tools._shared import load_polarity_dict
DICT_PATH = "tools/dicts_city_gs.json"

CORE = "data/processed/city_gs_events_core.csv"
OUT_DIR = "artifacts/phase"
BIN_MIN = 5.0


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
    df = pd.read_csv(CORE)
    df = df.dropna(subset=["team_name"]).copy()
    df = df.sort_values(["half", "t_start", "event_id"], na_position="last").reset_index(drop=True)

    df["bin"] = (df["t_start"] // BIN_MIN) * BIN_MIN
    df["mom_evt"] = df["action_label"].apply(lambda x: score_action(x, POS, NEG))

    # switch count within each (half, bin)
    df["prev_team"] = df.groupby(["half", "bin"])["team_name"].shift(1)
    df["switch"] = (df["team_name"] != df["prev_team"]).astype(int)
    df.loc[df["prev_team"].isna(), "switch"] = 0

    totals = (
        df.groupby(["half", "bin"], dropna=True)
          .agg(total_events=("event_id","count"),
               switch_count=("switch","sum"),
               mom_bin_total=("mom_evt","sum"))
          .reset_index()
    )

    # per team counts (this will miss bins where a team has 0 events)
    team_bin = (
        df.groupby(["half","bin","team_name"], dropna=True)
          .agg(event_count=("event_id","count"),
               mom_sum=("mom_evt","sum"))
          .reset_index()
    )

    # ensure BOTH teams exist in EVERY (half, bin)
    teams = sorted(df["team_name"].unique().tolist())
    hb = totals[["half","bin"]].drop_duplicates()
    grid = hb.assign(_k=1).merge(pd.DataFrame({"team_name": teams, "_k": 1}), on="_k").drop(columns="_k")

    out = grid.merge(team_bin, on=["half","bin","team_name"], how="left")
    out["event_count"] = out["event_count"].fillna(0).astype(int)
    out["mom_sum"] = out["mom_sum"].fillna(0).astype(int)

    out = out.merge(totals, on=["half","bin"], how="left")

    out["possession_share_proxy"] = out["event_count"] / out["total_events"].clip(lower=1)
    out["transition_index"] = out["switch_count"] / out["total_events"].clip(lower=1)

    # data-driven thresholds (now meaningful)
    low_poss = out["possession_share_proxy"].quantile(0.40)
    high_poss = out["possession_share_proxy"].quantile(0.60)
    low_mom = out["mom_sum"].quantile(0.35)
    high_mom = out["mom_sum"].quantile(0.65)

    def phase_v3(r):
        share = r["possession_share_proxy"]
        mom = r["mom_sum"]
        # attack if high share and non-negative mom OR high mom with >= neutral share
        if (share >= high_poss and mom >= 0) or (mom >= high_mom and share >= 0.5):
            return "attack"
        # defence if low share and non-positive mom OR low mom with <= neutral share
        if (share <= low_poss and mom <= 0) or (mom <= low_mom and share <= 0.5):
            return "defence"
        return "transition"

    out["phase_label_v3"] = out.apply(phase_v3, axis=1)

    # write
    out = out.sort_values(["half","bin","team_name"]).reset_index(drop=True)
    out_csv = os.path.join(OUT_DIR, "city_gs_phase_5min_v3.csv")
    out.to_csv(out_csv, index=False)

    # diagnostics
    print("[v3] teams:", teams)
    print("[v3] possession quantiles:",
          {q: float(out["possession_share_proxy"].quantile(q)) for q in [0.1,0.25,0.4,0.5,0.6,0.75,0.9]})
    print("[v3] mom_sum quantiles:",
          {q: float(out["mom_sum"].quantile(q)) for q in [0.1,0.25,0.35,0.5,0.65,0.75,0.9]})
    print("[v3] thresholds:",
          f"low_poss(q40)={low_poss:.3f} high_poss(q60)={high_poss:.3f} low_mom(q35)={low_mom:.3f} high_mom(q65)={high_mom:.3f}")
    print("[v3] phase_counts:")
    print(out["phase_label_v3"].value_counts().to_string())

    # plot: possession+momentum
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    for team in teams:
        g = out[out["team_name"] == team]
        x = g["bin"] + (g["half"]-1)*45
        axes[0].plot(x, g["possession_share_proxy"], marker="o", label=team)
        axes[1].plot(x, g["mom_sum"], marker="o", label=team)

    axes[0].set_ylabel("Possession share (proxy)")
    axes[0].set_ylim(0, 1)
    axes[0].axhline(0.5, linewidth=1)
    axes[1].set_ylabel("Momentum (sum)")
    axes[1].axhline(0, linewidth=1)
    axes[1].set_xlabel("Minute (half-merged)")
    axes[0].set_title("City–GS | Possession proxy + Momentum (v3, 5-min bins)")
    axes[0].legend()
    axes[1].legend()
    fig.tight_layout()

    out_png = os.path.join(OUT_DIR, "city_gs_phase_5min_v3.png")
    fig.savefig(out_png, dpi=150)
    plt.close(fig)

    print("[v3] out_csv:", out_csv)
    print("[v3] out_png:", out_png)

if __name__ == "__main__":
    main()
