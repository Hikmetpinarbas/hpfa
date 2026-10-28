from __future__ import annotations

import argparse
import hashlib
import json
import tomllib
import zipfile
from pathlib import Path
from typing import Iterable

ALLOWED_SUFFIXES = {".py", ".json", ".csv", ".tsv", ".yaml", ".yml", ".txt", ".md"}
REQUIRED_ROOT_FILES = (
    "README.md",
    "LICENSE",
    "NOTICE",
    "THIRD_PARTY_NOTICES.md",
    "pyproject.toml",
)
REQUIRED_RELEASE_FILES = (
    "release/commercial_pilot_policy_v1.json",
    "release/HPFA_CONTROLLED_COMMERCIAL_PILOT_QUICKSTART_V1.md",
    "release/release_bundle_policy_v1.json",
    "release/release_dependency_policy_v1.json",
)
FORBIDDEN_PARTS = {"tests", "__pycache__", "runtime", "data", "vendor", "out", "build", "_diag"}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _iter_product_files(repo: Path) -> Iterable[Path]:
    pyproject = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    root_modules = sorted(set(pyproject["tool"]["setuptools"].get("py-modules") or []))

    selected: set[Path] = set()
    for rel in REQUIRED_ROOT_FILES + REQUIRED_RELEASE_FILES:
        path = repo / rel
        if path.is_file():
            selected.add(path)

    for module in root_modules:
        path = repo / f"{module}.py"
        if path.is_file():
            selected.add(path)

    for root_name in ("hpfa", "canon"):
        root = repo / root_name
        if not root.is_dir():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(repo)
            if any(part in FORBIDDEN_PARTS for part in rel.parts):
                continue
            if path.suffix.lower() not in ALLOWED_SUFFIXES:
                continue
            selected.add(path)

    return sorted(selected, key=lambda p: p.relative_to(repo).as_posix())


def build_bundle(repo: Path, out: Path, *, exact_head_sha: str) -> dict:
    repo = repo.resolve()
    out = out.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    files = list(_iter_product_files(repo))

    manifest = {
        "bundle_id": "hpfa_controlled_commercial_pilot_bundle_v1",
        "exact_head_sha": exact_head_sha,
        "commercial_scope": "ASSISTED_CONTROLLED_PILOT",
        "production_release": False,
        "public_index_upload_authorized": False,
        "raw_match_data_bundled": False,
        "raw_donor_bundled": False,
        "third_party_runtime_bundled": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "file_count": len(files) + 1,
    }
    manifest_bytes = (
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    fixed_time = (1980, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in files:
            rel = path.relative_to(repo).as_posix()
            info = zipfile.ZipInfo(rel, date_time=fixed_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, path.read_bytes())
        info = zipfile.ZipInfo("HPFA_CONTROLLED_COMMERCIAL_PILOT_MANIFEST.json", date_time=fixed_time)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info, manifest_bytes)

    result = dict(manifest)
    result["bundle_status"] = "PASS"
    result["bundle_sha256"] = _sha256(out)
    result["bundle_path"] = str(out)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", default=".")
    parser.add_argument("--out", required=True)
    parser.add_argument("--exact-head", required=True)
    parser.add_argument("--report-out")
    args = parser.parse_args()

    report = build_bundle(
        Path(args.repo),
        Path(args.out),
        exact_head_sha=args.exact_head,
    )
    if args.report_out:
        report_path = Path(args.report_out)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
