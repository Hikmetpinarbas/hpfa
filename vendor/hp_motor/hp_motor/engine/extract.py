from __future__ import annotations
import pandas as pd
from hp_motor.metrics.metric_object import MetricObject
from hp_motor.metrics.registry import MetricRegistry
from hp_motor.engine.entropy import action_entropy

def _count_actions_containing(df: pd.DataFrame, keywords: list[str]):
    col = "action" if "action" in df.columns else ("Action" if "Action" in df.columns else None)
    if not col:
        return None
    s = df[col].astype(str).str.lower()
    mask = False
    for k in keywords:
        mask = mask | s.str.contains(k, na=False)
    return int(mask.sum())

def _filter_team(df: pd.DataFrame, team_name: str) -> pd.DataFrame:
    col = "team" if "team" in df.columns else ("Team" if "Team" in df.columns else None)
    if not col:
        return df

    t = team_name.lower()
    return df[df[col].astype(str).str.lower().str.contains(t, na=False)]

def extract_team_metrics(df: pd.DataFrame, team_name: str) -> MetricRegistry:
    reg = MetricRegistry()

    tdf = _filter_team(df, team_name)

    # --- SAFETY CHECK ---
    reg.add(MetricObject(
        name="Rows_After_Team_Filter",
        value=len(tdf),
        status="OK",
        evidence="Row count after fuzzy team match",
        interpretation="Takım filtresinin gerçekten satır yakalayıp yakalamadığını gösterir."
    ))

    # --- SHOTS ---
    reg.add(MetricObject(
        name="Shots",
        value=None,
        status="UNKNOWN",
        evidence="Event schema has no explicit shot action",
        interpretation="Bu veri setinde doğrudan şut aksiyonu yok."
    ))

    # --- SHOT-RELATED ATTACKING INVOLVEMENT ---
    shot_related = _count_actions_containing(
        tdf,
        keywords=[
            "with shots",
            "ceza sahasına",
            "into the box"
        ]
    )

    reg.add(MetricObject(
        name="Shot_Related_Attacking_Involvement",
        value=shot_related,
        status="PROXY" if shot_related is not None else "UNKNOWN",
        evidence="Event actions containing: with shots / ceza sahasına / into the box",
        interpretation=(
            "Şutla sonuçlanan veya şut ihtimali barındıran hücumlara katılımı gösteren PROXY metriktir. "
            "Gerçek şut sayısı değildir."
        )
    ))

    # --- ACTION ENTROPY (Shannon) ---
    ent = action_entropy(tdf)
    reg.add(MetricObject(
        name="Action_Entropy",
        value=ent,
        status="OK" if ent is not None else "UNKNOWN",
        evidence="Shannon entropy over action distribution",
        interpretation="Aksiyon çeşitliliği üzerinden belirsizlik düzeyi (nedensel iddia içermez)."
    ))

    # --- TOTAL ACTIONS ---
    reg.add(MetricObject(
        name="Total_Actions",
        value=len(tdf),
        status="OK",
        evidence="Row count after team filter",
        interpretation="Takımın toplam aksiyon hacmini gösterir."
    ))

    return reg
