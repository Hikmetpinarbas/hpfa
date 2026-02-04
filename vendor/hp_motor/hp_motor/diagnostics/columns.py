from __future__ import annotations
from pathlib import Path
import pandas as pd

def list_event_columns(path: str) -> list[str]:
    p = Path(path)
    df = pd.read_csv(p, sep=";", engine="python", encoding="utf-8")
    return list(df.columns)

def list_action_values(path: str, col: str = "action", top: int = 30):
    p = Path(path)
    df = pd.read_csv(p, sep=";", engine="python", encoding="utf-8")
    if col not in df.columns:
        return None
    return df[col].astype(str).str.lower().value_counts().head(top)
