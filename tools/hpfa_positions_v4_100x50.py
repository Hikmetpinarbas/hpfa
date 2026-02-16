#!/usr/bin/env python3
import os, sys, json, math, hashlib
from collections import defaultdict, Counter
import numpy as np

PITCH_L=105.0; PITCH_W=68.0
OUT_L=100.0; OUT_W=50.0

# Positioning proxy (actor-location likely)
KEEP_ACTIONS = {
  "Top Taşıma",
  "Başarılı driplingler",
  "Başarısız Driplingler",
  "İsabetli Şut",
  "İsabetsiz Şut",
  "Gol",
  "Başarılı Top Kapma",
  "Başarısız Top Kapma",
  "Geri Kazanılan Toplar",
  "Faul",
  "Yapılan Fauller",
}

META_ACTIONS={"Start of the 1st half","Halftime","Start of the 2nd half","End of the match"}

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
  t=s(r.get("team_raw") or r.get("team") or "")
  if not t or t.upper() in {"UNKNOWN_TEAM","UNKNOWN","NULL","NONE"}: return None
  return t

def action_of(r): return s(r.get("action") or "")

def half_of(r):
  try:
    h=r.get("half"); return int(h) if h is not None else None
  except: return None

def player_of(r):
  code=s(r.get("code") or "")
  if not code: return None
  left=code.split(" - ")[0].strip()
  if ". " in left: left=left.split(". ",1)[1].strip()
  return left or None

def safe_xy(r):
  try:
    x=float(r.get("x")); y=float(r.get("y"))
    if math.isnan(x) or math.isnan(y): return None
    x=max(0.0,min(PITCH_L,x)); y=max(0.0,min(PITCH_W,y))
    return x,y
  except: return None

def to_100x50(x,y):
  return (x/PITCH_L)*OUT_L, (y/PITCH_W)*OUT_W

def jitter(name, scale=0.85):
  import hashlib
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
  plt.plot([0,OUT_L],[0,0],lw=1); plt.plot([0,OUT_L],[OUT_W,OUT_W],lw=1)
  plt.plot([0,0],[0,OUT_W],lw=1); plt.plot([OUT_L,OUT_L],[0,OUT_W],lw=1)
  plt.plot([OUT_L/2,OUT_L/2],[0,OUT_W],lw=1,alpha=0.6)
  plt.xlim(0,OUT_L); plt.ylim(0,OUT_W)

def savefig(plt,outdir,name,dpi=340):
  p=os.path.join(outdir,name)
  plt.tight_layout(); plt.savefig(p,dpi=dpi); plt.close()
  return name

def write_index(outdir, items, info):
  p=os.path.join(outdir,"index.html")
  with open(p,"w",encoding="utf-8") as f:
    f.write('<!doctype html><meta charset="utf-8">')
    f.write('<h2>HPFA positions_v4 — actor-location actions only (100×50)</h2>')
    f.write('<ul>')
    for line in info: f.write(f"<li>{line}</li>")
    f.write('</ul><ul>')
    for it in items:
      f.write(f'<li><b>{it["title"]}</b><br><img src="{it["file"]}" style="max-width:100%"></li>')
    f.write('</ul>')
  return p

def choose_top2_teams(ev):
  c=Counter()
  for r in ev:
    t=team_of(r); a=action_of(r)
    if not t or a in META_ACTIONS: continue
    c[t]+=1
  return [t for t,_ in c.most_common(2)]

def decide_flip(rows):
  # Decide flip using SHOT-like actions (most reliable direction signal)
  xs1=[]; xs2=[]
  for r in rows:
    a=action_of(r)
    if a in META_ACTIONS: continue
    if a not in {"İsabetli Şut","İsabetsiz Şut","Gol","Top Taşıma"}: continue
    pt=safe_xy(r)
    if not pt: continue
    h=half_of(r)
    if h==1: xs1.append(pt[0])
    elif h==2: xs2.append(pt[0])
  if len(xs1)<20 or len(xs2)<20:
    return False, f"insufficient(h1={len(xs1)},h2={len(xs2)})"
  m1=float(np.median(xs1)); m2=float(np.median(xs2))
  d0=abs(m2-m1); d1=abs(m2-(PITCH_L-m1))
  flip=d1<d0
  return flip, f"m1={m1:.1f},m2={m2:.1f},d0={d0:.1f},d1={d1:.1f}"

def main():
  if len(sys.argv)!=3:
    print("USAGE: hpfa_positions_v4_100x50.py <match_out_dir> <report_out_dir>")
    sys.exit(2)

  match_out=sys.argv[1]; outdir=sys.argv[2]
  os.makedirs(outdir, exist_ok=True)

  ev=load_jsonl(os.path.join(match_out,"canonical_outfield.jsonl"))
  top2=choose_top2_teams(ev)
  if len(top2)!=2: raise SystemExit(f"Need 2 teams, got {top2}")

  by=defaultdict(list)
  for r in ev:
    t=team_of(r)
    if t in top2: by[t].append(r)

  flip_cfg={}; info=[]
  for t in top2:
    flip,reason=decide_flip(by[t])
    flip_cfg[t]=flip
    info.append(f"<b>{t}</b>: flip_second_half={flip} ({reason})")

  plt=ensure_mpl()
  items=[]
  for t in top2:
    pts=defaultdict(list); touches=Counter()
    for r in by[t]:
      a=action_of(r)
      if a in META_ACTIONS or a not in KEEP_ACTIONS: continue
      p=player_of(r); pt=safe_xy(r)
      if not p or not pt: continue
      x,y=pt
      if flip_cfg[t] and half_of(r)==2:
        x=PITCH_L-x
      x,y=to_100x50(x,y)
      pts[p].append((x,y)); touches[p]+=1

    top=[p for p,_ in touches.most_common(11)]  # outfield 11
    plt.figure(figsize=(10,6)); draw_pitch(plt)
    xs=[]; ys=[]; ss=[]
    for p in top:
      arr=pts.get(p,[])
      if len(arr)<3: continue
      ax=np.array([q[0] for q in arr]); ay=np.array([q[1] for q in arr])
      x=float(np.median(ax)); y=float(np.median(ay))
      jx,jy=jitter(p,0.9)
      x=max(0,min(OUT_L,x+jx)); y=max(0,min(OUT_W,y+jy))
      xs.append(x); ys.append(y); ss.append(55+4*min(touches[p],120))
      plt.text(x,y,p,fontsize=8,ha="center",va="center")
    plt.scatter(xs,ys,s=ss,alpha=0.84)
    plt.title(f"Median actor-locations (no passes) — {t}")
    fn=savefig(plt,outdir,f"01_positions_actor__{t.replace(' ','_')}.png")
    items.append({"title":f"Positions (actor-only) — {t}","file":fn})

  idx=write_index(outdir,items,info)
  print("OK ✅ positions_v4 built")
  print("OUT:", outdir)
  print("INDEX:", idx)

if __name__=="__main__":
  main()
