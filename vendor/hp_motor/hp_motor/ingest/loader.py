from __future__ import annotations
import pandas as pd

def _detect_sep(path: str) -> str:
    # Basit ve etkili: ilk satıra bak, noktalı virgül yoğun ise ';' kullan
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        first = f.readline()
    if first.count(";") >= first.count(","):
        return ";"
    return ","

def load_table(path: str) -> pd.DataFrame:
    p = path.lower()

    if p.endswith(".xlsx") or p.endswith(".xls"):
        return pd.read_excel(path)

    if p.endswith(".csv"):
        sep = _detect_sep(path)
        return pd.read_csv(path, sep=sep, encoding="utf-8", engine="python")

    raise ValueError(f"Unsupported file type: {path}")
