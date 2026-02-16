#!/usr/bin/env python3
import json, sys, os

IN = sys.argv[1]
OUT = sys.argv[2]

def infer_phase(r):
    a = (r.get("action") or "").lower()
    x = r.get("x")
    if a in ("pass", "shot", "cross"):
        return "F1"
    if a in ("tackle", "interception", "clearance"):
        return "F2"
    if a in ("loss", "miscontrol"):
        return "F3"
    if a in ("recovery", "interception"):
        return "F4"
    if a in ("corner", "freekick"):
        return "F5"
    return "UNK"

os.makedirs(os.path.dirname(OUT), exist_ok=True)

with open(IN, "r", encoding="utf-8") as f, open(OUT, "w", encoding="utf-8") as o:
    for line in f:
        r = json.loads(line)
        r["phase"] = infer_phase(r)
        o.write(json.dumps(r, ensure_ascii=False) + "\n")

print("PHASE TAG DONE ✅")
