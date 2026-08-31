from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import trackable_action_trace_candidates_current_v1 as current_trace
from hpfa.modules.core.action_occurrence_admission_lite.src import action_occurrence_admission as occurrence

PACKAGE_NAME = "HPFA_OCCURRENCE_ACTIVE_MATCH_EVIDENCE_V1.zip"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_head() -> str:
    repo = Path(__file__).resolve().parent
    try:
        return subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def build_package(input_dir: str | Path, out_dir: str | Path) -> dict:
    input_root = Path(input_dir).expanduser().resolve(strict=False)
    phone_root = occurrence.validate_out(out_dir)
    phone_root.mkdir(parents=True, exist_ok=True)
    package_path = phone_root / PACKAGE_NAME

    if not input_root.is_dir():
        raise ValueError("active_match_input_directory_missing")

    with tempfile.TemporaryDirectory(prefix="hpfa_occurrence_evidence_") as temp_name:
        temp_root = Path(temp_name)
        runtime_payload = current_trace.runtime_write_outputs(input_root, temp_root)
        generated_files = sorted(path for path in temp_root.rglob("*") if path.is_file())
        input_files = sorted(path for path in input_root.iterdir() if path.is_file())

        manifest = {
            "package_id": "HPFA_OCCURRENCE_ACTIVE_MATCH_EVIDENCE_V1",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "exact_git_head": _git_head(),
            "input_surface_count": len(input_files),
            "input_surfaces": [
                {
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
                for path in input_files
            ],
            "artifact_count": len(generated_files),
            "artifacts": [
                {
                    "path": path.relative_to(temp_root).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
                for path in generated_files
            ],
            "runtime_status": runtime_payload.get("status"),
            "current_occurrence_status": runtime_payload.get("current_occurrence_status"),
            "current_occurrence_candidate_count": runtime_payload.get("current_occurrence_candidate_count", 0),
            "canonical_event_count": "UNKNOWN",
            "true_action_count": "UNKNOWN",
            "production_release": False,
        }

        with zipfile.ZipFile(package_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in generated_files:
                archive.write(path, arcname=path.relative_to(temp_root).as_posix())
            archive.writestr(
                "HPFA_PACKAGE_MANIFEST.json",
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            )

    return {
        "status": runtime_payload.get("status"),
        "package_path": str(package_path),
        "package_size_bytes": package_path.stat().st_size,
        "package_sha256": _sha256(package_path),
        "exact_git_head": manifest["exact_git_head"],
        "input_surface_count": manifest["input_surface_count"],
        "artifact_count": manifest["artifact_count"],
        "current_occurrence_status": manifest["current_occurrence_status"],
        "current_occurrence_candidate_count": manifest["current_occurrence_candidate_count"],
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the current occurrence-gated ACTIVE_MATCH spine and emit one compressed evidence package."
    )
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    payload = build_package(args.input_dir, args.out_dir)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if payload.get("status") == "FAIL_CLOSED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
