from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def zip_content_hashes(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as archive:
        return {
            name: hashlib.sha256(archive.read(name)).hexdigest()
            for name in sorted(archive.namelist())
        }


def compare_wheels(a: Path, b: Path) -> dict:
    a_hash = sha256_file(a)
    b_hash = sha256_file(b)
    a_content = zip_content_hashes(a)
    b_content = zip_content_hashes(b)
    names_equal = set(a_content) == set(b_content)
    content_diffs = sorted(
        name for name in set(a_content) & set(b_content)
        if a_content[name] != b_content[name]
    )
    return {
        "wheel_a_sha256": a_hash,
        "wheel_b_sha256": b_hash,
        "byte_identical": a_hash == b_hash,
        "entry_name_sets_equal": names_equal,
        "content_diff_entries": content_diffs,
    }


def build_once(repo: Path, out_dir: Path, source_date_epoch: str) -> Path:
    shutil.rmtree(repo / "build", ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["SOURCE_DATE_EPOCH"] = source_date_epoch
    subprocess.run(
        [sys.executable, "-m", "pip", "wheel", ".", "--no-deps", "-w", str(out_dir)],
        cwd=repo,
        env=env,
        check=True,
        stdout=subprocess.DEVNULL,
    )
    wheels = sorted(out_dir.glob("hpfa-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected_one_hpfa_wheel:{len(wheels)}")
    return wheels[0]


def run_probe(repo: Path, out_dir: Path) -> dict:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    epoch = subprocess.check_output(
        ["git", "show", "-s", "--format=%ct", "HEAD"], cwd=repo, text=True
    ).strip()
    build_root = out_dir / "builds"
    shutil.rmtree(build_root, ignore_errors=True)
    wheel_a = build_once(repo, build_root / "a", epoch)
    wheel_b = build_once(repo, build_root / "b", epoch)
    comparison = compare_wheels(wheel_a, wheel_b)
    return {
        "probe_id": "hpfa_reproducible_wheel_probe_v1",
        "status": "PASS" if comparison["byte_identical"] else "FAIL",
        "scope": "SAME_SOURCE_SAME_TOOLCHAIN_BUILD_ENVIRONMENT",
        "git_head": head,
        "source_date_epoch": epoch,
        "dependency_lock_complete": False,
        "cross_toolchain_reproducibility": "NOT_EVALUATED",
        **comparison,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    report = run_probe(repo, out_dir)
    (out_dir / "hpfa_reproducible_wheel_probe_v1.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
