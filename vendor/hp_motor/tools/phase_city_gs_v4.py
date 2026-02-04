import os
import pandas as pd
import matplotlib.pyplot as plt

SRC_V3 = "artifacts/phase/city_gs_phase_5min_v3.csv"
OUT_DIR = "artifacts/phase"

def main():
    df = pd.read_csv(SRC_V3)

    # thresholds from existing columns
    low_poss = df["possession_share_proxy"].quantile(0.40)
    high_poss = df["possession_share_proxy"].quantile(0.60)

    # IMPORTANT: treat mom_sum==0 as neutral, not negative
    # define mom thresholds around positive/negative tails
    pos_mom = df["mom_sum"].quantile(0.70)   # usually 1+
    neg_mom = df["mom_sum"].quantile(0.30)   # usually 0 (so we'll force negative only)
    # Force negative threshold to -1, because 0 isn't "negative"
    neg_mom = -1

    def phase_v4(r):
        share = r["possession_share_proxy"]
        mom = r["mom_sum"]
        # Attack: high share and non-negative OR clearly positive mom with >= neutral share
        if (share >= high_poss and mom >= 0) or (mom >= pos_mom and share >= 0.5):
            return "attack"
        # Defence: low share AND truly negative momentum (strict)
        if (share <= low_poss and mom <= neg_mom):
            return "defence"
        # Transition: high switching or middling zones
        return "transition"

    df["phase_label_v4"] = df.apply(phase_v4, axis=1)

    print("[v4] thresholds:",
          f"low_poss(q40)={low_poss:.3f} high_poss(q60)={high_poss:.3f} pos_mom(q70)={pos_mom:.3f} neg_mom={neg_mom}")
    print("[v4] counts:")
    print(df["phase_label_v4"].value_counts().to_string())

    out_csv = os.path.join(OUT_DIR, "city_gs_phase_5min_v4.csv")
    df.to_csv(out_csv, index=False)

    # Plot phase shares per team (stacked)
    teams = sorted(df["team_name"].dropna().unique().tolist())
    shares = []
    for t in teams:
        g = df[df["team_name"] == t]
        vc = g["phase_label_v4"].value_counts(normalize=True)
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
    ax.set_title("City–GS | Phase shares (v4: neutral momentum handled)")
    ax.legend()
    fig.tight_layout()

    out_png = os.path.join(OUT_DIR, "city_gs_phase_shares_v4.png")
    fig.savefig(out_png, dpi=150)
    plt.close(fig)

    print("[v4] out_csv:", out_csv)
    print("[v4] out_png:", out_png)

if __name__ == "__main__":
    main()
