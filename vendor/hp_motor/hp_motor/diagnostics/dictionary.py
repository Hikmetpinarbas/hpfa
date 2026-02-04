from __future__ import annotations
import pandas as pd
import re

def _norm(s: str) -> str:
    s = str(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.replace("%", " %")
    return s

def load_dictionary(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # boş/satır başlığı gibi satırlar varsa tutalım ama normalize kolonunu ekleyelim
    df["metric_name_norm"] = df["metric_name"].astype(str).map(_norm)
    return df

def build_alias_map(columns: list[str], dict_df: pd.DataFrame) -> dict[str, str]:
    """
    Returns: {original_col: canonical_metric_name}
    Eşleşme stratejisi: normalize edilmiş tam eşleşme + basit contains fallback.
    """
    col_norm = {_norm(c): c for c in columns}
    dict_norm = dict(zip(dict_df["metric_name_norm"], dict_df["metric_name"]))

    alias = {}
    # 1) exact match
    for cn, orig in col_norm.items():
        if cn in dict_norm:
            alias[orig] = dict_norm[cn]

    # 2) contains fallback (riskli -> WEAK olarak kullanılacak; burada sadece map üretiyoruz)
    dict_keys = list(dict_norm.keys())
    for cn, orig in col_norm.items():
        if orig in alias:
            continue
        hits = [k for k in dict_keys if (cn in k) or (k in cn)]
        if len(hits) == 1:
            alias[orig] = dict_norm[hits[0]]

    return alias
