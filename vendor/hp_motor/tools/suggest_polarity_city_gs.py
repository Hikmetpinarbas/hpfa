import json
import pandas as pd

SRC = "artifacts/registry/city_gs_action_labels.csv"
OUT = "artifacts/registry/city_gs_polarity_suggest.json"

POS_KW = [
    "accurate", "successful", "won", "recover", "kazan", "başarılı", "isabetli",
    "shot on target", "goal", "gol", "save", "kurtar",
]
NEG_KW = [
    "incomplete", "unsuccessful", "loss", "kayb", "kayıp", "başarısız", "isabetsiz",
    "foul", "faul", "lost",
    "inaccurate",  # explicit
]
NEUTRAL_KW = [
    "start of the", "end of the",
]

def has_any(s, kws):
    return any(k in s for k in kws)

def main():
    df = pd.read_csv(SRC)
    df["label"] = df["action_label"].astype(str)
    df = df.sort_values("count", ascending=False).reset_index(drop=True)

    pos, neg, neutral, review = [], [], [], []

    for _, r in df.iterrows():
        label = r["label"].strip().lower()
        cnt = int(r["count"])

        # quick neutral/meta filter
        if has_any(label, [k.lower() for k in NEUTRAL_KW]):
            neutral.append({"label": label, "count": cnt})
            continue

        # critical guard: don't let "inaccurate" be treated as "accurate"
        if "inaccurate" in label:
            n = True
            p = False
        else:
            p = has_any(label, [k.lower() for k in POS_KW])
            n = has_any(label, [k.lower() for k in NEG_KW])

        if p and not n:
            pos.append({"label": label, "count": cnt})
        elif n and not p:
            neg.append({"label": label, "count": cnt})
        elif p and n:
            review.append({"label": label, "count": cnt, "reason": "pos+neg keywords"})
        else:
            if cnt >= 20:
                review.append({"label": label, "count": cnt, "reason": "high freq, no keywords"})
            else:
                neutral.append({"label": label, "count": cnt})

    payload = {
        "source": SRC,
        "positive_candidates": pos[:80],
        "negative_candidates": neg[:80],
        "manual_review": review[:120],
        "neutral": neutral[:120],
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print("[suggest] out:", OUT)
    print("[suggest] pos:", len(payload["positive_candidates"]))
    print("[suggest] neg:", len(payload["negative_candidates"]))
    print("[suggest] review:", len(payload["manual_review"]))
    print("[suggest] neutral:", len(payload["neutral"]))
    print("\n[suggest] top_pos (10):")
    for x in payload["positive_candidates"][:10]:
        print(" -", x["label"], x["count"])
    print("\n[suggest] top_neg (10):")
    for x in payload["negative_candidates"][:10]:
        print(" -", x["label"], x["count"])

if __name__ == "__main__":
    main()
