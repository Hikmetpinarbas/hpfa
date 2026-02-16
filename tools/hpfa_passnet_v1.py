#!/usr/bin/env python3
import os, sys, json, math
from collections import defaultdict, Counter

PASS_OK = {"Paslar adresi bulanlar"}

def load_jsonl(path):
    out=[]
    with open(path,"r",encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try: out.append(json.loads(line))
            except: pass
    return out

def s(x): return (x or "").strip()

def tsec(x):
    try: return float(x)
    except: return None

def safe_xy(r):
    try:
        x=r.get("x"); y=r.get("y")
        if x is None or y is None: return None
        x=float(x); y=float(y)
        if math.isnan(x) or math.isnan(y): return None
        return x,y
    except: return None

def team_of(r):
    return s(r.get("team_raw") or r.get("team") or "UNKNOWN_TEAM")

def action_of(r):
    return s(r.get("action") or "")

def player_of(r):
    code=s(r.get("code") or "")
    if not code: return None
    left=code.split(" - ")[0].strip()
    if ". " in left:
        left=left.split(". ",1)[1].strip()
    return left or None

def ensure_mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt

def save(plt, outdir, name, dpi=280):
    p=os.path.join(outdir,name)
    plt.tight_layout()
    plt.savefig(p, dpi=dpi)
    plt.close()
    return name

def write_index(outdir, items):
    p=os.path.join(outdir,"index.html")
    with open(p,"w",encoding="utf-8") as f:
        f.write('<!doctype html><meta charset="utf-8">')
        f.write('<h2>HPFA passnet_v1 — E2 sequence proxy</h2>')
        f.write('<p><b>Evidence:</b> E2. Receiver inferred from next same-team PASS_OK within 8s. Not ground-truth tracking.</p>')
        f.write('<ul>')
        for it in items:
            f.write(f'<li><div style="margin:14px 0;"><div><b>{it["title"]}</b></div>'
                    f'<img src="{it["file"]}" style="max-width:100%;"></div></li>')
        f.write('</ul>')
    return p

def main():
    if len(sys.argv)!=3:
        print("USAGE: hpfa_passnet_v1.py <match_out_dir> <report_out_dir>")
        sys.exit(2)

    match_out=sys.argv[1]
    outdir=sys.argv[2]
    os.makedirs(outdir, exist_ok=True)

    src=os.path.join(match_out,"canonical_outfield.jsonl")
    if not os.path.exists(src):
        raise SystemExit(f"ERROR missing: {src}")

    ev=load_jsonl(src)
    if not ev:
        raise SystemExit("ERROR: canonical_outfield empty")

    plt=ensure_mpl()

    # split by team
    teams=sorted({team_of(r) for r in ev})
    by_team=defaultdict(list)
    for r in ev:
        by_team[team_of(r)].append(r)

    items=[]

    for t in teams:
        rows=by_team[t]
        rows_sorted=sorted(
            [(tsec(r.get("t_start")) or 0.0, r) for r in rows],
            key=lambda z:z[0]
        )

        # avg positions per player (using all events with xy)
        pos_sum=defaultdict(lambda: [0.0,0.0,0])  # x,y,n
        touches=Counter()

        for tt,r in rows_sorted:
            p=player_of(r)
            xy=safe_xy(r)
            if not p: continue
            touches[p]+=1
            if xy:
                pos_sum[p][0]+=xy[0]
                pos_sum[p][1]+=xy[1]
                pos_sum[p][2]+=1

        # compute avg pos only where we have coordinates
        avg_pos={}
        for p,(sx,sy,n) in pos_sum.items():
            if n>0:
                avg_pos[p]=(sx/n, sy/n)

        # build edges from PASS_OK sequence proxy
        passes=[(tt,r) for tt,r in rows_sorted if action_of(r) in PASS_OK and player_of(r)]
        edges=Counter()
        prog_sum=defaultdict(float)  # (u,v)->sum dx
        prog_n=defaultdict(int)

        for i in range(len(passes)-1):
            t1,r1=passes[i]
            t2,r2=passes[i+1]
            if (t2-t1) < 0 or (t2-t1) > 8:
                continue
            u=player_of(r1); v=player_of(r2)
            if not u or not v or u==v:
                continue
            edges[(u,v)] += 1

            xy1=safe_xy(r1); xy2=safe_xy(r2)
            if xy1 and xy2:
                dx=xy2[0]-xy1[0]
                prog_sum[(u,v)] += dx
                prog_n[(u,v)] += 1

        # choose top players to keep graph readable
        top_players=[p for p,_ in touches.most_common(11)]
        top_set=set(top_players)

        # --- FIG 1: Average Positions + involvement ---
        plt.figure(figsize=(10,6))
        xs=[]; ys=[]; ss=[]; labs=[]
        for p in top_players:
            if p not in avg_pos: continue
            x,y=avg_pos[p]
            xs.append(x); ys.append(y)
            ss.append(40 + 6*touches[p])
            labs.append(p)
        plt.scatter(xs, ys, s=ss, alpha=0.75)
        for x,y,p in zip(xs,ys,labs):
            plt.text(x, y, p, fontsize=8, ha="center", va="center")
        plt.title(f"E2 — Avg Positions (proxy) + involvement — {t}")
        plt.xlabel("x"); plt.ylabel("y")
        fn=save(plt, outdir, f"01_avg_positions__{t.replace(' ','_')}.png")
        items.append({"title":f"Avg positions + involvement — {t}", "file":fn})

        # --- FIG 2: Passing Network (sequence proxy) ---
        # Node positions = avg_pos. Edge width = count. Edge color = mean dx (progressive)
        import numpy as np
        from matplotlib import cm

        # collect edges among top players
        E=[((u,v),w) for (u,v),w in edges.items() if u in top_set and v in top_set and u in avg_pos and v in avg_pos]
        if E:
            maxw=max(w for _,w in E)
            # compute progressive mean
            prog_mean={}
            for (u,v),w in E:
                n=prog_n.get((u,v),0)
                prog_mean[(u,v)] = (prog_sum.get((u,v),0.0)/n) if n>0 else 0.0

            # normalize colors by prog_mean range
            vals=[prog_mean[k] for k,_ in E]
            vmin=min(vals); vmax=max(vals)
            if abs(vmax-vmin) < 1e-9:
                vmin, vmax = vmin-1.0, vmax+1.0

            plt.figure(figsize=(10,6))
            # draw edges
            for (u,v),w in E:
                x1,y1=avg_pos[u]; x2,y2=avg_pos[v]
                lw=0.6 + 3.6*(w/maxw)
                pm=prog_mean[(u,v)]
                c=cm.coolwarm((pm - vmin)/(vmax - vmin))
                plt.plot([x1,x2],[y1,y2], linewidth=lw, color=c, alpha=0.75)

            # draw nodes
            for p in top_players:
                if p not in avg_pos: continue
                x,y=avg_pos[p]
                plt.scatter([x],[y], s=60+5*touches[p], alpha=0.9)
                plt.text(x, y, p, fontsize=8, ha="center", va="center")

            plt.title(f"E2 — Pass Network (sequence proxy). Edge color=mean Δx, width=count — {t}")
            plt.xlabel("x"); plt.ylabel("y")
            fn=save(plt, outdir, f"02_pass_network__{t.replace(' ','_')}.png")
            items.append({"title":f"Pass network (Δx color, count width) — {t}", "file":fn})

    idx=write_index(outdir, items)
    print("OK ✅ passnet_v1 built")
    print("OUT:", outdir)
    print("INDEX:", idx)

if __name__=="__main__":
    main()
