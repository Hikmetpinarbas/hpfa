#!/usr/bin/env python3
import os, sys, json, math
from collections import Counter, defaultdict

KW_SHOT = ("şut", "shot", "vuruş", "kafa vuruş", "volley")
KW_TURNOVER = ("top kayb", "loss", "miscontrol", "bad control", "hata", "turnover")
KW_REGAIN = ("top kazan", "recovery", "interception", "tackle", "ball win", "kapma", "pas arası")
KW_SETPIECE = ("korner", "corner", "freekick", "serbest vuruş", "taç", "throw", "penalt", "penalty")

def s(x): return (x or "").strip().lower()

def load_jsonl(path):
    out=[]
    with open(path,"r",encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try: out.append(json.loads(line))
            except: pass
    return out

def is_kw(text, kws):
    t=s(text)
    return any(k in t for k in kws)

def get_team(rec):
    return (rec.get("team_raw") or rec.get("team") or "").strip() or "UNKNOWN_TEAM"

def get_action_blob(rec):
    a = rec.get("action") or ""
    c = rec.get("code") or ""
    return f"{a} {c}"

def minute_bucket(t):
    try: return int(float(t)//60)
    except: return None

def safe_xy(rec):
    try:
        x,y = rec.get("x"), rec.get("y")
        if x is None or y is None: return None
        x=float(x); y=float(y)
        if math.isnan(x) or math.isnan(y): return None
        return x,y
    except: return None

def classify_phase_proxy(blob):
    if is_kw(blob, KW_SETPIECE): return "F5/F6"
    if is_kw(blob, KW_TURNOVER): return "F3"
    if is_kw(blob, KW_REGAIN): return "F4"
    return "OPEN"

def write_html_index(outdir, pngs):
    path = os.path.join(outdir, "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write('<!doctype html><meta charset="utf-8">')
        f.write('<h2>HPFA report_v2 — rz-gs-20260208</h2>')
        f.write('<p>Not: F1/F2 possession yoksa "OPEN" proxy olarak kalır. F3/F4/F5-6 daha güvenilir.</p>')
        for p in pngs:
            f.write(f'<div style="margin:14px 0;"><div><b>{p}</b></div><img src="{p}" style="max-width:100%;"></div>')
    return path

def main():
    if len(sys.argv)!=3:
        print("USAGE: hpfa_report_v2.py <match_out_dir> <report_out_dir>")
        sys.exit(2)

    match_out=sys.argv[1]
    rep_out=sys.argv[2]
    os.makedirs(rep_out, exist_ok=True)

    outfield_path=os.path.join(match_out,"canonical_outfield.jsonl")
    if not os.path.exists(outfield_path):
        print("ERROR missing:", outfield_path)
        sys.exit(1)

    events=load_jsonl(outfield_path)
    if not events:
        print("ERROR: empty/unreadable canonical_outfield.jsonl")
        sys.exit(1)

    # group
    by_team=defaultdict(list)
    for r in events:
        team=get_team(r)
        by_team[team].append(r)

    # import plotting
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # helpers
    def savefig(name):
        path=os.path.join(rep_out,name)
        plt.tight_layout()
        plt.savefig(path, dpi=170)
        plt.close()
        return name

    pngs=[]

    # 0) team sizes
    teams=sorted(by_team.keys())
    team_sizes={t:len(by_team[t]) for t in teams}

    # 1) Events per minute by team (lines)
    per_min=defaultdict(Counter)
    for t,lst in by_team.items():
        for r in lst:
            m=minute_bucket(r.get("t_start"))
            if m is not None: per_min[t][m]+=1
    plt.figure()
    for t in teams:
        mins=sorted(per_min[t])
        vals=[per_min[t][m] for m in mins]
        plt.plot(mins, vals, label=t)
    plt.title("Event intensity (events/min) — by team")
    plt.xlabel("Minute"); plt.ylabel("Events")
    plt.legend(fontsize=7)
    pngs.append(savefig("06_events_per_minute_by_team.png"))

    # 2) Cumulative events by team
    plt.figure()
    for t in teams:
        mins=range(0, max(per_min[t].keys() or [0])+1)
        cum=0
        xs=[]; ys=[]
        for m in mins:
            cum += per_min[t].get(m,0)
            xs.append(m); ys.append(cum)
        plt.plot(xs, ys, label=t)
    plt.title("Cumulative events — by team")
    plt.xlabel("Minute"); plt.ylabel("Cumulative events")
    plt.legend(fontsize=7)
    pngs.append(savefig("07_cumulative_events_by_team.png"))

    # 3) Phase proxy distribution by team
    phase_ct=defaultdict(Counter)
    for t,lst in by_team.items():
        for r in lst:
            ph=classify_phase_proxy(get_action_blob(r))
            phase_ct[t][ph]+=1
    phases=sorted({p for t in teams for p in phase_ct[t].keys()})
    plt.figure()
    x=range(len(phases))
    width=0.8/max(1,len(teams))
    for i,t in enumerate(teams):
        vals=[phase_ct[t].get(p,0) for p in phases]
        xs=[xi + i*width for xi in x]
        plt.bar(xs, vals, width=width, label=t)
    plt.title("Phase proxy counts (F3/F4/F5F6/OPEN) — by team")
    plt.xticks([xi + width*(len(teams)-1)/2 for xi in x], phases, rotation=25, ha="right")
    plt.legend(fontsize=7)
    pngs.append(savefig("08_phase_proxy_by_team.png"))

    # 4) Top actions by team (top 15)
    def action_label(r):
        a=s(r.get("action") or "")
        return a if a else "unknown"
    top_actions=defaultdict(Counter)
    for t,lst in by_team.items():
        for r in lst:
            top_actions[t][action_label(r)]+=1

    for t in teams:
        items=top_actions[t].most_common(15)
        labs=[k for k,_ in items][::-1]
        vals=[v for _,v in items][::-1]
        plt.figure()
        plt.barh(labs, vals)
        plt.title(f"Top actions (15) — {t}")
        plt.xlabel("count")
        pngs.append(savefig(f"09_top_actions__{t.replace(' ','_')}.png"))

    # 5) Shot heatmap (2D hist) — all + by team
    def plot_hist2d(title, pts, fname, bins=30):
        plt.figure()
        if pts:
            xs=[x for x,_ in pts]; ys=[y for _,y in pts]
            plt.hist2d(xs, ys, bins=bins)
        plt.title(title); plt.xlabel("x"); plt.ylabel("y")
        return savefig(fname)

    shots_all=[]
    tov_all=[]
    reg_all=[]
    for r in events:
        blob=get_action_blob(r)
        xy=safe_xy(r)
        if not xy: continue
        if is_kw(blob, KW_SHOT): shots_all.append(xy)
        if is_kw(blob, KW_TURNOVER): tov_all.append(xy)
        if is_kw(blob, KW_REGAIN): reg_all.append(xy)

    pngs.append(plot_hist2d("Shot locations — heatmap (all)", shots_all, "10_shots_heatmap_all.png"))
    pngs.append(plot_hist2d("Turnover locations — heatmap (all)", tov_all, "11_turnovers_heatmap_all.png"))
    pngs.append(plot_hist2d("Regain locations — heatmap (all)", reg_all, "12_regains_heatmap_all.png"))

    # by team heatmaps (shots/turnovers)
    for t,lst in by_team.items():
        spts=[]; tpts=[]
        for r in lst:
            blob=get_action_blob(r)
            xy=safe_xy(r)
            if not xy: continue
            if is_kw(blob, KW_SHOT): spts.append(xy)
            if is_kw(blob, KW_TURNOVER): tpts.append(xy)
        pngs.append(plot_hist2d(f"Shots heatmap — {t}", spts, f"13_shots_heatmap__{t.replace(' ','_')}.png"))
        pngs.append(plot_hist2d(f"Turnovers heatmap — {t}", tpts, f"14_turnovers_heatmap__{t.replace(' ','_')}.png"))

    # 6) Regain Δt (turnover -> next regain, same team <=30s) by team
    regain_dt_by_team=defaultdict(list)
    for t,lst in by_team.items():
        # collect regain times
        regain_times=[]
        for r in lst:
            if r.get("t_start") is None: continue
            blob=get_action_blob(r)
            if is_kw(blob, KW_REGAIN):
                try: regain_times.append(float(r["t_start"]))
                except: pass
        regain_times.sort()
        if not regain_times: 
            continue
        # turnover times
        for r in lst:
            if r.get("t_start") is None: continue
            blob=get_action_blob(r)
            if not is_kw(blob, KW_TURNOVER): 
                continue
            try: t0=float(r["t_start"])
            except: 
                continue
            t1=None
            for rt in regain_times:
                if rt>=t0:
                    t1=rt; break
            if t1 is None: 
                continue
            dt=t1-t0
            if 0<=dt<=30:
                regain_dt_by_team[t].append(dt)

    for t in teams:
        plt.figure()
        vals=regain_dt_by_team.get(t,[])
        if vals:
            plt.hist(vals, bins=25)
        plt.title(f"Regain Δt (<=30s) — {t}")
        plt.xlabel("seconds"); plt.ylabel("count")
        pngs.append(savefig(f"15_regain_dt_hist__{t.replace(' ','_')}.png"))

    # 7) Basic tempo proxy: gaps between events (all)
    gaps=[]
    ev_sorted=sorted([r for r in events if r.get("t_start") is not None], key=lambda r: float(r["t_start"]))
    prev=None
    for r in ev_sorted:
        try: t=float(r["t_start"])
        except: continue
        if prev is not None:
            dt=t-prev
            if 0<=dt<=20:
                gaps.append(dt)
        prev=t
    plt.figure()
    if gaps:
        plt.hist(gaps, bins=40)
    plt.title("Tempo proxy: Δt between consecutive events (<=20s)")
    plt.xlabel("seconds"); plt.ylabel("count")
    pngs.append(savefig("16_tempo_gap_hist.png"))

    # write index.html
    idx = write_html_index(rep_out, pngs)
    print("REPORT V2 OK ✅")
    print("OUTDIR:", rep_out)
    print("INDEX:", idx)
    print("PNGS:", len(pngs))

if __name__=="__main__":
    main()
