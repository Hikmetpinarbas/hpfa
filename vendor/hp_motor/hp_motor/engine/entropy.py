from __future__ import annotations
import pandas as pd
import math

def action_entropy(df: pd.DataFrame) -> float | None:
    col = "action" if "action" in df.columns else ("Action" if "Action" in df.columns else None)
    if not col or df.empty:
        return None

    counts = df[col].astype(str).value_counts()
    total = counts.sum()
    if total == 0:
        return None

    ent = 0.0
    for c in counts:
        p = c / total
        ent -= p * math.log2(p)
    return ent
