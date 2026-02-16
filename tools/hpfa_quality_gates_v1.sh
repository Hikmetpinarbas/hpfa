#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

MATCH_ID="${1:-rz-gs-20260208}"
OUTDIR="${2:-$HOME/hpfa/out/$MATCH_ID}"

CANON="$OUTDIR/canonical_outfield.jsonl"
[ -f "$CANON" ] || { echo "ERROR: missing $CANON"; exit 1; }

REP="$OUTDIR/quality_gates_v1"
mkdir -p "$REP"

python - <<'PY'
import json, os, math
from collections import Counter, defaultdict

outdir=os.environ["REP"]
canon=os.environ["CANON"]

def s(x): return (x or "").strip()
def safe_float(x):
    try:
        v=float(x)
        if math.isnan(v): return None
        return v
    except: return None

rows=[]
with open(canon,"r",encoding="utf-8") as f:
    for line in f:
        line=line.strip()
        if not line: continue
        try: rows.append(json.loads(line))
        except: pass

# Gate A: team coverage
teams=Counter()
unknown=0
for r in rows:
    t=s(r.get("team_raw") or "")
    if not t or t.upper().startswith("UNKNOWN"):
        unknown += 1
    else:
        teams[t]+=1

# Gate B: coord bounds sanity (expect 0..105 and 0..68)
oob=0; nxy=0
for r in rows:
    x=safe_float(r.get("x")); y=safe_float(r.get("y"))
    if x is None or y is None: continue
    nxy+=1
    if x<0 or x>105 or y<0 or y>68: oob+=1

# Gate C: pass semantic suspicion (pass x median way ahead of carry/shot)
PASS="Paslar adresi bulanlar"
CARRY="Top Taşıma"
SHOT={"İsabetli Şut","İsabetsiz Şut","Gol"}

def player_of(r):
    code=s(r.get("code") or "")
    if not code: return None
    left=code.split(" - ")[0].strip()
    if ". " in left: left=left.split(". ",1)[1].strip()
    return left or None

by=defaultdict(lambda: {"pass":[], "carry":[], "shot":[]})
for r in rows:
    p=player_of(r)
    if not p: continue
    a=s(r.get("action") or "")
    x=safe_float(r.get("x"))
    if x is None: continue
    if a==PASS: by[p]["pass"].append(x)
    elif a==CARRY: by[p]["carry"].append(x)
    elif a in SHOT: by[p]["shot"].append(x)

def med(xs):
    xs=sorted(xs)
    if not xs: return None
    n=len(xs)
    return xs[n//2] if n%2==1 else 0.5*(xs[n//2-1]+xs[n//2])

sus=[]
for p,d in by.items():
    mp=med(d["pass"]); mc=med(d["carry"]); ms=med(d["shot"])
    if mp is None or (mc is None and ms is None): 
        continue
    anchor = mc if mc is not None else ms
    if anchor is None: 
        continue
    if len(d["pass"])>=30 and abs(mp-anchor)>=18:  # 18m+ fark: hedef-semantik şüphesi
        sus.append((p,len(d["pass"]),mp,mc,ms))

sus.sort(key=lambda z: abs(z[2]- (z[3] if z[3] is not None else z[4])), reverse=True)

report={
  "n_rows": len(rows),
  "team_counts": teams,
  "unknown_team_rows": unknown,
  "xy_rows": nxy,
  "xy_out_of_bounds": oob,
  "pass_semantic_suspects_top10": [
    {"player":p,"n_pass":n,"med_x_pass":mp,"med_x_carry":mc,"med_x_shot":ms}
    for p,n,mp,mc,ms in sus[:10]
  ],
  "interpretation": {
    "unknown_team": "UNKNOWN_TEAM > 0 ise team mapping/join sorunu var; grafiklerde 3. takım çıkar.",
    "oob_xy": "oob>0 ise parsing/scale hatası var (delimiter, sütun kayması, yanlış x/y).",
    "pass_semantics": "suspects doluysa pas koordinatı 'hedef noktası' olabilir; positions hesaplarında pasları kullanma."
  }
}

os.makedirs(outdir, exist_ok=True)
with open(os.path.join(outdir,"quality_gates.json"),"w",encoding="utf-8") as f:
    json.dump(report,f,ensure_ascii=False,indent=2)
print("OK ✅ wrote", os.path.join(outdir,"quality_gates.json"))
PY

echo "OPEN: $REP/quality_gates.json"
