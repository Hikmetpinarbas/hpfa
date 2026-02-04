import os
import pandas as pd
import matplotlib.pyplot as plt

CORE = "data/processed/city_gs_events_core.csv"
PHASE = "artifacts/phase/city_gs_phase_5min.csv"
OUT_DIR = "artifacts/scorecard"

# Keep consistent with momentum/phase dictionaries
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
    core = pd.read_csv(CORE)
    core = core.dropna(subset=["team_name"]).copy()
    core["score"] = core["action_label"].apply(score_action)

    # match duration proxy (max t_start per half)
    dur = core.groupby("half")["t_start"].max().fillna(0).to_dict()
    match_minutes = float(dur.get(1, 45)) + float(dur.get(2, 45))
    if match_minutes <= 0:
        match_minutes = 90.0

    # core-level aggregates per team
    g = core.groupby("team_name")
    summary = pd.DataFrame({
        "team_name": g.size().index,
        "event_count": g.size().values,
        "mom_total": g["score"].sum().values,
        "mom_per90": (g["score"].sum() * (90.0 / match_minutes)).values,
        "pos_actions": (g["score"].apply(lambda s: (s==1).sum())).values,
        "neg_actions": (g["score"].apply(lambda s: (s==-1).sum())).values,
    })
    summary["pass_eff_proxy"] = summary["pos_actions"] / (summary["pos_actions"] + summary["neg_actions"]).replace(0, 1)

    # phase file aggregates (per team bins)
    ph = pd.read_csv(PHASE)
    # possession proxy average over bins
    poss = ph.groupby("team_name")["possession_share_proxy"].mean().reset_index()
    poss = poss.rename(columns={"possession_share_proxy":"possession_share_proxy_mean"})

    # phase shares
    phase_counts = ph.pivot_table(index="team_name", columns="phase_label", values="bin", aggfunc="count", fill_value=0)
    phase_counts = phase_counts.reset_index()
    # ensure columns exist
    for col in ["attack","transition","defence"]:
        if col not in phase_counts.columns:
            phase_counts[col] = 0
    tot_bins = (phase_counts["attack"] + phase_counts["transition"] + phase_counts["defence"]).replace(0, 1)
    phase_counts["attack_share"] = phase_counts["attack"] / tot_bins
    phase_counts["transition_share"] = phase_counts["transition"] / tot_bins
    phase_counts["defence_share"] = phase_counts["defence"] / tot_bins

    out = summary.merge(poss, on="team_name", how="left").merge(
        phase_counts[["team_name","attack_share","transition_share","defence_share"]],
        on="team_name", how="left"
    )

    csv_out = os.path.join(OUT_DIR, "city_gs_scorecard.csv")
    out.to_csv(csv_out, index=False)

    # ---- Plot scorecard ----
    teams = out["team_name"].tolist()
    metrics = [
        ("Possession% (proxy)", out["possession_share_proxy_mean"].fillna(0).values * 100),
        ("Momentum/90", out["mom_per90"].fillna(0).values),
        ("Pass eff (proxy)", out["pass_eff_proxy"].fillna(0).values * 100),
        ("Attack share", out["attack_share"].fillna(0).values * 100),
        ("Transition share", out["transition_share"].fillna(0).values * 100),
        ("Defence share", out["defence_share"].fillna(0).values * 100),
    ]

    fig = plt.figure(figsize=(11, 5))
    ax = fig.add_subplot(111)
    ax.axis("off")

    # table-like render
    col_labels = ["Team"] + [m[0] for m in metrics]
    cell_text = []
    for i, team in enumerate(teams):
        row = [team]
        for _, vals in metrics:
            v = vals[i]
            if "Momentum" in col_labels[len(row)]:
                row.append(f"{v:.1f}")
            else:
                row.append(f"{v:.1f}")
        cell_text.append(row)

    table = ax.table(cellText=cell_text, colLabels=col_labels, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 1.5)

    ax.set_title("City–GS | Scorecard (event-only proxies)", pad=12)

    png_out = os.path.join(OUT_DIR, "city_gs_scorecard.png")
    plt.tight_layout()
    plt.savefig(png_out, dpi=150)
    plt.close(fig)

    print("[scorecard] core:", CORE)
    print("[scorecard] phase:", PHASE)
    print("[scorecard] out_csv:", csv_out)
    print("[scorecard] out_png:", png_out)
    print("[scorecard] teams:", teams)

if __name__ == "__main__":
    main()
