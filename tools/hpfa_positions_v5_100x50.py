import os, json, math, argparse
from collections import defaultdict, Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

PITCH_W_105=105.0
PITCH_H_68=68.0
PITCH_W_100=100.0
PITCH_H_50=50.0

# Positions proxy: actor-location kabul edilebilir aksiyonlar
ALLOW_ACTIONS = {
    "Top Taşıma",
    "Geri Kazanılan Toplar",
    "Rakip sahada geri kazanılan toplar",
    "Başarılı İkili Mücadeleler",
    "Başarısız İkili Mücadeleler",
    "Başarılı driplingler",
    "Başarısız Driplingler",
    "Başarılı Top Kapma",
    "Başarısız Top Kapma",
    "İsabetli Şut",
    "İsabetsiz Şut",
    "Gol",
    "Faul",
    "Yapılan Fauller",
    "Uzaklaştırma",
}

# Paslar (destination şüphesi) positions için YASAK
BAN_ACTIONS = {
    "Paslar adresi bulanlar",
    "Başarılı İleri Paslar",
    "Başarısız İleri Paslar",
    "İsabetli İlerletici Paslar",
    "Başarısız İlerletici Paslar",
    "Uzun paslar",
    "Başarısız Uzun Toplar",
    "İsabetsiz Ortalar",
    "İsabetli Ortalar",
    "Ceza sahasına / İsabetli",
    "Başarısız Ceza Sahasına Paslar",
    "İsabetli Kilit Paslar",
    "Başarısız Kilit Paslar",
}

def safe_float(x):
    try:
        v=float(x)
        if math.isnan(v): return None
        return v
    except: return None

def s(x): return (x or "").strip()

def player_of(code: str):
    code = s(code)
    if not code: return None
    left = code.split(" - ")[0].strip()
    if ". " in left:
        left = left.split(". ",1)[1].strip()
    return left or None

def to_100x50(x105,y68):
    return x105*(PITCH_W_100/PITCH_W_105), y68*(PITCH_H_50/PITCH_H_68)

def flip_x(x, width):
    return (width - x) if x is not None else None

def draw_pitch(ax, w=100, h=50):
    # minimalist pitch: dış çizgiler + orta çizgi + orta nokta
    ax.plot([0,w,w,0,0],[0,0,h,h,0])
    ax.plot([w/2,w/2],[0,h])
    ax.scatter([w/2],[h/2], s=8)
    ax.set_xlim(0,w); ax.set_ylim(0,h)
    ax.set_aspect('equal', adjustable='box')
    ax.axis("off")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--match-id", required=True)
    ap.add_argument("--canon", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--flip-second-half", action="store_true")
    args=ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    rows=[]
    with open(args.canon,"r",encoding="utf-8") as f:
        for line in f:
            line=line.strip()
            if not line: continue
            try: rows.append(json.loads(line))
            except: pass

    # filter: drop UNKNOWN team + banned actions
    keep=[]
    dropped_unknown=0
    dropped_ban=0
    dropped_notallow=0
    for r in rows:
        team=s(r.get("team_raw"))
        if (not team) or team.upper().startswith("UNKNOWN"):
            dropped_unknown += 1
            continue
        a=s(r.get("action"))
        if a in BAN_ACTIONS:
            dropped_ban += 1
            continue
        if a not in ALLOW_ACTIONS:
            dropped_notallow += 1
            continue
        x=safe_float(r.get("x")); y=safe_float(r.get("y"))
        if x is None or y is None: 
            continue
        half=r.get("half")
        x100,y50 = to_100x50(x,y)

        if args.flip_second_half and int(half or 1)==2:
            x100 = flip_x(x100, PITCH_W_100)

        p=player_of(r.get("code") or "")
        if not p: 
            continue
        keep.append((team,p,x100,y50))

    teams=sorted(set(t for t,_,_,_ in keep))
    # plot: per team scatter of median positions (player-level)
    for team in teams:
        pts=defaultdict(list)
        for t,p,x,y in keep:
            if t!=team: continue
            pts[p].append((x,y))
        med={}
        for p,xy in pts.items():
            xs=sorted(v[0] for v in xy); ys=sorted(v[1] for v in xy)
            n=len(xs)
            mx=xs[n//2] if n%2 else 0.5*(xs[n//2-1]+xs[n//2])
            my=ys[n//2] if n%2 else 0.5*(ys[n//2-1]+ys[n//2])
            med[p]=(mx,my,len(xy))

        fig=plt.figure(figsize=(9,5))
        ax=fig.add_subplot(111)
        draw_pitch(ax,100,50)

        xs=[v[0] for v in med.values()]
        ys=[v[1] for v in med.values()]
        ax.scatter(xs,ys, s=40)

        # label top 14 by sample size to avoid clutter
        top=sorted(med.items(), key=lambda kv: kv[1][2], reverse=True)[:14]
        for p,(x,y,n) in top:
            ax.text(x+0.8,y+0.4, p.split(" (")[0], fontsize=7)

        ax.set_title(f"HPFA positions_v5_100x50 — median (actor-location only)\\n{team} | flip_second_half={args.flip_second_half} | dropped_unknown={dropped_unknown} dropped_ban={dropped_ban} dropped_notallow={dropped_notallow}")
        out_png=os.path.join(args.out_dir, f"positions_{team.replace('/','_')}.png")
        fig.savefig(out_png, dpi=160, bbox_inches="tight")
        plt.close(fig)

    # index.html
    html=["<!doctype html><meta charset='utf-8'>",
          f"<h2>HPFA positions_v5_100x50 — {args.match_id}</h2>",
          "<p>Positions = median of actor-location proxy events (NO passes). 100×50. UNKNOWN filtered.</p>",
          "<ul>"]
    for team in teams:
        fn=f"positions_{team.replace('/','_')}.png"
        html.append(f"<li><h3>{team}</h3><img src='{fn}' style='max-width:100%;'></li>")
    html.append("</ul>")
    with open(os.path.join(args.out_dir,"index.html"),"w",encoding="utf-8") as f:
        f.write("\n".join(html))

    # summary json
    with open(os.path.join(args.out_dir,"summary.json"),"w",encoding="utf-8") as f:
        json.dump({
            "match_id": args.match_id,
            "teams": teams,
            "kept_points": len(keep),
            "dropped_unknown": dropped_unknown,
            "dropped_ban_actions": dropped_ban,
            "dropped_not_allowlist": dropped_notallow,
            "notes": "positions computed from actor-location proxy events; passes removed due to destination semantics risk."
        }, f, ensure_ascii=False, indent=2)

    print("OK ✅", args.out_dir)

if __name__=="__main__":
    main()
