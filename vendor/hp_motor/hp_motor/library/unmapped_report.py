from __future__ import annotations
import re
from pathlib import Path
import pandas as pd
import json

def norm(s: str) -> str:
    s = str(s).strip().lower()
    s = s.replace("’", "'")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[•\t]", " ", s)
    return s

def load_unique_names(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        t = line.strip()
        if not t:
            continue
        # metrik olmayan satırları filtrele (ama agresif olmayalım)
        if t.lower().startswith(("amaç:", "not:", "liste:", "kapsam:", "#")):
            continue
        out.append(t)
    # normalize duplicate remove
    seen = set()
    cleaned = []
    for x in out:
        k = norm(x)
        if k and k not in seen:
            seen.add(k)
            cleaned.append(x)
    return cleaned

def load_dictionary(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "metric_name" not in df.columns:
        raise ValueError("dictionary csv must have 'metric_name' column")
    df["metric_name_norm"] = df["metric_name"].astype(str).map(norm)
    return df

def load_ontology(root: Path) -> dict | None:
    # optional: metric_ontology.json
    p = root / "metric_ontology.json"
    if not p.exists():
        # sometimes nested
        hits = list(root.rglob("metric_ontology.json"))
        if not hits:
            return None
        p = hits[0]
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None

def main():
    base = Path("hp_motor/library")
    unique_path = base / "HP_METRIC_NAMES_UNIQUE_v1.txt"
    dict_path = base / "hp_metric_dictionary.csv"
    onto_root = base / "ontology"

    names = load_unique_names(unique_path)
    ddf = load_dictionary(dict_path)
    dict_set = set(ddf["metric_name_norm"].tolist())

    unmapped = [n for n in names if norm(n) not in dict_set]

    # write outputs
    out1 = Path("hp_motor/reports/unmapped_metrics.txt")
    out1.write_text("\n".join(unmapped), encoding="utf-8")

    # lightweight grouping heuristic (physical/gk/set-piece etc.)
    def bucket(n: str) -> str:
        k = norm(n)
        if any(x in k for x in ["speed", "distance", "metabolic", "kcal", "energy", "accel", "decel"]):
            return "physical_tracking"
        if any(x in k for x in ["gk", "keeper", "goalkeeper", "save", "psxg"]):
            return "goalkeeper"
        if any(x in k for x in ["corner", "free kick", "set piece", "duran top", "taç"]):
            return "set_piece"
        if any(x in k for x in ["press", "ppda", "pressure"]):
            return "pressing"
        if any(x in k for x in ["xg", "shot", "şut", "goal"]):
            return "shots_xg"
        return "other"

    buckets = {}
    for n in unmapped:
        b = bucket(n)
        buckets.setdefault(b, []).append(n)

    out2 = Path("hp_motor/reports/unmapped_metrics_grouped.txt")
    lines = []
    for b in sorted(buckets.keys()):
        lines.append(f"[{b}] ({len(buckets[b])})")
        lines.extend(buckets[b])
        lines.append("")
    out2.write_text("\n".join(lines), encoding="utf-8")

    print(f"OK: unique={len(names)} dict={len(ddf)} unmapped={len(unmapped)}")
    print("Wrote:")
    print(f"- {out1}")
    print(f"- {out2}")

if __name__ == "__main__":
    main()
