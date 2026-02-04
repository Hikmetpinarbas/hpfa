import os
import pandas as pd
import matplotlib.pyplot as plt

SRC_PHASE_V1 = "artifacts/phase/city_gs_phase_5min.csv"
OUT_DIR = "artifacts/phase"

def main():
    df = pd.read_csv(SRC_PHASE_V1)

    # Calibrate thresholds from data distribution
    # possession: low vs high
    low_poss = df["possession_share_proxy"].quantile(0.40)
    high_poss = df["possession_share_proxy"].quantile(0.60)

    # momentum: low vs high (use mom_sum distribution)
    low_mom = df["mom_sum"].quantile(0.35)
    high_mom = df["mom_sum"].quantile(0.65)

    def phase_v2(r):
        share = r["possession_share_proxy"]
        mom = r["mom_sum"]
        # Attack: high share OR high mom (both strong gives more confidence)
        if (share >= high_poss and mom >= 0) or (mom >= high_mom and share >= 0.5):
            return "attack"
        # Defence: low share OR low mom
        if (share <= low_poss and mom <= 0) or (mom <= low_mom and share <= 0.5):
            return "defence"
        return "transition"

    df["phase_label_v2"] = df.apply(phase_v2, axis=1)

    # Summaries
    v1 = df["phase_label"].value_counts()
    v2 = df["phase_label_v2"].value_counts()

    print("[calib] thresholds:")
    print(f"  low_poss(q40)={low_poss:.3f}  high_poss(q60)={high_poss:.3f}")
    print(f"  low_mom(q35) ={low_mom:.3f}  high_mom(q65) ={high_mom:.3f}")
    print("\n[v1 counts]")
    print(v1.to_string())
    print("\n[v2 counts]")
    print(v2.to_string())

    # Write v2 csv
    out_csv = os.path.join(OUT_DIR, "city_gs_phase_5min_v2.csv")
    df.to_csv(out_csv, index=False)

    # Plot: stacked shares per team (v2)
    teams = sorted(df["team_name"].dropna().unique().tolist())
    shares = []
    for t in teams:
        g = df[df["team_name"] == t]
        vc = g["phase_label_v2"].value_counts(normalize=True)
        shares.append([
            vc.get("attack", 0.0),
            vc.get("transition", 0.0),
            vc.get("defence", 0.0),
        ])

    fig = plt.figure(figsize=(8,4))
    ax = fig.add_subplot(111)

    attack = [s[0] for s in shares]
    trans  = [s[1] for s in shares]
    defend = [s[2] for s in shares]

    x = list(range(len(teams)))
    ax.bar(x, attack, label="attack")
    ax.bar(x, trans, bottom=attack, label="transition")
    ax.bar(x, defend, bottom=[a+t for a,t in zip(attack, trans)], label="defence")

    ax.set_xticks(x)
    ax.set_xticklabels(teams, rotation=0)
    ax.set_ylim(0,1)
    ax.set_ylabel("Share of 5-min bins")
    ax.set_title("City–GS | Phase shares (v2 calibrated)")
    ax.legend()
    fig.tight_layout()

    out_png = os.path.join(OUT_DIR, "city_gs_phase_shares_v2.png")
    fig.savefig(out_png, dpi=150)
    plt.close(fig)

    print("\n[calib] out_csv:", out_csv)
    print("[calib] out_png:", out_png)

if __name__ == "__main__":
    main()
