import os, json, glob, hashlib
from pathlib import Path

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

out_dir = os.environ.get("OUT_DIR")
if not out_dir:
    cands = sorted(glob.glob(os.path.expanduser("~/hpfa/_out/engine_run_*")))
    if not cands:
        raise SystemExit("[FAIL] OUT_DIR not set and no engine_run_* found")
    out_dir = cands[-1]

out = Path(out_dir)
meta_p = out / "engine_meta.json"
seq_p  = out / "engine_seq_possessions.json"
xt_p   = out / "engine_xt01_grid.json"

print("OUT_DIR:", out.as_posix())
for p in [meta_p, seq_p, xt_p]:
    print(" -", p.name, "exists=", p.exists(), "sha256=", sha256_file(p) if p.exists() else None)

meta = json.loads(meta_p.read_text(encoding="utf-8"))
print("\n== engine_meta.json ==")
print("keys:", sorted(meta.keys()))
print("source_csv:", meta.get("source_csv"))
print("n_events:", meta.get("n_events"))
print("modules.keys:", list((meta.get("modules") or {}).keys()))
print("refs_library:", meta.get("refs_library"))

seq = json.loads(seq_p.read_text(encoding="utf-8"))
print("\n== engine_seq_possessions.json ==")
print("keys:", list(seq.keys()))
print("policy:", seq.get("policy"))
print("n_possessions:", seq.get("n_possessions"))

summ = seq.get("summaries")
print("summaries type:", type(summ).__name__)
if isinstance(summ, dict):
    print("summaries keys:", list(summ.keys())[:50])
elif isinstance(summ, list):
    print("summaries len:", len(summ))
    if summ:
        print("summaries[0] keys:", list(summ[0].keys())[:50] if isinstance(summ[0], dict) else type(summ[0]).__name__)
else:
    print("summaries:", summ)

xt = json.loads(xt_p.read_text(encoding="utf-8"))
print("\n== engine_xt01_grid.json ==")
print("grid_spec:", xt.get("grid_spec"))
print("solve_spec:", xt.get("solve_spec"))
gv = xt.get("grid_values") or {}
print("grid_values_n:", len(gv))
print("sample:", list(gv.items())[:8])
