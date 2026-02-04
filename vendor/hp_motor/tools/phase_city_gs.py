import os
import pandas as pd
import matplotlib.pyplot as plt

SRC = "data/processed/city_gs_events_core.csv"
OUT_DIR = "artifacts/phase"
BIN_MIN = 5.0  # minutes

# Same MVP dictionary as momentum (keep consistent)
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

def score_action(label):
    if not isinstance(label, str):
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
    df = pd.read_csv(SRC)

    # Guards
    for c in ["t_start", "team_name", "action_label", "event_id"]:
        if c not in df.columns:
            raise SystemExit(f"Missing column: {c}")

    # Drop meta rows without team
    df = df.dropna(subset=["team_name"]).copy()

    # Sort chronologically
    df = df.sort_values(["half", "t_start", "event_id"], na_position="last").reset_index(drop=True)

    # Bin
    df["bin"] = (df["t_start"] // BIN_MIN) * BIN_MIN

    # Momentum score per event
    df["mom_evt"] = df["action_label"].apply(score_action)

    # Possession proxy: count switches within each bin (team changes)
    # switch = current team != previous team (within same half+bin)
    df["prev_team"] = df.groupby(["half", "bin"])["team_name"].shift(1)
    df["switch"] = (df["team_name"] != df["prev_team"]).astype(int)
    df.loc[df["prev_team"].isna(), "switch"] = 0  # first row in bin isn't a switch

    # Aggregates per (team, bin)
    team_bin = (
        df.groupby(["team_name", "half", "bin"], dropna=True)
          .agg(
              event_count=("event_id", "count"),
              mom_sum=("mom_evt", "sum"),
          )
          .reset_index()
    )

    # Totals per (half, bin)
    totals = (
        df.groupby(["half", "bin"], dropna=True)
          .agg(
              total_events=("event_id", "count"),
              switch_count=("switch", "sum"),
          )
          .reset_index()
    )

    out = team_bin.merge(totals, on=["half","bin"], how="left")
    out["possession_share_proxy"] = out["event_count"] / out["total_events"].clip(lower=1)

    # Transition intensity proxy: more switches => more transition-y
    # Normalize by total events to avoid bin length artifacts
    out["transition_index"] = out["switch_count"] / out["total_events"].clip(lower=1)

    # Phase label (MVP):
    # - attack: possession_share high AND momentum positive
    # - defence: possession_share low AND momentum negative
    # - transition: else
    def phase_row(r):
        share = r["possession_share_proxy"]
        mom = r["mom_sum"]
        if share >= 0.52 and mom >= 1:
            return "attack"
        if share <= 0.48 and mom <= -1:
            return "defence"
        return "transition"

    out["phase_label"] = out.apply(phase_row, axis=1)

    # Output CSV
    csv_out = os.path.join(OUT_DIR, "city_gs_phase_5min.csv")
    out = out.sort_values(["half","bin","team_name"]).reset_index(drop=True)
    out.to_csv(csv_out, index=False)

    # Plot: two panels (possession share + momentum), per team
    teams = sorted(out["team_name"].dropna().unique().tolist())
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)

    for team in teams:
        g = out[out["team_name"] == team]
        x = g["bin"] + (g["half"]-1)*45  # put halves on one timeline (rough)
        axes[0].plot(x, g["possession_share_proxy"], marker="o", label=team)
        axes[1].plot(x, g["mom_sum"], marker="o", label=team)

    axes[0].set_ylabel("Possession share (proxy)")
    axes[0].set_ylim(0, 1)
    axes[0].axhline(0.5, linewidth=1)

    axes[1].set_ylabel("Momentum (sum)")
    axes[1].axhline(0, linewidth=1)
    axes[1].set_xlabel("Minute (half-merged)")

    axes[0].set_title("City–GS | Possession proxy + Momentum (5-min bins)")
    axes[0].legend()
    axes[1].legend()

    fig.tight_layout()
    png_out = os.path.join(OUT_DIR, "city_gs_phase_5min.png")
    fig.savefig(png_out, dpi=150)
    plt.close(fig)

    # Console summary
    print("[phase] src:", SRC)
    print("[phase] out_csv:", csv_out)
    print("[phase] out_png:", png_out)
    print("[phase] rows:", out.shape[0])
    print("[phase] teams:", teams)
    print("[phase] phase_counts:")
    print(out["phase_label"].value_counts().to_string())

if __name__ == "__main__":
    main()
