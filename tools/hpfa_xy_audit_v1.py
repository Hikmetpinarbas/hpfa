#!/usr/bin/env python3
import os, sys, json, math
from collections import defaultdict

def load_jsonl(p):
    out=[]
    with open(p,"r",encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try: out.append(json.loads(line))
            except: pass
    return out

def s(x): return (x or "").strip()

def player_of(r):
    code=s(r.get("code") or "")
    if not code: return None
    left=code.split(" - ")[0].strip()
    if ". " in left: left=left.split(". ",1)[1].strip()
    return left or None

def xy(r):
    try:
        x=float(r.get("x")); y=float(r.get("y"))
        if math.isnan(x) or math.isnan(y): return None
        return x,y
    except: return None

PASS="Paslar adresi bulanlar"
CARRY="Top Taşıma"
SHOT_OK={"İsabetli Şut","İsabetsiz Şut","Gol"}

def main():
    src=sys.argv[1]
    ev=load_jsonl(src)

    by=defaultdict(lambda: {"pass":[], "carry":[], "shot":[]})
    for r in ev:
        p=player_of(r)
        if not p: continue
        a=s(r.get("action"))
        pt=xy(r)
        if not pt: continue
        if a==PASS: by[p]["pass"].append(pt[0])
        elif a==CARRY: by[p]["carry"].append(pt[0])
        elif a in SHOT_OK: by[p]["shot"].append(pt[0])

    def med(xs):
        xs=sorted(xs)
        if not xs: return None
        n=len(xs)
        return xs[n//2] if n%2==1 else 0.5*(xs[n//2-1]+xs[n//2])

    # Print players where pass median is much higher than carry/shot median
    rows=[]
    for p,d in by.items():
        mp=med(d["pass"]); mc=med(d["carry"]); ms=med(d["shot"])
        if mp is None: continue
        rows.append((p, len(d["pass"]), mp, mc, ms))
    rows.sort(key=lambda z: z[2], reverse=True)

    print("player | n_pass | med_x_pass | med_x_carry | med_x_shot")
    for p,n,mp,mc,ms in rows[:25]:
        print(f"{p} | {n:4d} | {mp:6.1f} | {mc if mc is not None else 'NA':>6} | {ms if ms is not None else 'NA':>6}")

