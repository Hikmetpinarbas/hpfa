import argparse
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime

HOME = Path("/data/data/com.termux/files/home")
HPFA = HOME / "hpfa"
DIAG = HPFA / "_diag"
DIAG.mkdir(parents=True, exist_ok=True)

DEFAULT_WATCH = [
    "engine_seq_possessions.json",
    "engine_xt01_grid.json",
    "engine_meta.json",
]

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "ignore")).hexdigest()

def load_json(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        return None

def stable_json_hash(obj) -> str:
    # JSON obj -> canonical string -> sha256
    try:
        s = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except Exception:
        s = str(obj)
    return sha256_text(s)

def best_run_dir(out_dir: Path) -> Path:
    if out_dir.is_dir():
        return out_dir
    raise SystemExit(f"[FAIL] OUT_DIR not found or not a dir: {out_dir}")

def collect_fingerprint(run_dir: Path, watch_names):
    fp = {
        "run_dir": str(run_dir),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "files": [],
    }

    for name in watch_names:
        p = run_dir / name
        if not p.exists():
            fp["files"].append({
                "name": name,
                "path": str(p),
                "present": False,
            })
            continue

        item = {
            "name": name,
            "path": str(p),
            "present": True,
            "size_bytes": p.stat().st_size,
            "sha256": sha256_file(p),
        }

        # JSON ise içerik-hash de üret (field order farkı vs. ayıklamak için)
        if p.suffix.lower() == ".json":
            obj = load_json(p)
            if obj is not None:
                item["json_canon_sha256"] = stable_json_hash(obj)

        fp["files"].append(item)

    # fingerprint toplu hash (list order stable)
    canon = json.dumps(fp, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    fp["fingerprint_sha256"] = sha256_text(canon)
    return fp

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir", help="hpfa _out run directory (engine_run_YYYYMMDD_HHMMSS)")
    ap.add_argument("--watch", nargs="*", default=DEFAULT_WATCH, help="artifact basenames to watch")
    ap.add_argument("--baseline", default=str(DIAG / "engine_artifacts.BASELINE.json"), help="baseline json path")
    ap.add_argument("--write-baseline", action="store_true", help="write baseline = current fingerprint")
    ap.add_argument("--strict", action="store_true", help="fail if any watched file is missing")
    args = ap.parse_args()

    run_dir = best_run_dir(Path(args.out_dir))
    fp = collect_fingerprint(run_dir, args.watch)

    baseline_path = Path(args.baseline)
    if args.write_baseline:
        baseline_path.write_text(json.dumps(fp, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] baseline written: {baseline_path}")
        print(f"[OK] fingerprint_sha256={fp['fingerprint_sha256']}")
        return

    # strict missing check
    if args.strict:
        missing = [x for x in fp["files"] if not x.get("present")]
        if missing:
            print("[FAIL] missing watched artifacts:")
            for m in missing:
                print(" -", m["name"], "->", m["path"])
            raise SystemExit(3)

    if not baseline_path.exists():
        print(f"[WARN] baseline not found: {baseline_path}")
        print("[HINT] create baseline with:")
        print(f"       python ~/hpfa/tools/hp_engine_artifact_guard.py {run_dir} --write-baseline")
        print(f"[OK] fingerprint_sha256={fp['fingerprint_sha256']}")
        return

    base = load_json(baseline_path)
    if base is None:
        print(f"[FAIL] cannot read baseline json: {baseline_path}")
        raise SystemExit(4)

    base_fp = base.get("fingerprint_sha256")
    cur_fp = fp.get("fingerprint_sha256")

    if base_fp == cur_fp:
        print("[OK] artifact fingerprint: MATCH")
        print(f"[OK] baseline={baseline_path}")
        print(f"[OK] fingerprint_sha256={cur_fp}")
        return

    # diff report (file-level)
    print("[FAIL] artifact fingerprint: DRIFT")
    print(f"[FAIL] baseline={baseline_path}")
    print(f"[FAIL] baseline_fp={base_fp}")
    print(f"[FAIL] current_fp ={cur_fp}")
    print("\n== FILE-LEVEL DIFF ==")

    base_map = {x["name"]: x for x in base.get("files", []) if "name" in x}
    cur_map  = {x["name"]: x for x in fp.get("files", []) if "name" in x}

    names = sorted(set(base_map.keys()) | set(cur_map.keys()))
    for n in names:
        b = base_map.get(n)
        c = cur_map.get(n)
        if b is None:
            print(f"[DIFF] + {n} (new) sha256={c.get('sha256')}")
            continue
        if c is None:
            print(f"[DIFF] - {n} (missing now) baseline_sha256={b.get('sha256')}")
            continue

        if b.get("present") != c.get("present"):
            print(f"[DIFF] ! {n} present baseline={b.get('present')} now={c.get('present')}")
            continue

        # compare sha
        if b.get("sha256") != c.get("sha256"):
            print(f"[DIFF] * {n} sha256 changed")
            print(f"       baseline={b.get('sha256')}")
            print(f"       now     ={c.get('sha256')}")
        # compare json canon sha if exists
        if b.get("json_canon_sha256") and c.get("json_canon_sha256") and b.get("json_canon_sha256") != c.get("json_canon_sha256"):
            print(f"[DIFF] * {n} json_canon_sha256 changed")
            print(f"       baseline={b.get('json_canon_sha256')}")
            print(f"       now     ={c.get('json_canon_sha256')}")

    # write current snapshot for inspection
    snap = DIAG / f"engine_artifacts.SNAPSHOT.{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    snap.write_text(json.dumps(fp, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[OK] current snapshot written: {snap}")
    raise SystemExit(9)

if __name__ == "__main__":
    main()
