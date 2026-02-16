#!/usr/bin/env python3
import os, sys, json, math, hashlib
from collections import defaultdict, Counter
import numpy as np

PITCH_L=105.0
PITCH_W=68.0

KEEP_ACTIONS = {
  "Paslar adresi bulanlar",
  "Başarılı İleri Paslar",
  "İsabetli İlerletici Paslar",
  "Top Taşıma",
  "İsabetli Şut",
  "İsabetsiz Şut",
  "Gol",
  "Başarılı driplingler",
  "Başarılı Top Kapma",
  "Geri Kazanılan Toplar",
  "Top Kaybı",
}

META_ACTIONS = {
  "Start of the 1st half","Halftime","Start of the 2nd half","End of the match"
}

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

def team_of(r):
  t = s(r.get("team_raw") or r.get("team") or "")
  if not t: return None
  if t.upper() in {"UNKNOWN_TEAM","UNKNOWN","NULL","NONE"}: return None
  return t

def action_of(r):
  return s(r.get("action") or "")

def half_of(r):
  try:
    h=r.get("half")
    return int(h) if h is not None else None
  except:
    return None

def player_of(r):
  code=s(r.get("code") or "")
  if not code: return None
  left=code.split(" - ")[0].strip()
  if ". " in left: left=left.split(". ",1)[1].strip()
  return left or None

def safe_xy(r):
  try:
    x=r.get("x"); y=r.get("y")
    if x is None or y is None: return None
    x=float(x); y=float(y)
    if math.isnan(x) or math.isnan(y): return None
    # clamp to pitch; your data is 105x68
    x=max(0.0,min(PITCH_L,x))
    y=max(0.0,min(PITCH_W,y))
    return x,y
  except:
    return None

def jitter_for_name(name, scale=1.2):
  h=hashlib.md5(name.encode("utf-8")).hexdigest()
  a=int(h[:8],16)/0xffffffff
  b=int(h[8:16],16)/0xffffffff
  return (a-0.5)*2*scale, (b-0.5)*2*scale

def ensure_mpl():
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  return plt

def draw_pitch(plt):
  plt.plot([0,105],[0,0],linewidth=1)
  plt.plot([0,105],[68,68],linewidth=1)
  plt.plot([0,0],[0,68],linewidth=1)
  plt.plot([105,105],[0,68],linewidth=1)
  plt.plot([52.5,52.5],[0,68],linewidth=1,alpha=0.6)
  plt.xlim(0,105); plt.ylim(0,68)

def savefig(plt, outdir, name, dpi=320):
  p=os.path.join(outdir,name)
  plt.tight_layout()
  plt.savefig(p,dpi=dpi)
  plt.close()
  return name

def write_index(outdir, items, info_lines):
  p=os.path.join(outdir,"index.html")
  with open(p,"w",encoding="utf-8") as f:
    f.write('<!doctype html><meta charset="utf-8">')
    f.write('<h2>HPFA positions_v2_auto — 2-team filter + auto flip</h2>')
    f.write('<ul>')
    for line in info_lines:
      f.write(f'<li>{line}</li>')
    f.write('</ul>')
    f.write('<ul>')
    for it in items:
      f.write(f'<li><div style="margin:14px 0;"><div><b>{it["title"]}</b></div>'
              f'<img src="{it["file"]}" style="max-width:100%;"></div></li>')
    f.write('</ul>')
  return p

def choose_top2_teams(ev):
  c=Counter()
  for r in ev:
    t=team_of(r)
    a=action_of(r)
    if not t: continue
    if a in META_ACTIONS: continue
    c[t]+=1
  return [t for t,_ in c.most_common(2)]

def decide_flip_for_team(rows):
  # If vendor already aligns attack direction, half1 and half2 x-medians will be similar.
  # If vendor uses absolute pitch, teams swap sides: median_x2 ~= 105 - median_x1.
  xs1=[]; xs2=[]
  for r in rows:
    if action_of(r) in META_ACTIONS: continue
    xy=safe_xy(r)
    if not xy: continue
    h=half_of(r)
    if h==1: xs1.append(xy[0])
    elif h==2: xs2.append(xy[0])
  if len(xs1)<50 or len(xs2)<50:
    return False, "insufficient_half_samples"
  m1=float(np.median(xs1))
  m2=float(np.median(xs2))
  # Compare two hypotheses:
  # H0: no flip needed -> distance |m2 - m1|
  # H1: flip needed -> distance |m2 - (105 - m1)|
  d0=abs(m2 - m1)
  d1=abs(m2 - (PITCH_L - m1))
  flip = d1 < d0
  reason=f"m1={m1:.1f}, m2={m2:.1f}, d0={d0:.1f}, d1={d1:.1f}"
  return flip, reason

def norm_xy_team(r, x, y, flip_second_half):
  h=half_of(r)
  if flip_second_half and h==2:
    x = PITCH_L - x
  return x,y

def main():
  if len(sys.argv)!=3:
    print("USAGE: hpfa_positions_v2_auto.py <match_out_dir> <report_out_dir>")
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

  top2=choose_top2_teams(ev)
  if len(top2)!=2:
    raise SystemExit(f"ERROR: expected 2 teams, found: {top2}")

  # filter to top2 teams only
  by_team=defaultdict(list)
  for r in ev:
    t=team_of(r)
    if not t or t not in top2: 
      continue
    by_team[t].append(r)

  # decide flip per team
  flip_cfg={}
  info=[]
  for t, rows in by_team.items():
    flip, reason = decide_flip_for_team(rows)
    flip_cfg[t]=flip
    info.append(f"<b>{t}</b>: flip_second_half={flip} ({reason})")

  plt=ensure_mpl()
  items=[]

  for t in top2:
    rows=by_team[t]

    pts=defaultdict(list)
    touches=Counter()

    for r in rows:
      a=action_of(r)
      if a in META_ACTIONS: 
        continue
      if a and a not in KEEP_ACTIONS:
        continue
      p=player_of(r)
      if not p: 
        continue
      xy=safe_xy(r)
      if not xy: 
        continue
      x,y = norm_xy_team(r, xy[0], xy[1], flip_cfg[t])
      pts[p].append((x,y))
      touches[p]+=1

    top_players=[p for p,_ in touches.most_common(11)]

    plt.figure(figsize=(10,6))
    draw_pitch(plt)

    xs=[]; ys=[]; ss=[]
    for p in top_players:
      arr=pts.get(p,[])
      if len(arr)<3:
        continue
      ax=np.array([q[0] for q in arr]); ay=np.array([q[1] for q in arr])
      x=float(np.median(ax)); y=float(np.median(ay))
      jx,jy=jitter_for_name(p, scale=1.2)
      x2=max(0,min(105,x+jx)); y2=max(0,min(68,y+jy))
      xs.append(x2); ys.append(y2)
      ss.append(50 + 4*min(touches[p],120))
      plt.text(x2, y2, p, fontsize=8, ha="center", va="center")

    plt.scatter(xs, ys, s=ss, alpha=0.82)
    plt.title(f"Median action-locations (2-team + auto-flip) — {t}")
    plt.xlabel("x (m)"); plt.ylabel("y (m)")
    fn=savefig(plt, outdir, f"01_positions_median__{t.replace(' ','_')}.png")
    items.append({"title": f"Median positions — {t}", "file": fn})

  idx=write_index(outdir, items, info)
  print("OK ✅ positions_v2_auto built")
  print("Teams:", top2)
  print("OUT:", outdir)
  print("INDEX:", idx)

if __name__=="__main__":
  main()
