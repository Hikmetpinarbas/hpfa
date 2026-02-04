import os
import numpy as np
import pandas as pd

SRC = "artifacts/phase/city_gs_phase_5min_v7.csv"   # aslında 5s bin
OUT = "artifacts/phase/city_gs_phase_5min_v7_rollup5m.csv"

ATT_HIGH = 0.65
DEF_LOW  = 0.35
MOM_POS  = 1
MOM_NEG  = -1

SW_TH = 22          # rollup(5dk) switch_count eşiği (p70-80 bandı)
MOM_DEF_B_MAX = 0   # both_active_switch için momentum freni

def phase_v7_row(r):
    share = float(r["possession_share_proxy"])
    mom   = float(r["mom_sum"])
    sw    = int(r["switch_count"])
    ta    = int(r.get("teams_active", 0) or 0)

    if (share >= ATT_HIGH) or (mom >= MOM_POS and share >= 0.50):
        return "attack"
        # Defence-A: net reaktif (neg momentum)
    if (share <= DEF_LOW) and (mom <= MOM_NEG):
        return "defence"

    # Defence-B: düşük share + iki takım aktif + yüksek switch + momentum pozitif değil
    if (share <= DEF_LOW) and (ta == 2) and (sw >= SW_TH) and (mom <= MOM_DEF_B_MAX):
        return "defence"
    return "transition"

def main():
    df = pd.read_csv(SRC)

    # 5 dakika bin (saniye)
    df["bin_5m"] = (np.floor(df["bin"] / 300.0) * 300).astype(int)

    # 5dk rollup
    gcols = ["team_name", "half", "bin_5m"]
    agg = df.groupby(gcols).agg(
        possession_share_proxy=("possession_share_proxy", "mean"),
        mom_sum=("mom_sum", "sum"),
        switch_count=("switch_count", "sum"),
        teams_active=("teams_active", "max"),
        event_count=("event_count", "sum"),
    ).reset_index().rename(columns={"bin_5m": "bin"})

    agg["phase_label_v7_5m"] = agg.apply(phase_v7_row, axis=1)

    os.makedirs("artifacts/phase", exist_ok=True)
    agg.to_csv(OUT, index=False)

    print("[rollup] out:", OUT)
    print("[rollup] rows:", agg.shape[0])
    print("[rollup] counts:")
    print(agg["phase_label_v7_5m"].value_counts().to_string())

if __name__ == "__main__":
    main()
