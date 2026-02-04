import os
import pandas as pd

CORE = "data/processed/city_gs_events_core.csv"
OUT = "artifacts/registry/city_gs_action_labels.csv"

def main():
    df = pd.read_csv(CORE)
    df = df.dropna(subset=["team_name"]).copy()

    # basic registry
    g = (df.groupby("action_label")
           .agg(
               count=("event_id","count"),
               teams=("team_name", lambda x: ", ".join(sorted(set([t for t in x.dropna().unique().tolist()])))),
               sample_code=("event_code_raw", lambda x: x.dropna().astype(str).head(1).tolist()[0] if len(x.dropna()) else ""),
               sample_action=("action_raw", lambda x: x.dropna().astype(str).head(1).tolist()[0] if len(x.dropna()) else ""),
           )
           .reset_index()
        )

    # heuristic category tagging (lite)
    def cat(label: str):
        if not isinstance(label, str):
            return "other"
        l = label.lower()
        if "pas" in l or "pass" in l:
            return "pass"
        if "shot" in l or "şut" in l or "goal" in l or "gol" in l:
            return "shot"
        if "cross" in l or "orta" in l:
            return "cross"
        if "tackle" in l or "müdahale" in l:
            return "tackle"
        if "interception" in l or "araya" in l:
            return "interception"
        if "foul" in l or "faul" in l:
            return "foul"
        if "duel" in l or "ikili" in l:
            return "duel"
        if "corner" in l or "korner" in l or "set-piece" in l:
            return "set_piece"
        if "clearance" in l or "uzaklaştır" in l:
            return "clearance"
        if "save" in l or "kurtar" in l:
            return "keeper"
        return "other"

    g["category"] = g["action_label"].apply(cat)

    g = g.sort_values(["count","category","action_label"], ascending=[False, True, True]).reset_index(drop=True)
    g.to_csv(OUT, index=False)

    print("[registry] out:", OUT)
    print("[registry] unique_labels:", g.shape[0])
    print("[registry] top10:")
    print(g.head(10)[["action_label","category","count"]].to_string(index=False))

if __name__ == "__main__":
    main()
