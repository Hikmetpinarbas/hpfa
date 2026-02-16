import os, json, glob, hashlib
from pathlib import Path

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

primary_dir = os.environ.get("PRIMARY_DIR")
out_dir = os.environ.get("OUT_DIR")

if not out_dir:
    cands = sorted(glob.glob(os.path.expanduser("~/hpfa/_out/engine_run_*")))
    if not cands:
        raise SystemExit("[FAIL] OUT_DIR not set and no engine_run_* found")
    out_dir = cands[-1]

out = Path(out_dir)
meta_p = out / "engine_meta.json"
if not meta_p.exists():
    raise SystemExit(f"[FAIL] missing {meta_p}")

meta = json.loads(meta_p.read_text(encoding="utf-8"))

# input evidence
source_csv = meta.get("source_csv") or "events_canonical.csv"
src_path = None
if primary_dir:
    src_path = Path(primary_dir) / source_csv
src_sha = sha256_file(src_path) if (src_path and src_path.exists()) else None

# mapping evidence (if exists)
map_path = Path(os.getcwd()) / "mappings" / "engine_action_map.json"
map_sha = sha256_file(map_path) if map_path.exists() else None

# library refs evidence
refs = meta.get("refs_library") or {}
refs_json = json.dumps(refs, sort_keys=True, ensure_ascii=False).encode("utf-8")
refs_sha = hashlib.sha256(refs_json).hexdigest()

stamped = {
    "engine_id": os.environ.get("ENGINE_ID", "engine_alpha"),
    "provider": os.environ.get("ENGINE_PROVIDER", "hpfa.engine.internal"),
    "algo_version": os.environ.get("ENGINE_ALGO_VERSION", "v0.1"),
    "input": {
        "primary_dir": primary_dir,
        "source_csv": source_csv,
        "source_csv_sha256": src_sha,
    },
    "evidence": {
        "out_dir": out.as_posix(),
        "artifacts": meta.get("artifacts") or [],
        "artifact_sha256": {
            "engine_seq_possessions.json": sha256_file(out / "engine_seq_possessions.json") if (out / "engine_seq_possessions.json").exists() else None,
            "engine_xt01_grid.json": sha256_file(out / "engine_xt01_grid.json") if (out / "engine_xt01_grid.json").exists() else None,
            "engine_meta.json": sha256_file(out / "engine_meta.json"),
        },
        "mapping": {
            "engine_action_map.json": map_path.as_posix() if map_path.exists() else None,
            "sha256": map_sha,
        },
        "refs_library_sha256": refs_sha,
    },
    "raw_engine_meta": meta,
}

out_p = out / "engine_meta_stamped.json"
out_p.write_text(json.dumps(stamped, indent=2, ensure_ascii=False), encoding="utf-8")
print("[OK] wrote:", out_p.as_posix())
