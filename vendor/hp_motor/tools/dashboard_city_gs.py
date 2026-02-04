import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg

MOM_PNG = "artifacts/momentum/city_gs_momentum_5min.png"
PHASE_V3_PNG = "artifacts/phase/city_gs_phase_5min_v7.png"
PHASE_V6_SHARES = "artifacts/phase/city_gs_phase_shares_v7.png"
SCORE_PNG = "artifacts/scorecard/city_gs_scorecard.png"

OUT = "artifacts/dashboard/city_gs_dashboard.png"

def safe_img(path):
    if not os.path.exists(path):
        return None
    try:
        return mpimg.imread(path)
    except Exception:
        return None

def main():
    imgs = {
        "Momentum (5min)": safe_img(MOM_PNG),
        "Possession+Momentum (v7)": safe_img(PHASE_V3_PNG),
        "Phase shares (v7)": safe_img(PHASE_V6_SHARES),
        "Scorecard (v7)": safe_img(SCORE_PNG),
    }

    missing = [k for k,v in imgs.items() if v is None]
    if missing:
        raise SystemExit(f"Missing/Unreadable images: {missing}")

    fig = plt.figure(figsize=(12, 8))

    keys = list(imgs.keys())
    for i, k in enumerate(keys, start=1):
        ax = fig.add_subplot(2, 2, i)
        ax.imshow(imgs[k])
        ax.set_title(k, fontsize=10)
        ax.axis("off")

    fig.suptitle("City–GS | HP Motor Dashboard (event-only, lite-core)", fontsize=12)
    fig.tight_layout(rect=[0,0,1,0.96])

    fig.savefig(OUT, dpi=150)
    plt.close(fig)

    print("[dashboard] out:", OUT)
    print("[dashboard] sources:")
    print(" -", MOM_PNG)
    print(" -", PHASE_V3_PNG)
    print(" -", PHASE_V6_SHARES)
    print(" -", SCORE_PNG)

if __name__ == "__main__":
    main()
