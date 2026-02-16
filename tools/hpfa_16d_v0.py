#!/usr/bin/env python3
import os, sys, json, math, re
from collections import defaultdict

# ---------------------------
# Config
# ---------------------------
DPI = 260
TOP_N_PLAYERS_PER_TEAM = 8  # radar sayısı (çok olursa ağırlaşır)

# 16D names (canonical)
DIMS = [
  "Technical","Tactical","Physical","Psychological","Sociological","Biomechanical",
  "Cognitive","Nutrition","Sleep","InjuryHistory","CulturalAdaptation","EconomicValue",
  "Communication","Leadership","DecisionMaking","Environmental"
]

# ---------------------------
# Helpers
# ---------------------------
def load_jsonl(path):
    out=[]
    with open(path,"r",encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try: out.append(json.loads(line))
            except: pass
    return out

def s(x): return ("" if x is None else str(x)).strip()

def norm01(val, lo, hi):
    if val is None: return None
    try:
        v=float(val)
    except:
        return None
    if hi <= lo: return 0.0
    if v <= lo: return 0.0
    if v >= hi: return 1.0
    return (v-lo)/(hi-lo)

def pick_col(rec, keys):
    # return first matching key (case-insensitive, stripped)
    lower_map = {k.strip().lower(): k for k in rec.keys()}
    for kk in keys:
        k = kk.strip().lower()
        if k in lower_map:
            return lower_map[k]
    return None

def parse_minutes(rec):
    # try common columns
    for k in ["minutes","minute","min","oynadığı süre","oynadigi sure","süre","sure","time played","playing time"]:
        col = pick_col(rec,[k])
        if col:
            v = rec.get(col)
            try:
                return float(v)
            except:
                pass
    return None

def team_name(rec):
    for k in ["team","takım","takim","club","kulüp","kulup"]:
        col = pick_col(rec,[k])
        if col:
            t = s(rec.get(col))
            if t: return t
    return "UNKNOWN_TEAM"

def player_name(rec):
    for k in ["player","oyuncu","name","isim"]:
        col = pick_col(rec,[k])
        if col:
            p = s(rec.get(col))
            if p: return p
    # fallback: shirt no + name patterns
    for k in rec.keys():
        if "oyuncu" in k.lower() or "player" in k.lower():
            p = s(rec.get(k))
            if p: return p
    return "UNKNOWN_PLAYER"

def to_float(v):
    try:
        if v is None: return None
        if isinstance(v,(int,float)): return float(v)
        vv = str(v).replace("%","").replace(",",".").strip()
        if vv=="": return None
        return float(vv)
    except:
        return None

# ---------------------------
# Dimension model (16D_v0)
# ---------------------------
# NOTE: Only Core+Proxy computed. Others set to None -> plotted as 0.5 with hatch mark.
#
# TECHNICAL: shots, on target, goals, xG, pass accuracy, key passes
# TACTICAL: progressive passes, xA, deep completions (if any), touches/pos (if any)
# PHYSICAL (proxy): minutes + event-rate proxy from outfield events (optional)
# COGNITIVE (proxy): NAS proxy if computed later; here use "Errors/turnovers" inversely if exists
# DECISION-MAKING (proxy): risky actions inversely (errors, dispossessed, losses) + pass% balance
#
# Everything else: placeholder (needs metadata)

def build_dim_scores(player_rec, mins, global_ranges):
    # discover numeric stats
    # we map a set of common column names (TR+EN)
    cols = player_rec.keys()

    def v(keys):
        col = pick_col(player_rec, keys)
        return to_float(player_rec.get(col)) if col else None

    goals = v(["goals","gol"])
    assists = v(["assists","asist"])
    xg = v(["xg","expected goals","beklenen gol"])
    xa = v(["xa","expected assists","beklenen asist"])
    shots = v(["shots","şut","sut"])
    sot = v(["shots on target","isabetli şut","isabetli sut","sot"])
    pass_acc = v(["pass accuracy","pas isabet %","pas isabet","isabet %","pas %"])
    key_pass = v(["key passes","kilit pas"])
    prog_pass = v(["progressive passes","progressive pass","ilerici pas","progresif pas"])
    errors = v(["errors","hatalar","hata"])
    losses = v(["losses","top kaybı","top kaybi","dispossessed","turnovers"])

    # Normalizations (auto ranges from dataset)
    R = global_ranges

    tech_parts = []
    tech_parts.append(norm01(shots, R["shots"][0], R["shots"][1]))
    tech_parts.append(norm01(sot,   R["sot"][0],   R["sot"][1]))
    tech_parts.append(norm01(goals, R["goals"][0], R["goals"][1]))
    tech_parts.append(norm01(xg,    R["xg"][0],    R["xg"][1]))
    tech_parts.append(norm01(pass_acc, R["pass_acc"][0], R["pass_acc"][1]))
    tech_parts.append(norm01(key_pass, R["key_pass"][0], R["key_pass"][1]))
    tech = avg_ignore_none(tech_parts)

    tact_parts = []
    tact_parts.append(norm01(prog_pass, R["prog_pass"][0], R["prog_pass"][1]))
    tact_parts.append(norm01(xa,        R["xa"][0],        R["xa"][1]))
    tact_parts.append(norm01(assists,   R["assists"][0],   R["assists"][1]))
    tact = avg_ignore_none(tact_parts)

    # physical proxy: minutes (scaled) – very rough in v0
    phys = None
    if mins is not None:
        phys = norm01(mins, R["mins"][0], R["mins"][1])

    # cognitive proxy: fewer errors/losses => higher score
    cog = None
    inv_parts = []
    if errors is not None:
        inv_parts.append(1.0 - norm01(errors, R["errors"][0], R["errors"][1]))
    if losses is not None:
        inv_parts.append(1.0 - norm01(losses, R["losses"][0], R["losses"][1]))
    cog = avg_ignore_none(inv_parts)

    # decision making proxy: blend pass_acc + inverse losses/errors
    dec_parts = []
    dec_parts.append(norm01(pass_acc, R["pass_acc"][0], R["pass_acc"][1]))
    if errors is not None: dec_parts.append(1.0 - norm01(errors, R["errors"][0], R["errors"][1]))
    if losses is not None: dec_parts.append(1.0 - norm01(losses, R["losses"][0], R["losses"][1]))
    decision = avg_ignore_none(dec_parts)

    scores = {d: None for d in DIMS}
    scores["Technical"] = tech
    scores["Tactical"] = tact
    scores["Physical"] = phys
    scores["Cognitive"] = cog
    scores["DecisionMaking"] = decision

    # Others remain None (needs metadata)
    return scores

def avg_ignore_none(vals):
    vv=[v for v in vals if v is not None]
    if not vv: return None
    return sum(vv)/len(vv)

def compute_global_ranges(players):
    # compute min/max for normalization across this match sheet
    keys = {
        "shots":["shots","şut","sut"],
        "sot":["shots on target","isabetli şut","isabetli sut","sot"],
        "goals":["goals","gol"],
        "assists":["assists","asist"],
        "xg":["xg","expected goals","beklenen gol"],
        "xa":["xa","expected assists","beklenen asist"],
        "pass_acc":["pass accuracy","pas isabet %","pas isabet","isabet %","pas %"],
        "key_pass":["key passes","kilit pas"],
        "prog_pass":["progressive passes","progressive pass","ilerici pas","progresif pas"],
        "errors":["errors","hatalar","hata"],
        "losses":["losses","top kaybı","top kaybi","dispossessed","turnovers"],
    }
    # init
    rng = {k:[math.inf,-math.inf] for k in keys}
    rng["mins"]=[math.inf,-math.inf]

    for r in players:
        mins = parse_minutes(r)
        if mins is not None:
            rng["mins"][0]=min(rng["mins"][0], mins)
            rng["mins"][1]=max(rng["mins"][1], mins)
        for kk, aliases in keys.items():
            col = pick_col(r, aliases)
            if not col: 
                continue
            v = to_float(r.get(col))
            if v is None: 
                continue
            rng[kk][0]=min(rng[kk][0], v)
            rng[kk][1]=max(rng[kk][1], v)

    # fallback for missing columns
    for k,(lo,hi) in rng.items():
        if lo==math.inf or hi==-math.inf:
            rng[k]=[0.0, 1.0]
        elif hi==lo:
            rng[k]=[lo, lo+1.0]
    return rng

def radar_plot(ax, labels, values, title, placeholder_mask):
    import numpy as np
    N=len(labels)
    angles = np.linspace(0, 2*np.pi, N, endpoint=False).tolist()
    values = values + values[:1]
    angles = angles + angles[:1]

    ax.plot(angles, values, linewidth=2)
    ax.fill(angles, values, alpha=0.15)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_yticklabels([])
    ax.set_ylim(0,1)
    ax.set_title(title, fontsize=10)

    # hatch mark placeholders: draw small red dot ring where placeholder used
    # (no custom colors requested; keep minimal: use marker only)
    for i, is_ph in enumerate(placeholder_mask):
        if is_ph:
            ax.plot([angles[i]],[values[i]], marker="x", markersize=6)

def main():
    if len(sys.argv)!=3:
        print("USAGE: hpfa_16d_v0.py <match_out_dir> <report_out_dir>")
        sys.exit(2)

    match_out=sys.argv[1]
    rep_out=sys.argv[2]
    os.makedirs(rep_out, exist_ok=True)

    # find stats jsonl in match_out
    stats_files=[f for f in os.listdir(match_out) if f.endswith(".jsonl") and f.startswith("stats__")]
    if not stats_files:
        print("ERROR: no stats__*.jsonl in", match_out)
        sys.exit(1)

    # pick the biggest stats file as main (usually players sheet)
    stats_files_sorted=sorted(stats_files, key=lambda fn: os.path.getsize(os.path.join(match_out,fn)), reverse=True)
    stats_path=os.path.join(match_out, stats_files_sorted[0])
    rows=load_jsonl(stats_path)

    # Heuristic: keep rows that look like player rows
    players=[]
    for r in rows:
        p=player_name(r)
        if p!="UNKNOWN_PLAYER":
            players.append(r)
    if len(players)<10:
        # fallback: use all
        players=rows

    # global ranges for normalization
    R=compute_global_ranges(players)

    # team grouping
    by_team=defaultdict(list)
    for r in players:
        by_team[team_name(r)].append(r)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Build per-player radars
    out_png=[]
    for team, plist in by_team.items():
        # compute a simple "overall core score" for ordering
        scored=[]
        for pr in plist:
            mins=parse_minutes(pr)
            scores=build_dim_scores(pr, mins, R)
            core = avg_ignore_none([scores["Technical"],scores["Tactical"],scores["Physical"],scores["Cognitive"],scores["DecisionMaking"]])
            scored.append((core if core is not None else -1.0, pr, scores))
        scored.sort(key=lambda x: x[0], reverse=True)
        scored=scored[:TOP_N_PLAYERS_PER_TEAM]

        for core, pr, scores in scored:
            labels=DIMS
            vals=[]
            placeholder=[]
            for d in labels:
                v=scores.get(d)
                if v is None:
                    vals.append(0.5)     # placeholder
                    placeholder.append(True)
                else:
                    vals.append(float(v))
                    placeholder.append(False)
            fig=plt.figure(figsize=(7.2,7.2))
            ax=plt.subplot(111, polar=True)
            radar_plot(ax, labels, vals, f"16D_v0 Radar — {player_name(pr)} — {team}", placeholder)
            fname=f"16d_player__{team.replace(' ','_')}__{re.sub(r'[^A-Za-z0-9_]+','_',player_name(pr))}.png"
            path=os.path.join(rep_out,fname)
            plt.tight_layout()
            plt.savefig(path, dpi=DPI)
            plt.close()
            out_png.append(fname)

        # Team average radar
        team_scores_acc=defaultdict(list)
        for pr in plist:
            mins=parse_minutes(pr)
            scores=build_dim_scores(pr, mins, R)
            for d,v in scores.items():
                if v is not None:
                    team_scores_acc[d].append(v)

        labels=DIMS
        vals=[]
        placeholder=[]
        for d in labels:
            vv=team_scores_acc.get(d,[])
            if not vv:
                vals.append(0.5); placeholder.append(True)
            else:
                vals.append(sum(vv)/len(vv)); placeholder.append(False)

        fig=plt.figure(figsize=(7.2,7.2))
        ax=plt.subplot(111, polar=True)
        radar_plot(ax, labels, vals, f"16D_v0 Team Average — {team}", placeholder)
        fname=f"16d_team_avg__{team.replace(' ','_')}.png"
        plt.tight_layout()
        plt.savefig(os.path.join(rep_out,fname), dpi=DPI)
        plt.close()
        out_png.append(fname)

    # index.html
    idx=os.path.join(rep_out,"index.html")
    with open(idx,"w",encoding="utf-8") as f:
        f.write('<!doctype html><meta charset="utf-8">')
        f.write('<h2>HPFA 16D_v0 — Radar Dashboard</h2>')
        f.write('<p>X işaretleri: bu maç datasında olmayan boyutlar (placeholder=0.5). Core/Proxy: Technical/Tactical/Physical/Cognitive/DecisionMaking.</p>')
        for fn in out_png:
            f.write(f'<div style="margin:14px 0;"><div><b>{fn}</b></div><img src="{fn}" style="max-width:100%;"></div>')

    print("OK ✅ 16D_v0 built")
    print("stats_source:", os.path.basename(stats_path))
    print("OUTDIR:", rep_out)
    print("INDEX:", idx)

if __name__=="__main__":
    main()
