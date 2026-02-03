#!/usr/bin/env python3
"""
HPFA Orchestrator: copied-not-deleted repo merge with provenance.

Usage:
  python orchestrator/migrate_repos.py --engine /path/to/HP-Engine --motor /path/to/HP-Motor --target /path/to/hpfa

Behavior:
  - Copies files (does NOT delete anything in source).
  - Skips .git, .venv, __pycache__, caches.
  - Writes <file>.PROVENANCE.json next to each copied file.
  - Embeds commit hash if source is a git repo.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


SKIP_DIR_NAMES = {
    ".git", ".venv", "__pycache__", ".pytest_cache", "dist", "build", ".mypy_cache",
}
SKIP_FILE_SUFFIXES = {
    ".pyc", ".pyo", ".DS_Store",
}


@dataclass(frozen=True)
class CopyPlan:
    src_root: Path
    dst_root: Path
    source_name: str
    commit: Optional[str]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def is_git_repo(path: Path) -> bool:
    return (path / ".git").exists()


def git_head_commit(path: Path) -> Optional[str]:
    if not is_git_repo(path):
        return None
    try:
        out = subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out or None
    except Exception:
        return None


def should_skip_dir(dir_path: Path) -> bool:
    name = dir_path.name
    return name in SKIP_DIR_NAMES


def should_skip_file(file_path: Path) -> bool:
    if file_path.name in {"Thumbs.db"}:
        return True
    return file_path.suffix in SKIP_FILE_SUFFIXES


def iter_files(root: Path) -> Iterable[Path]:
    for base, dirs, files in os.walk(root):
        base_p = Path(base)

        # prune dirs in-place
        pruned = []
        for d in list(dirs):
            dp = base_p / d
            if should_skip_dir(dp):
                pruned.append(d)
        for d in pruned:
            dirs.remove(d)

        for f in files:
            fp = base_p / f
            if should_skip_file(fp):
                continue
            yield fp


def safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def write_provenance(dst_file: Path, plan: CopyPlan, src_file: Path) -> None:
    prov = {
        "source_repo": plan.source_name,
        "source_root": str(plan.src_root.resolve()),
        "source_commit": plan.commit,
        "original_path": str(src_file.resolve()),
        "copied_to": str(dst_file.resolve()),
        "copied_at_utc": utc_now_iso(),
    }
    prov_path = dst_file.with_name(dst_file.name + ".PROVENANCE.json")
    with open(prov_path, "w", encoding="utf-8") as f:
        json.dump(prov, f, ensure_ascii=False, indent=2)


def copy_one(src_file: Path, plan: CopyPlan) -> None:
    rel = src_file.relative_to(plan.src_root)
    dst_file = plan.dst_root / rel
    safe_mkdir(dst_file.parent)

    # copied-not-deleted: if exists, DO NOT overwrite (preserve earlier copy)
    if not dst_file.exists():
        shutil.copy2(src_file, dst_file)

    # provenance always updated/created (records this orchestrator run)
    write_provenance(dst_file, plan, src_file)


def run_copy(plan: CopyPlan) -> tuple[int, int]:
    copied = 0
    scanned = 0
    for src_file in iter_files(plan.src_root):
        scanned += 1
        copy_one(src_file, plan)
        copied += 1
    return scanned, copied


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--engine", required=True, help="Path to HP-Engine repo (local clone)")
    p.add_argument("--motor", required=True, help="Path to HP-Motor repo (local clone)")
    p.add_argument("--target", required=True, help="Path to HPFA target repo root (this repo)")
    args = p.parse_args()

    engine = Path(args.engine).expanduser().resolve()
    motor = Path(args.motor).expanduser().resolve()
    target = Path(args.target).expanduser().resolve()

    if not engine.exists():
        raise SystemExit(f"--engine path not found: {engine}")
    if not motor.exists():
        raise SystemExit(f"--motor path not found: {motor}")
    if not target.exists():
        raise SystemExit(f"--target path not found: {target}")

    engine_commit = git_head_commit(engine)
    motor_commit = git_head_commit(motor)

    plan_engine = CopyPlan(
        src_root=engine,
        dst_root=target / "hp-engine",
        source_name="HP-Engine",
        commit=engine_commit,
    )
    plan_motor = CopyPlan(
        src_root=motor,
        dst_root=target / "hp-motor",
        source_name="HP-Motor",
        commit=motor_commit,
    )

    safe_mkdir(plan_engine.dst_root)
    safe_mkdir(plan_motor.dst_root)

    e_scanned, e_copied = run_copy(plan_engine)
    m_scanned, m_copied = run_copy(plan_motor)

    print(f"[OK] Engine: scanned={e_scanned} copied={e_copied} -> {plan_engine.dst_root}")
    print(f"[OK] Motor : scanned={m_scanned} copied={m_copied} -> {plan_motor.dst_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
