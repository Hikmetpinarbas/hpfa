import json

def load_polarity_dict(path: str):
    with open(path, "r", encoding="utf-8") as f:
        d = json.load(f)
    pos = set([str(x).strip().lower() for x in d.get("force_positive", [])])
    neg = set([str(x).strip().lower() for x in d.get("force_negative", [])])
    neu = set([str(x).strip().lower() for x in d.get("neutral", [])])
    return pos, neg, neu, d
