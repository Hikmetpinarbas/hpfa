from __future__ import annotations
import pandas as pd
from hp_motor.metrics.metric_object import MetricObject

def _find_col(df: pd.DataFrame, candidates: list[str]) -> str | None:
    cols = list(df.columns)
    low = {str(c).strip().lower(): c for c in cols}
    for cand in candidates:
        key = cand.strip().lower()
        if key in low:
            return low[key]
    # contains fallback (tek hit)
    hits = []
    for cand in candidates:
        key = cand.strip().lower()
        for k, orig in low.items():
            if key in k:
                hits.append(orig)
    hits = list(dict.fromkeys(hits))
    return hits[0] if len(hits) == 1 else None

def _team_filter(df: pd.DataFrame, team_name: str) -> pd.DataFrame:
    team_col = _find_col(df, ["team", "Team", "Squad", "Takım", "team_name"])
    if not team_col:
        return df.iloc[0:0]  # boş -> team bazlı ayrılamıyor
    s = df[team_col].astype(str).str.lower()
    return df[s.str.contains(team_name.lower(), na=False)]

def extract_team_match_stats(df: pd.DataFrame, team_name: str) -> list[MetricObject]:
    out: list[MetricObject] = []
    tdf = _team_filter(df, team_name)

    # takım kolonunu bulamadıysak: WEAK/UNKNOWN üret
    if tdf.empty:
        out.append(MetricObject(
            name="MatchStats_TeamFilter",
            value=None,
            status="WEAK",
            evidence="Match-stats table present but team column not detected or team not matched",
            interpretation="Match-stats verisi var ancak takım bazlı ayrıştırma zayıf/başarısız; metrikler temkinli okunmalı."
        ))
        return out

    shots_col = _find_col(df, ["Shots", "Total Shots", "Şut", "Suts", "Total_shots"])
    xg_col    = _find_col(df, ["xG", "Expected Goals", "xg"])
    sot_col   = _find_col(df, ["SoT", "Shots on Target", "İsabetli Şut", "Shots_on_target"])

    def _sum(colname: str | None):
        if not colname:
            return None
        return pd.to_numeric(tdf[colname], errors="coerce").sum()

    shots = _sum(shots_col)
    xg    = _sum(xg_col)
    sot   = _sum(sot_col)

    out.append(MetricObject(
        name="Shots",
        value=None if shots is None else float(shots),
        status="OK" if shots is not None else "UNKNOWN",
        evidence=f"Match-stats column: {shots_col}" if shots_col else "Shots column not found",
        interpretation="Şut hacmi; kaliteyi tek başına garanti etmez."
    ))
    out.append(MetricObject(
        name="xG",
        value=None if xg is None else float(xg),
        status="OK" if xg is not None else "UNKNOWN",
        evidence=f"Match-stats column: {xg_col}" if xg_col else "xG column not found",
        interpretation="Şut kalitesine dair olasılıksal okuma; model bağımlıdır."
    ))
    out.append(MetricObject(
        name="SoT",
        value=None if sot is None else float(sot),
        status="OK" if sot is not None else "UNKNOWN",
        evidence=f"Match-stats column: {sot_col}" if sot_col else "SoT column not found",
        interpretation="Kaleyi bulan şut; bitiriciliği tek başına açıklamaz."
    ))
    return out
