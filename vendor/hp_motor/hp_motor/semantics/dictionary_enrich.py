from __future__ import annotations
import pandas as pd
import re

def _norm(s: str) -> str:
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def load_dictionary(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # bazı satırlar sezon başlığı gibi (ör: 2025/2026) -> unit/polarity boş; yine de bırakırız
    df["metric_name_norm"] = df["metric_name"].astype(str).map(_norm)
    return df

def enrich(metric_name: str, dict_df: pd.DataFrame | None) -> dict:
    if dict_df is None:
        return {"unit": None, "polarity": None, "recommended_transform": None, "canonical_family": None}

    n = _norm(metric_name)
    row = dict_df[dict_df["metric_name_norm"] == n]
    if row.empty:
        return {"unit": None, "polarity": None, "recommended_transform": None, "canonical_family": None}

    r = row.iloc[0]
    return {
        "unit": None if pd.isna(r.get("unit")) else r.get("unit"),
        "polarity": None if pd.isna(r.get("polarity")) else r.get("polarity"),
        "recommended_transform": None if pd.isna(r.get("recommended_transform")) else r.get("recommended_transform"),
        "canonical_family": None if pd.isna(r.get("canonical_family")) else r.get("canonical_family"),
    }
