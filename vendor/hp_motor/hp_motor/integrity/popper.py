from __future__ import annotations
import pandas as pd

class PopperGate:
    """
    HARD_BLOCK sadece integrity kırığında:
    - df boş
    - gerekli minimum şema yok
    """

    @staticmethod
    def check(df: pd.DataFrame) -> dict:
        if df is None or df.empty:
            return {"status": "HARD_BLOCK", "reason": "Empty table / no rows."}

        cols = set(map(str, df.columns))

        # Match-stats şeması (varsa)
        if ("Shots" in cols) or ("xG" in cols):
            return {"status": "DEGRADED", "reason": "Match-stats schema detected (Shots/xG present partially/fully)."}

        # Event şeması (senin CSV)
        event_min = {"team", "action"}
        if event_min.issubset(cols):
            return {"status": "DEGRADED", "reason": "Event schema detected (team/action present). Shots/xG may be unavailable."}

        # Bazı sağlayıcılar 'Team' 'Action' yazar
        event_min_alt = {"Team", "Action"}
        if event_min_alt.issubset(cols):
            return {"status": "DEGRADED", "reason": "Event schema detected (Team/Action present). Shots/xG may be unavailable."}

        return {"status": "HARD_BLOCK", "reason": f"Unrecognized schema. Columns: {sorted(list(cols))[:40]} ..."}
