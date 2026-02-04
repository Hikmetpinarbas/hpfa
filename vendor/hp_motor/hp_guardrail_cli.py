#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json, argparse, importlib.util
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import pandas as pd

def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod

def ensure_dir(p): os.makedirs(p, exist_ok=True)
def write_json(p,o):
    with open(p,"w",encoding="utf-8") as f:
        json.dump(o,f,ensure_ascii=False,indent=2)

def ratio(a,b): return round(a/b,6) if b else 0.0

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--out",default="artifacts")
    args=ap.parse_args()

    ensure_dir(args.out)

    parsers=load_module("data_parsers-1.py","parsers")
    sot=load_module("hp_single_source_of_truth_v1_fixed.py","sot")
    gates=sot.HP_SYSTEM.default_gates
    required=gates["required_fields"]

    ext=args.input.lower().split(".")[-1]
    if ext=="csv": parser=parsers.CSVEventParser()
    elif ext in ["xls","xlsx"]: parser=parsers.ExcelMetricsParser()
    elif ext=="xml": parser=parsers.XMLEventParser()
    else:
        print("DESTEKLENMEYEN FORMAT"); sys.exit(2)

    df=parser.parse(args.input)
    rows=len(df); cols=set(df.columns)

    coverage={
        "rows":rows,
        "columns":list(cols),
        "team_ratio": ratio(df["team"].notna().sum(),rows) if "team" in cols else 0,
        "action_ratio": ratio(df["action"].notna().sum(),rows) if "action" in cols else 0,
        "x_ratio": ratio(df["x"].notna().sum(),rows) if "x" in cols else 0,
        "y_ratio": ratio(df["y"].notna().sum(),rows) if "y" in cols else 0
    }

    unknown_mask = (df["action_category"]=="OTHER") if "action_category" in cols else df["action"].isna()
    unknown_count=int(unknown_mask.sum())

    questions=[]
    for f in required:
        if f not in cols:
            questions.append({"id":"Q_REQUIRED_FIELDS","field":f})

    if "timestamp" in cols:
        questions.append({"id":"Q_TIME_UNIT"})
    if "x" in cols and "y" in cols:
        questions.append({"id":"Q_PITCH_SCALE"})

    status="OK"
    if unknown_count>0 or questions:
        status="SILENCE"

    write_json(f"{args.out}/coverage.json",coverage)
    write_json(f"{args.out}/questions_to_resolve.json",{"questions":questions})
    write_json(f"{args.out}/qualityguard.json",{
        "status":status,
        "unknown_actions":unknown_count
    })

    if unknown_count>0:
        write_json(f"{args.out}/unknown_actions.json",
            df.loc[unknown_mask,["action","team","timestamp"]].head(50).to_dict("records")
        )

    print("STATUS:",status)
    sys.exit(0 if status=="OK" else 20)

if __name__=="__main__":
    main()
