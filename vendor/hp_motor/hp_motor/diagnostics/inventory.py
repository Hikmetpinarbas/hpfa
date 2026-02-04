from __future__ import annotations

import json
import pandas as pd


def load_inventory(path: str):
    # expects a CSV file path
    return pd.read_csv(path)


def _infer_ncols_from_info(info_json: str) -> int | None:
    """
    Our staged _inventory.csv stores schema hints inside info_json.
    We try these keys in order:
      - {"columns":[...]}  (csv)
      - {"sample_headers":[...]} (xlsx)
      - {"sheets":[...]} alone is not enough for ncols
    """
    if not isinstance(info_json, str) or not info_json.strip():
        return None
    try:
        obj = json.loads(info_json)
    except Exception:
        return None

    if isinstance(obj, dict):
        cols = obj.get("columns")
        if isinstance(cols, list) and cols:
            return len(cols)
        hdr = obj.get("sample_headers")
        if isinstance(hdr, list) and hdr:
            return len(hdr)
    return None


def allowed_sheets_for_corr(inv: pd.DataFrame, max_corr_pairs: int = 15000):
    """
    Original implementation expected a 'corr_pairs' column.
    If missing, we infer corr_pairs from info_json where possible:
      corr_pairs = n_cols * (n_cols - 1) / 2

    Returns a list of filenames (or sheet identifiers if present).
    """
    if inv is None or len(inv) == 0:
        return []

    inv = inv.copy()

    if "corr_pairs" not in inv.columns:
        # Try to infer corr_pairs
        if "info_json" in inv.columns:
            ncols = inv["info_json"].apply(_infer_ncols_from_info)
            inv["corr_pairs"] = ncols.apply(lambda n: int(n * (n - 1) / 2) if isinstance(n, int) and n >= 2 else 0)
        else:
            # Nothing we can do; skip gating safely
            return []

    ok = inv[inv["corr_pairs"] <= max_corr_pairs]

    # Prefer a stable identifier column
    if "sheet" in ok.columns:
        return ok["sheet"].dropna().astype(str).tolist()
    if "filename" in ok.columns:
        return ok["filename"].dropna().astype(str).tolist()
    # fallback: return index labels
    return ok.index.astype(str).tolist()
