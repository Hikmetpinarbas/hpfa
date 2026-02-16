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

def player_of(r):
  code=s(r.get("code") or "")
  if not code: return None
  left=code.split(" - ")[0].strip()
  if ". " in left: left=left.split(". ",1)[1].strip()
  return left or None

def team_of(r):
  return s(r.get("team_raw") or r.get("team") or "UNKNOWN_TEAM")

def action_of(r):
  return s(r.get("action") or "")

def half_of(r):
  try:
    h=r.get("half")
    return int(h) if h is not None else None
  except:
    return None

def safe_xy(r):
  try:
    x=r.get("x"); y=r.get("y")
    if x is None or y is None: return None
    x=float(x); y=float(y)
    if math.isnan(x) or math.isnan(y): return None
    return x,y
  except:
    return None

def norm_xy_event(r, x, y):
  # already 105x68 in your data; keep it strict anyway
  x = max(0.0, min(PITCH_L, x))
  y = max(0.0, min(PITCH_W, y))
  # 2nd half flip to align direction
  if half_of(r)==2:
    x = PITCH_L - x
  return x,y

def jitter_for_name(name, scale=0.9):
  h=hashlib.md5(name.encode("utf-8")).hexdigest()
  a=int(h[:8],16)/0xffffffff
  b=int(h[8:16],16)/0xffffffff
  jx=(a-0.5)*2*scale
  jy=(b-0.5)*2*scale
  return jx, jy

def ensure_mpl():
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  return plt

def draw_pitch(plt):
  # outline
  plt.plot([0,105],[0,0],linewidth=1)
  plt.plot([0,105],[68,68],linewidth=1)
  plt.plot([0,0],[0,68],linewidth=1)
  plt.plot([105,105],[0,68],linewidth=1)
  # halfway
  plt.plot([52.5,52.5],[0,68],linewidth=1,alpha=0.6)
  plt.xlim(0,105); plt.ylim(0,68)

def savefig(plt, outdir, name, dpi=320):
  p=os.path.join(outdir,name)
  plt.tight_layout()
  plt.savefig(p,dpi=dpi)
  plt.close()
  return name

def write_index(outdir, items):
  p=os.path.join(outdir,"index.html")
  with open(p,"w",encoding="utf-8") as f:
    f.write('<!doctype html><meta charset="utf-8">')
    f.write('<h2>HPFA positions_v1 — median + jitter (105×68)</h2>')
    f.write('<p><b>Meaning:</b> action-location median (not tracking position). Filtered actions to reduce midfield inflation.</p>')
    f.write('<ul>')
    for it in items:
      f.write(f'<li><div style="margin:14px 0;"><div><b>{it["title"]}</b></div>'
              f'<img src="{it["file"]}" style="max-width:100%;"></div></li>')
    f.write('</ul>')
  return p

def main():
  if len(sys.argv)!=3:
    print("USAGE: hpfa_positions_v1.py <match_out_dir> <report_out_dir>")
    sys.exit(2)

  match_out=sys.argv[1]
  outdir=sys.argv[2]
  os.makedirs(outdir, exist_ok=True)

  src=os.path.join(match_out,"canonical_outfield.jsonl")
  if not os.path.exists(src):
    raise SystemExit(f"ERROR missing: {src}")

  ev=load_jsonl(src)
  plt=ensure_mpl()

  by_team=defaultdict(list)
  for r in ev:
    by_team[team_of(r)].append(r)

  items=[]
  for team, rows in sorted(by_team.items()):
    pts=defaultdict(list)   # player -> list[(x,y)]
    touches=Counter()

    for r in rows:
      p=player_of(r)
      if not p: continue
      a=action_of(r)
      if a and a not in KEEP_ACTIONS: 
        continue
      xy=safe_xy(r)
      if not xy: 
        continue
      x,y = norm_xy_event(r, xy[0], xy[1])
      pts[p].append((x,y))
      touches[p]+=1

    top=[p for p,_ in touches.most_common(11)]
    plt.figure(figsize=(10,6))
    draw_pitch(plt)
    xs=[]; ys=[]; ss=[]
    for p in top:
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

    plt.scatter(xs, ys, s=ss, alpha=0.8)
    plt.title(f"Median action-locations (filtered) — {team}")
    plt.xlabel("x (m)"); plt.ylabel("y (m)")
    fn=savefig(plt, outdir, f"01_positions_median__{team.replace(' ','_')}.png")
    items.append({"title": f"Median positions — {team}", "file": fn})

  idx=write_index(outdir, items)
  print("OK ✅ positions_v1 built")
  print("OUT:", outdir)
  print("INDEX:", idx)

if __name__=="__main__":
  main()
