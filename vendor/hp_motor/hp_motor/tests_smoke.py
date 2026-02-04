from __future__ import annotations
import sys
import pandas as pd

FILE = sys.argv[1]
TEAM1 = sys.argv[2]
TEAM2 = sys.argv[3]

from hp_motor.ingest.loader import load_table
from hp_motor.engine.extract import extract_team_metrics
from hp_motor.integrity.popper import PopperGate

df = load_table(FILE)
popper = PopperGate.check(df)
assert popper["status"] != "HARD_BLOCK", popper

r1 = extract_team_metrics(df, TEAM1).all()
r2 = extract_team_metrics(df, TEAM2).all()

def get(metric_list, name):
    for m in metric_list:
        if m.name == name:
            return m
    return None

# Team filter satır yakalamalı
assert get(r1, "Rows_After_Team_Filter").value > 0
assert get(r2, "Rows_After_Team_Filter").value > 0

# Total actions tutarlı
assert get(r1, "Total_Actions").value == get(r1, "Rows_After_Team_Filter").value
assert get(r2, "Total_Actions").value == get(r2, "Rows_After_Team_Filter").value

# Entropy ya OK ya UNKNOWN (event boş değilse OK bekleriz)
e1 = get(r1, "Action_Entropy")
e2 = get(r2, "Action_Entropy")
assert e1 is not None and e2 is not None
assert e1.status in ("OK","UNKNOWN")
assert e2.status in ("OK","UNKNOWN")

print("SMOKE OK")
