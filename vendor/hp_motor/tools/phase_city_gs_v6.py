import os
import pandas as pd
import matplotlib.pyplot as plt

SRC_V3 = "artifacts/phase/city_gs_phase_5min_v3.csv"
OUT_DIR = "artifacts/phase"

def main():
    df = pd.read_csv(SRC_V3)

    low_poss = df["possession_share_proxy"].quantile(0.40)
    high_poss = df["possession_share_proxy"].quantile(0.60)
    pos_mom = df["mom_sum"].quantile(0.70)

    # key change: use discrete switch_count, not transition_index quantile=0
    # switch_count exists in v3 file
    if "switch_count" not in df.columns:
        raise SystemExit("switch_count missing in v3 file; check phase_city_gs_v3 output columns")

    def phase_v6(r):
        share = r["possession_share_proxy"]
        mom = r["mom_sum"]
        sw = r["switch_count"]

        # Defence: low possession + at least 1 switch (pressure / instability)
        if share <= low_poss and sw >= 1:
            return "defence"

        # Attack
        if (share >= high_poss) or (mom >= pos_mom and share >= 0.5):
            return "attack"

        return "transition"

    df["phase_label_v6"] = df.apply(phase_v6, axis=1)

    print("[v6] thresholds:",
          f"low_poss(q40)={low_poss:.3f} high_poss(q60)={high_poss:.3f} pos_mom(q70)={pos_mom:.3f} | defence requires switch_count>=1")
    print("[v6] counts:")
    print(df["phase_label_v6"].value_counts().to_string())
    print("[v6] switch_count distribution (overall):")
    print(df["switch_count"].value_counts().head(10).to_string())

    out_csv = os.path.join(OUT_DIR, "city_gs_phase_5min_v6.csv")
    df.to_csv(out_csv, index=False)

    teams = sorted(df["team_name"].dropna().unique().tolist())
    shares = []
    for t in teams:
        g = df[df["team_name"] == t]
        vc = g["phase_label_v6"].value_counts(normalize=True)
        shares.append([vc.get("attack",0.0), vc.get("transition",0.0), vc.get("defence",0.0)])

    fig = plt.figure(figsize=(8,4))
    ax = fig.add_subplot(111)
    x = list(range(len(teams)))
    attack = [s[0] for s in shares]
    trans  = [s[1] for s in shares]
    defend = [s[2] for s in shares]

    ax.bar(x, attack, label="attack")
    ax.bar(x, trans, bottom=attack, label="transition")
    ax.bar(x, defend, bottom=[a+t for a,t in zip(attack, trans)], label="defence")
    ax.set_xticks(x)
    ax.set_xticklabels(teams)
    ax.set_ylim(0,1)
    ax.set_ylabel("Share of 5-min bins")
    ax.set_title("City–GS | Phase shares (v6: defence requires switch_count>=1)")
    ax.legend()
    fig.tight_layout()

    out_png = os.path.join(OUT_DIR, "city_gs_phase_shares_v6.png")
    fig.savefig(out_png, dpi=150)
    plt.close(fig)

    print("[v6] out_csv:", out_csv)
    print("[v6] out_png:", out_png)

if __name__ == "__main__":
    main()
