import os
import pandas as pd
import matplotlib.pyplot as plt

SRC_V3 = "artifacts/phase/city_gs_phase_5min_v3.csv"
OUT_DIR = "artifacts/phase"

ATT_HIGH = 0.65
DEF_LOW  = 0.35
MOM_POS  = 1
MOM_NEG  = -1

def main():
    df = pd.read_csv(SRC_V3)

    # (half,bin) bazında iki takım da aktif mi?
    both = df.groupby(["half","bin"])["event_count"].apply(lambda s: int((s>0).sum()))
    both = both.reset_index().rename(columns={"event_count":"teams_active"})
    df = df.merge(both, on=["half","bin"], how="left")

    def phase_v7(r):
        share = float(r["possession_share_proxy"])
        mom   = float(r["mom_sum"])
        sw    = int(r["switch_count"])
        ta    = int(r.get("teams_active", 0) or 0)

        # Attack
        if (share >= ATT_HIGH) or (mom >= MOM_POS and share >= 0.50):
            return "attack"

        # Defence: low possession AND (neg momentum OR both-active + at least one switch)
        if (share <= DEF_LOW) and (mom <= MOM_NEG or (ta == 2 and sw >= 1)):
            return "defence"

        return "transition"

    df["phase_label_v7"] = df.apply(phase_v7, axis=1)

    os.makedirs(OUT_DIR, exist_ok=True)
    out_csv = os.path.join(OUT_DIR, "city_gs_phase_5min_v7.csv")
    df.to_csv(out_csv, index=False)

    print("[v7] counts:")
    print(df["phase_label_v7"].value_counts().to_string())

    # Shares plot
    teams = sorted(df["team_name"].dropna().unique().tolist())
    shares = []
    for t in teams:
        g = df[df["team_name"] == t]
        vc = g["phase_label_v7"].value_counts(normalize=True)
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
    ax.set_title("City–GS | Phase shares (v7)")
    ax.legend()
    fig.tight_layout()
    out_shares = os.path.join(OUT_DIR, "city_gs_phase_shares_v7.png")
    fig.savefig(out_shares, dpi=150)
    plt.close(fig)

    # Time-series plot
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    for team in teams:
        g = df[df["team_name"] == team].sort_values(["half","bin"])
        x = g["bin"] + (g["half"]-1)*45
        axes[0].plot(x, g["possession_share_proxy"], marker="o", label=team)
        axes[1].plot(x, g["mom_sum"], marker="o", label=team)

    axes[0].set_ylabel("Possession share (proxy)")
    axes[0].set_ylim(0, 1)
    axes[0].axhline(0.5, linewidth=1)
    axes[1].set_ylabel("Momentum (sum)")
    axes[1].axhline(0, linewidth=1)
    axes[1].set_xlabel("Minute (half-merged)")
    axes[0].set_title("City–GS | Possession proxy + Momentum (v7)")
    axes[0].legend()
    axes[1].legend()
    fig.tight_layout()
    out_ts = os.path.join(OUT_DIR, "city_gs_phase_5min_v7.png")
    fig.savefig(out_ts, dpi=150)
    plt.close(fig)

    print("[v7] out_csv:", out_csv)
    print("[v7] out_shares_png:", out_shares)
    print("[v7] out_ts_png:", out_ts)

if __name__ == "__main__":
    main()
