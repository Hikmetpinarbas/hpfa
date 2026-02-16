#!/data/data/com.termux/files/usr/bin/python
import argparse
import hashlib
import json
from pathlib import Path

HOME = Path("/data/data/com.termux/files/home")
DIAG = HOME / "hpfa" / "_diag"
DEFAULT_BASELINE = DIAG / "engine_artifacts.CORE.BASELINE.json"

CORE_FILES = [
    "engine_seq_possessions.json",
    "engine_xt01_grid.json",
]

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def snapshot_core(run_dir: Path) -> dict:
    files = []
    for name in CORE_FILES:
        p = run_dir / name
        if not p.exists():
            raise FileNotFoundError(str(p))
        files.append({
            "name": name,
            "size": p.stat().st_size,
            "sha256": sha256_file(p),
        })

    h = hashlib.sha256()
    for r in sorted(files, key=lambda x: x["name"]):
        h.update(f'{r["name"]}\t{r["size"]}\t{r["sha256"]}\n'.encode("utf-8"))

    return {
        "run_dir": str(run_dir),
        "core_files": sorted(files, key=lambda x: x["name"]),
        "fingerprint_sha256": h.hexdigest(),
    }

def read_json(p: Path) -> dict:
    return json.loads(p.read_text("utf-8"))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", help="engine_run_* directory")
    ap.add_argument("--baseline", default=str(DEFAULT_BASELINE))
    ap.add_argument("--write-baseline", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.exists():
        print("[FAIL] missing run_dir:", run_dir)
        raise SystemExit(2)

    snap = snapshot_core(run_dir)
    baseline_p = Path(args.baseline)
    baseline_p.parent.mkdir(parents=True, exist_ok=True)

    if args.write_baseline:
        # NOOP guard: same fingerprint => do not overwrite baseline
        if baseline_p.exists():
            try:
                base = read_json(baseline_p)
                bfp = str(base.get("fingerprint_sha256", ""))
                cfp = str(snap.get("fingerprint_sha256", ""))
                if bfp and (bfp == cfp):
                    print("[OK] core baseline already up-to-date (noop)")
                    print("[OK] fingerprint_sha256=", cfp)
                    raise SystemExit(0)
            except Exception:
                # baseline corrupt/unknown => overwrite
                pass

        baseline_p.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
        print("[OK] core baseline written:", baseline_p)
        print("[OK] fingerprint_sha256=", snap["fingerprint_sha256"])
        raise SystemExit(0)

    if not baseline_p.exists():
        print("[FAIL] missing baseline:", baseline_p)
        print("[HINT] create baseline: python hp_engine_artifact_guard_strict_core.py RUN_DIR --write-baseline")
        raise SystemExit(4)

    base = read_json(baseline_p)
    bfp = str(base.get("fingerprint_sha256", ""))
    cfp = str(snap.get("fingerprint_sha256", ""))

    print("[OK] baseline(core) =", bfp)
    print("[OK] current(core)  =", cfp)

    if bfp == cfp:
        print("[OK] CORE_ARTIFACTS_MATCH")
        raise SystemExit(0)

    bidx = {r.get("name"): r for r in base.get("core_files", []) if isinstance(r, dict) and r.get("name")}
    cidx = {r.get("name"): r for r in snap.get("core_files", []) if isinstance(r, dict) and r.get("name")}

    print("\n== CORE FILE-LEVEL DIFF ==")
    for name in sorted(set(bidx) | set(cidx)):
        if name not in bidx:
            print("[ADDED]", name)
            continue
        if name not in cidx:
            print("[REMOVED]", name)
            continue
        if (bidx[name].get("sha256") != cidx[name].get("sha256")) or (bidx[name].get("size") != cidx[name].get("size")):
            print("[CHANGED]", name)
            print("  baseline_sha=", bidx[name].get("sha256"))
            print("  now_sha     =", cidx[name].get("sha256"))
            print("  baseline_sz =", bidx[name].get("size"))
            print("  now_sz      =", cidx[name].get("size"))

    if args.strict:
        print("\n[FAIL] CORE_ARTIFACTS_DRIFT")
        raise SystemExit(9)

    print("\n[WARN] core drift but not strict")
    raise SystemExit(0)

if __name__ == "__main__":
    main()
