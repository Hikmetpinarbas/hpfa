import os, json, glob, hashlib
from pathlib import Path

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

def pick_latest_engine_out(root: Path) -> Path | None:
    cands = sorted(root.glob("engine_run_*"))
    return cands[-1] if cands else None

HPFA_WORK = Path(os.environ.get("HPFA_WORK", Path.home()/"hpfa"))
HPFA_OUT  = Path(os.environ.get("HPFA_OUT", HPFA_WORK/"_out"))
PRIMARY_DIR = os.environ.get("PRIMARY_DIR")
OUT_DIR = os.environ.get("OUT_DIR")

if not PRIMARY_DIR:
    raise SystemExit("[FAIL] PRIMARY_DIR not set")
primary = Path(PRIMARY_DIR)

if not OUT_DIR:
    latest = pick_latest_engine_out(HPFA_OUT)
    if not latest:
        raise SystemExit("[FAIL] OUT_DIR not set and no engine_run_* found")
    OUT_DIR = str(latest)
out = Path(OUT_DIR)

src_csv = primary / "events_canonical.csv"
if not src_csv.exists():
    raise SystemExit(f"[FAIL] missing {src_csv}")

engine_meta_stamped = out / "engine_meta_stamped.json"
seq = out / "engine_seq_possessions.json"
xt  = out / "engine_xt01_grid.json"

ctx = {
    "version": "0.1.0",
    "paths": {
        "primary_dir": primary.as_posix(),
        "out_dir": out.as_posix(),
        "source_csv": src_csv.as_posix(),
        "engine_meta_stamped": engine_meta_stamped.as_posix() if engine_meta_stamped.exists() else None,
        "engine_seq": seq.as_posix() if seq.exists() else None,
        "engine_xt": xt.as_posix() if xt.exists() else None,
        "ssot_registry": (HPFA_WORK/"ssot/providers/registry.json").as_posix(),
        "engine_contract": (HPFA_WORK/"ssot/contracts/engine_provider_contract_v01.json").as_posix()
    },
    "sha256": {
        "events_canonical.csv": sha256_file(src_csv),
        "engine_meta_stamped.json": sha256_file(engine_meta_stamped) if engine_meta_stamped.exists() else None,
        "engine_seq_possessions.json": sha256_file(seq) if seq.exists() else None,
        "engine_xt01_grid.json": sha256_file(xt) if xt.exists() else None
    }
}

out_ctx = out / "run_context.json"
out_ctx.write_text(json.dumps(ctx, indent=2, ensure_ascii=False), encoding="utf-8")
print("[OK] wrote:", out_ctx.as_posix())
print("[OK] primary:", ctx["paths"]["primary_dir"])
print("[OK] out_dir:", ctx["paths"]["out_dir"])
