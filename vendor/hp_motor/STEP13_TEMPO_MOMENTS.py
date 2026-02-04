#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""STEP13_TEMPO_MOMENTS.py
Tempo+volatility over time axis. OFF if no time axis (NO-GUESSING).
Outputs: out/tempo_series.csv, out/tempo_segments.csv, optional out/tempo.png
"""
import argparse, csv, json, os, sys
from statistics import pstdev

VERSION = "STEP13_TEMPO_MOMENTS v0.1"

def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def load_phase_timeline(mp):
    p = os.path.join(mp, "out", "phase_timeline.csv")
    if not os.path.exists(p): return None, f"missing required input: {p}"
    rows=[]
    with open(p, "r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f): rows.append(row)
    return rows, None

def to_float(x):
    try:
        s=str(x).strip()
        if s=="": return None
        return float(s)
    except: return None

def to_int(x):
    try:
        s=str(x).strip()
        if s=="": return None
        return int(float(s))
    except: return None

def extract_time_sec(row):
    t = to_float(row.get("t_game_sec",""))
    if t is not None: return t
    m = to_int(row.get("minute","")); s = to_int(row.get("second",""))
    if m is not None and s is not None: return float(m*60+s)
    return None

def quantile(xs, q):
    if not xs: return None
    xs=sorted(xs)
    if q<=0: return xs[0]
    if q>=1: return xs[-1]
    idx=(len(xs)-1)*q
    lo=int(idx); hi=min(lo+1,len(xs)-1)
    frac=idx-lo
    return xs[lo]*(1-frac)+xs[hi]*frac

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--match-pack", required=True)
    ap.add_argument("--window-sec", type=int, default=60)
    ap.add_argument("--step-sec", type=int, default=10)
    ap.add_argument("--emit-png", action="store_true")
    args=ap.parse_args()

    mp=args.match_pack
    out_dir=os.path.join(mp,"out")
    os.makedirs(out_dir, exist_ok=True)
    health_path=os.path.join(out_dir,"module_health.json")
    health=read_json(health_path) if os.path.exists(health_path) else {"version":VERSION,"modules":{}}

    rows, err = load_phase_timeline(mp)
    if err:
        health["modules"]["tempo"]={"status":"STOP","reasons":[err]}
        write_json(health_path, health)
        print(f"STOP: {err}"); sys.exit(2)

    times=[extract_time_sec(r) for r in rows]
    if all(t is None for t in times):
        health["modules"]["tempo"]={"status":"OFF","reasons":["no_time_axis: need t_game_sec or (minute+second)"]}
        write_json(health_path, health)
        with open(os.path.join(out_dir,"tempo_segments.csv"),"w",encoding="utf-8",newline="") as f:
            w=csv.DictWriter(f, fieldnames=["status","reason"]); w.writeheader()
            w.writerow({"status":"OFF","reason":"no_time_axis"})
        print("OFF: tempo (no_time_axis)."); sys.exit(0)

    stream=[]
    for r,t in zip(rows,times):
        if t is None: continue
        stream.append((t, int(r.get("seq_idx","0") or 0)))
    stream.sort()
    st=[x[0] for x in stream]
    tmin,tmax=st[0],st[-1]
    window=float(args.window_sec); step=float(args.step_sec)

    def count_in_window(t0,t1):
        c=0
        for tt in st:
            if tt<t0: continue
            if tt>t1: break
            c+=1
        return c

    series=[]
    tempo=[]
    t=tmin
    while t<=tmax:
        t0=max(tmin,t-window); t1=t
        c=count_in_window(t0,t1)
        val=60.0*c/max(1.0,(t1-t0))
        tempo.append(val)
        series.append({"t_sec":round(t,3),"window_sec":int(window),"events_per_min":round(val,3)})
        t+=step

    K=max(5,int(window/max(1.0,step)))
    for i in range(len(series)):
        lo=max(0,i-K+1)
        chunk=tempo[lo:i+1]
        vol=pstdev(chunk) if len(chunk)>=2 else 0.0
        series[i]["volatility"]=round(vol,3)

    p33=quantile(tempo,0.33); p66=quantile(tempo,0.66); p90=quantile(tempo,0.90)
    v90=quantile([s["volatility"] for s in series],0.90)

    def regime(v):
        if v<p33: return "LOW"
        if v<p66: return "MID"
        return "HIGH"

    for s in series:
        s["regime"]=regime(s["events_per_min"])
        s["kaos_flag"]="1" if (s["events_per_min"]>=p90 and s["volatility"]>=v90) else "0"

    segs=[]
    cur=None
    for s in series:
        if cur is None:
            cur={"start_t":s["t_sec"],"end_t":s["t_sec"],"regime":s["regime"],"kaos_hits":int(s["kaos_flag"])}
        elif s["regime"]==cur["regime"]:
            cur["end_t"]=s["t_sec"]; cur["kaos_hits"]+=int(s["kaos_flag"])
        else:
            segs.append(cur); cur={"start_t":s["t_sec"],"end_t":s["t_sec"],"regime":s["regime"],"kaos_hits":int(s["kaos_flag"])}
    if cur: segs.append(cur)

    with open(os.path.join(out_dir,"tempo_series.csv"),"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f, fieldnames=list(series[0].keys()))
        w.writeheader()
        for s in series: w.writerow(s)

    with open(os.path.join(out_dir,"tempo_segments.csv"),"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f, fieldnames=["start_t","end_t","regime","kaos_hits"])
        w.writeheader()
        for s in segs: w.writerow(s)

        # Optional PNG - try but never fail the module
    if args.emit_png:
        try:
            import matplotlib.pyplot as plt
            xs=[s["t_sec"] for s in series]; ys=[s["events_per_min"] for s in series]
            plt.figure(); plt.plot(xs,ys)
            plt.xlabel("t_sec"); plt.ylabel("events_per_min"); plt.title("Tempo (rolling)")
            plt.savefig(os.path.join(out_dir,"tempo.png"), dpi=140, bbox_inches="tight")
            plt.close()
        except Exception as e:
            health["modules"]["tempo_png"]={"status":"DEGRADED","reasons":[f"png_skipped: {e}"]}

    health["modules"]["tempo"]={"status":"OK","reasons":[],
                                "notes":{"window_sec":args.window_sec,"step_sec":args.step_sec,
                                         "regime_thresholds":{"p33":p33,"p66":p66,"p90":p90,"vol_p90":v90},
                                         "no_guessing":True}}
    write_json(health_path, health)
    print("OK: STEP13 outputs written.")
if __name__=="__main__":
    main()
