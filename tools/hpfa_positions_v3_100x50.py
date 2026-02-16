#!/usr/bin/env python3
import os, sys, json, math, hashlib
from collections import defaultdict, Counter
import numpy as np

# Source pitch (your truth)
PITCH_L = 105.0
PITCH_W = 68.0

# Output pitch
OUT_L = 100.0
OUT_W = 50.0

# Actions for "positioning" proxy = on-ball attacking actions only
KEEP_ACTIONS = {
  "Paslar adresi bulanlar",
  "Başarılı İleri Paslar",
  "İsabetli İlerletici Paslar",
  "Top Taşıma",
  "İsabetli Şut",
  "İsabetsiz Şut",
  "Gol",
  "İsabetli Kilit Paslar",
}

META_ACTIONS = {
  "Start of the 1st half","Halftime","Start of the 2nd half","End of the match"
}

def load_jsonl(p):
  out=[]
  if not os.path.exists(p): return out
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
  up=t.upper()
  if up in {"UNKNOWN_TEAM","UNKNOWN","NULL","NONE"}: return None
  return t

def action_of(r): return s(r.get("action") or "")

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
  if ". " in left:
    left=left.split(". ",1)[1].strip()
  return left or None

def safe_xy(r):
  try:
    x=r.get("x"); y=r.get("y")
    if x is None or y is None: return None
    x=float(x); y=float(y)
    if math.isnan(x) or math.isnan(y): return None
    # strict clamp to 105x68
    x=max(0.0,min(PITCH_L,x))
    y=max(0.0,min(PITCH_W,y))
    return x,y
  except:
    return None

def to_100x50(x, y):
  return (x / PITCH_L) * OUT_L, (y / PITCH_W) * OUT_W

def jitter_for_name(name, scale=0.85):
  h=hashlib.md5(name.encode("utf-8")).hexdigest()
  a=int(h[:8],16)/0xffffffff
  b=int(h[8:16],16)/0xffffffff
  return (a-0.5)*2*scale, (b-0.5)*2*scale

def ensure_mpl():
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  return plt

def draw_pitch_100x50(plt):
  # outline
  plt.plot([0,OUT_L],[0,0],linewidth=1)
  plt.plot([0,OUT_L],[OUT_W,OUT_W],linewidth=1)
  plt.plot([0,0],[0,OUT_W],linewidth=1)
  plt.plot([OUT_L,OUT_L],[0,OUT_W],linewidth=1)
  # halfway
  plt.plot([OUT_L/2, OUT_L/2],[0,OUT_W],linewidth=1,alpha=0.6)
  plt.xlim(0,OUT_L); plt.ylim(0,OUT_W)

def savefig(plt, outdir, name, dpi=340):
  p=os.path.join(outdir,name)
  plt.tight_layout()
  plt.savefig(p,dpi=dpi)
  plt.close()
  return name

def write_index(outdir, items, info_lines):
  p=os.path.join(outdir,"index.html")
  with open(p,"w",encoding="utf-8") as f:
    f.write('<!doctype html><meta charset="utf-8">')
    f.write('<h2>HPFA positions_v3 — attacking-only + GK + auto flip (100×50)</h2>')
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

def choose_top2_teams(out_ev):
  c=Counter()
  for r in out_ev:
    t=team_of(r)
    a=action_of(r)
    if not t: continue
    if a in META_ACTIONS: continue
    c[t]+=1
  return [t for t,_ in c.most_common(2)]

def decide_flip_for_team(rows):
  # Use ONLY KEEP_ACTIONS to decide orientation (avoid defensive bias)
  xs1=[]; xs2=[]
  for r in rows:
    a=action_of(r)
    if a in META_ACTIONS: continue
    if a and a not in KEEP_ACTIONS: continue
    xy=safe_xy(r)
    if not xy: continue
    h=half_of(r)
    if h==1: xs1.append(xy[0])
    elif h==2: xs2.append(xy[0])
  if len(xs1)<40 or len(xs2)<40:
    return False, f"insufficient_half_samples (h1={len(xs1)}, h2={len(xs2)})"
  m1=float(np.median(xs1)); m2=float(np.median(xs2))
  d0=abs(m2-m1)
  d1=abs(m2-(PITCH_L-m1))
  flip = d1 < d0
  return flip, f"m1={m1:.1f}, m2={m2:.1f}, d0={d0:.1f}, d1={d1:.1f}"

def norm_xy_team(r, x, y, flip_second_half):
  h=half_of(r)
  if flip_second_half and h==2:
    x = PITCH_L - x
  return x, y

def collect_positions(rows, flip_second_half):
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
    x,y = norm_xy_team(r, xy[0], xy[1], flip_second_half)
    x,y = to_100x50(x,y)
    pts[p].append((x,y))
    touches[p]+=1
  return pts, touches

def collect_gk_positions(gk_rows, flip_second_half):
  # GK stream may not have actions in KEEP_ACTIONS; keep all with xy for GK
  pts=defaultdict(list)
  touches=Counter()
  for r in gk_rows:
    if action_of(r) in META_ACTIONS:
      continue
    p=player_of(r)
    if not p: 
      continue
    xy=safe_xy(r)
    if not xy: 
      continue
    x,y = norm_xy_team(r, xy[0], xy[1], flip_second_half)
    x,y = to_100x50(x,y)
    pts[p].append((x,y))
    touches[p]+=1
  return pts, touches

def main():
  if len(sys.argv)!=3:
    print("USAGE: hpfa_positions_v3_100x50.py <match_out_dir> <report_out_dir>")
    sys.exit(2)

  match_out=sys.argv[1]
  outdir=sys.argv[2]
  os.makedirs(outdir, exist_ok=True)

  outfield_path=os.path.join(match_out,"canonical_outfield.jsonl")
  if not os.path.exists(outfield_path):
    raise SystemExit(f"ERROR missing: {outfield_path}")

  out_ev=load_jsonl(outfield_path)
  top2=choose_top2_teams(out_ev)
  if len(top2)!=2:
    raise SystemExit(f"ERROR: expected 2 teams, found: {top2}")

  # filter to top2 teams only
  by_team=defaultdict(list)
  for r in out_ev:
    t=team_of(r)
    if not t or t not in top2:
      continue
    by_team[t].append(r)

  # GK stream (optional)
  gk_path=os.path.join(match_out,"canonical_gk.jsonl")
  gk_ev=load_jsonl(gk_path)
  gk_by_team=defaultdict(list)
  for r in gk_ev:
    t=team_of(r)
    if not t or t not in top2:
      continue
    gk_by_team[t].append(r)

  # decide flip per team (attacking-only)
  flip_cfg={}
  info=[]
  for t in top2:
    flip, reason = decide_flip_for_team(by_team[t])
    flip_cfg[t]=flip
    info.append(f"<b>{t}</b>: flip_second_half={flip} ({reason})")

  plt=ensure_mpl()
  items=[]

  for t in top2:
    pts, touches = collect_positions(by_team[t], flip_cfg[t])

    # add GK if exists
    gk_note="GK: none (no canonical_gk.jsonl or no rows)"
    if gk_by_team.get(t):
      gk_pts, gk_touches = collect_gk_positions(gk_by_team[t], flip_cfg[t])
      if gk_touches:
        # take top GK by touches, add to pts
        gk_name = gk_touches.most_common(1)[0][0]
        pts[gk_name].extend(gk_pts[gk_name])
        touches[gk_name] += gk_touches[gk_name]
        gk_note=f"GK included: {gk_name}"
    info.append(f"{t}: {gk_note}")

    # choose 11 outfield + 1 GK = 12 max
    top_players=[p for p,_ in touches.most_common(12)]

    plt.figure(figsize=(10,6))
    draw_pitch_100x50(plt)

    xs=[]; ys=[]; ss=[]
    for p in top_players:
      arr=pts.get(p,[])
      if len(arr)<3:
        continue
      ax=np.array([q[0] for q in arr]); ay=np.array([q[1] for q in arr])
      x=float(np.median(ax)); y=float(np.median(ay))
      jx,jy=jitter_for_name(p, scale=0.9)
      x2=max(0,min(OUT_L,x+jx)); y2=max(0,min(OUT_W,y+jy))
      xs.append(x2); ys.append(y2)
      ss.append(55 + 4*min(touches[p],120))
      plt.text(x2, y2, p, fontsize=8, ha="center", va="center")

    plt.scatter(xs, ys, s=ss, alpha=0.84)
    plt.title(f"Median attacking action-locations (100×50) — {t}")
    plt.xlabel("x (0–100)"); plt.ylabel("y (0–50)")
    fn=savefig(plt, outdir, f"01_positions_attack_median__{t.replace(' ','_')}.png")
    items.append({"title": f"Attacking median positions — {t}", "file": fn})

  idx=write_index(outdir, items, info)
  print("OK ✅ positions_v3_100x50 built")
  print("Teams:", top2)
  print("OUT:", outdir)
  print("INDEX:", idx)

if __name__=="__main__":
  main()
