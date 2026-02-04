import os
import pandas as pd
import matplotlib.pyplot as plt

SRC_V3 = "artifacts/phase/city_gs_phase_5min_v3.csv"
OUT_DIR = "artifacts/phase"

def main():
    df = pd.read_csv(SRC_V3)

    # thresholds (data-driven)
    low_poss = df["possession_share_proxy"].quantile(0.40)
    high_poss = df["possession_share_proxy"].quantile(0.60)
    high_trans = df["transition_index"].quantile(0.60)

    # momentum is optional cue (only if positive)
    pos_mom = df["mom_sum"].quantile(0.70)

    def phase_v5(r):
        share = r["possession_share_proxy"]
        trans = r["transition_index"]
        mom = r["mom_sum"]

        # Defence: low possession AND high transition pressure
        if share <= low_poss and trans >= high_trans:
            return "defence"

        # Attack: high possession OR clearly positive momentum with neutral+ share
        if (share >= high_poss) or (mom >= pos_mom and share >= 0.5):
            return "attack"

        return "transition"

    df["phase_label_v5"] = df.apply(phase_v5, axis=1)

    print("[v5] thresholds:",
          f"low_poss(q40)={low_poss:.3f} high_poss(q60)={high_poss:.3f} high_trans(q60)={high_trans:.3f} pos_mom(q70)={pos_mom:.3f}")
    print("[v5] counts:")
    print(df["phase_label_v5"].value_counts().to_string())

    out_csv = os.path.join(OUT_DIR, "city_gs_phase_5min_v5.csv")
    df.to_csv(out_csv, index=False)

    # Plot phase shares per team (stacked)
    teams = sorted(df["team_name"].dropna().unique().tolist())
    shares = []
    for t in teams:
        g = df[df["team_name"] == t]
        vc = g["phase_label_v5"].value_counts(normalize=True)
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
    ax.set_title("City–GS | Phase shares (v5: defence via low possession + high transition)")
    ax.legend()
    fig.tight_layout()

    out_png = os.path.join(OUT_DIR, "city_gs_phase_shares_v5.png")
    fig.savefig(out_png, dpi=150)
    plt.close(fig)

    print("[v5] out_csv:", out_csv)
    print("[v5] out_png:", out_png)

if __name__ == "__main__":
    main()
