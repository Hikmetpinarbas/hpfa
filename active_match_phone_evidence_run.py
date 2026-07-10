from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


RUNNER_ID = "active_match_phone_evidence_run_v1"
DEFAULT_MATCH_DIR = "runtime/active_single_match/current"
PHONE_OUTPUT_ROOT = Path("/sdcard/Download/HPFA")
ALTERNATE_PHONE_OUTPUT_ROOT = Path("/storage/emulated/0/Download/HPFA")
SURFACE_SUFFIXES = {".csv", ".xml", ".xlsx"}
MANIFEST_JSON = "hpfa_test_match_execution_manifest.json"
MANIFEST_TXT = "hpfa_test_match_execution_manifest.txt"
EVIDENCE_ZIP = "HPFA_TEST_MATCH_EVIDENCE_PACK.zip"

EXPECTED_OUTPUTS = (
    "active_match_spine_check_v1.json",
    "active_match_spine_check_v1.txt",
    "active_match_surface_manifest_v1.json",
    "active_match_full_run_lite_v1.json",
    "active_match_full_run_lite_v1.txt",
    "active_match_analyst_report_lite_v1.json",
    "active_match_analyst_report_lite_v1.txt",
    "event_window_builder_lite_v1.json",
    "event_window_builder_lite_v1.txt",
    "time_scale_router_lite_v1.json",
    "time_scale_router_lite_v1.txt",
    "axis_integrity_tagger_lite_v1.json",
    "axis_integrity_tagger_lite_v1.txt",
)

REQUIRED_JSON_STATUSES = {
    "active_match_spine_check_v1.json": {"PASS"},
    "active_match_surface_manifest_v1.json": {"PASS"},
    "active_match_full_run_lite_v1.json": {"REVIEW_REQUIRED"},
    "active_match_analyst_report_lite_v1.json": {"PASS"},
}
BLOCKING_STATUSES = {"", "UNKNOWN", "FAIL", "FAILED", "FAIL_CLOSED", "BLOCKED", "ERROR"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _resolve(root: Path, value: str | Path) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else (root / path).resolve()


def _validate_flat_phone_output(path: Path) -> Path:
    resolved = path.expanduser().resolve(strict=False)
    allowed = {
        PHONE_OUTPUT_ROOT.resolve(strict=False),
        ALTERNATE_PHONE_OUTPUT_ROOT.resolve(strict=False),
    }
    if resolved not in allowed:
        raise ValueError(
            "nested_phone_output_directory_rejected: "
            f"use {PHONE_OUTPUT_ROOT} or {ALTERNATE_PHONE_OUTPUT_ROOT} directly, not {resolved}"
        )
    return resolved


def _surface_files(match_dir: Path) -> list[Path]:
    if not match_dir.exists() or not match_dir.is_dir():
        return []
    return sorted(
        [path for path in match_dir.iterdir() if path.is_file() and path.suffix.lower() in SURFACE_SUFFIXES],
        key=lambda path: path.name.lower(),
    )


def _run(command: list[str], cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    return {
        "command": command,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _owned_artifact_names() -> tuple[str, ...]:
    return (*EXPECTED_OUTPUTS, MANIFEST_JSON, MANIFEST_TXT, EVIDENCE_ZIP)


def _clear_owned_artifacts(output_root: Path) -> list[str]:
    cleared: list[str] = []
    for name in _owned_artifact_names():
        path = output_root / name
        if path.exists() or path.is_symlink():
            if not path.is_file() and not path.is_symlink():
                raise ValueError(f"owned_output_path_not_file:{name}")
            path.unlink()
            cleared.append(name)
    return cleared


def _surface_fingerprints(surfaces: list[Path]) -> list[dict[str, Any]]:
    return [
        {"name": path.name, "size_bytes": path.stat().st_size, "sha256": _sha256(path)}
        for path in surfaces
    ]


def _read_json_object(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, type(exc).__name__
    if not isinstance(value, dict):
        return None, "json_root_not_object"
    return value, None


def _inspect_outputs(output_root: Path) -> dict[str, Any]:
    produced: list[dict[str, Any]] = []
    missing: list[str] = []
    empty: list[str] = []
    malformed_json: list[dict[str, str]] = []
    status_failures: list[dict[str, Any]] = []

    for name in EXPECTED_OUTPUTS:
        path = output_root / name
        if not path.exists() or not path.is_file():
            missing.append(name)
            continue
        size = path.stat().st_size
        if size <= 0:
            empty.append(name)
            continue
        produced.append({"name": name, "size_bytes": size, "sha256": _sha256(path)})
        if path.suffix.lower() != ".json":
            continue
        payload, error = _read_json_object(path)
        if error is not None or payload is None:
            malformed_json.append({"name": name, "error": error or "invalid_json"})
            continue
        status = str(payload.get("status") or "").upper()
        allowed = REQUIRED_JSON_STATUSES.get(name)
        if allowed is not None and status not in allowed:
            status_failures.append({"name": name, "status": status, "allowed": sorted(allowed)})
        elif status in BLOCKING_STATUSES:
            status_failures.append({"name": name, "status": status, "allowed": "non_blocking_status"})

    return {
        "produced": produced,
        "missing": missing,
        "empty": empty,
        "malformed_json": malformed_json,
        "status_failures": status_failures,
    }


def _write_manifest(
    output_root: Path,
    match_dir: Path,
    surfaces: list[Path],
    steps: list[dict[str, Any]],
    cleared_artifacts: list[str],
) -> dict[str, Any]:
    inspection = _inspect_outputs(output_root)
    all_steps_passed = bool(steps) and all(step.get("passed") is True for step in steps)
    semantic_outputs_passed = not any(
        inspection[key] for key in ("missing", "empty", "malformed_json", "status_failures")
    )
    evidence_complete = all_steps_passed and semantic_outputs_passed
    report = {
        "runner_id": RUNNER_ID,
        "status": "ACTIVE_MATCH_EVIDENCE_PASS" if evidence_complete else "FAIL_CLOSED",
        "decision": "PHONE_EVIDENCE_PACK_READY" if evidence_complete else "PHONE_EVIDENCE_PACK_INCOMPLETE",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(_repo_root()),
        "match_dir": str(match_dir),
        "surface_file_count": len(surfaces),
        "surface_files": [path.name for path in surfaces],
        "surface_inputs": _surface_fingerprints(surfaces),
        "steps": steps,
        "engineering_evidence": {
            "all_steps_passed": all_steps_passed,
            "semantic_outputs_passed": semantic_outputs_passed,
            "expected_output_count": len(EXPECTED_OUTPUTS),
            "produced_output_count": len(inspection["produced"]),
            "missing_outputs": inspection["missing"],
            "empty_outputs": inspection["empty"],
            "malformed_json_outputs": inspection["malformed_json"],
            "status_failures": inspection["status_failures"],
            "cleared_preexisting_artifacts": cleared_artifacts,
            "output_root": str(output_root),
        },
        "produced_outputs": inspection["produced"],
        "evidence_zip": str(output_root / EVIDENCE_ZIP),
        "claim_boundary": {
            "canonical_event_count": "UNKNOWN",
            "phase_truth": False,
            "possession_truth": False,
            "sequence_truth": False,
            "rhythm_truth": False,
            "tactical_truth": False,
            "dominance_truth": False,
            "coach_intention_truth": False,
            "off_ball_truth": False,
        },
        "release_status": "ACTIVE_MATCH_EVIDENCE_PASS" if evidence_complete else "FAIL_CLOSED",
        "production_release": False,
    }

    json_path = output_root / MANIFEST_JSON
    txt_path = output_root / MANIFEST_TXT
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "HPFA TEST MATCH EXECUTION MANIFEST V1",
        "====================================",
        f"status={report['status']}",
        f"decision={report['decision']}",
        f"match_dir={report['match_dir']}",
        f"surface_file_count={report['surface_file_count']}",
        f"surface_inputs={json.dumps(report['surface_inputs'], ensure_ascii=False, sort_keys=True)}",
        f"all_steps_passed={all_steps_passed}",
        f"semantic_outputs_passed={semantic_outputs_passed}",
        f"produced_output_count={len(inspection['produced'])}",
        f"missing_outputs={inspection['missing']}",
        f"empty_outputs={inspection['empty']}",
        f"malformed_json_outputs={inspection['malformed_json']}",
        f"status_failures={inspection['status_failures']}",
        f"cleared_preexisting_artifacts={cleared_artifacts}",
        "canonical_event_count=UNKNOWN",
        "production_release=False",
        "",
        "[surface_files]",
        *[f"- {name}" for name in report["surface_files"]],
        "",
        "[steps]",
    ]
    for step in steps:
        lines.append(
            f"- passed={step['passed']} returncode={step['returncode']} "
            f"command={' '.join(step['command'])}"
        )
        if step.get("stderr"):
            lines.append(f"  stderr={step['stderr']}")
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def _write_zip(output_root: Path) -> Path:
    zip_path = output_root / EVIDENCE_ZIP
    names = [name for name in EXPECTED_OUTPUTS if (output_root / name).exists()]
    names.extend([MANIFEST_JSON, MANIFEST_TXT])
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in names:
            path = output_root / name
            if path.exists() and path.is_file():
                archive.write(path, arcname=name)
    return zip_path


def main() -> int:
    root = _repo_root()
    parser = argparse.ArgumentParser(description="Run HPFA ACTIVE_MATCH product chain and write a flat phone evidence pack.")
    parser.add_argument("--match-dir", default=DEFAULT_MATCH_DIR)
    parser.add_argument("--out-dir", default=str(PHONE_OUTPUT_ROOT))
    args = parser.parse_args()

    match_dir = _resolve(root, args.match_dir)
    output_root = _validate_flat_phone_output(Path(args.out_dir))
    output_root.mkdir(parents=True, exist_ok=True)
    cleared_artifacts = _clear_owned_artifacts(output_root)

    surfaces = _surface_files(match_dir)
    if not surfaces:
        report = _write_manifest(output_root, match_dir, surfaces, [], cleared_artifacts)
        _write_zip(output_root)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 1

    steps = [
        _run(
            [sys.executable, "active_match_spine_runner.py", str(match_dir), "--out-dir", str(output_root)],
            root,
        ),
        _run(
            [sys.executable, "active_match_full_run.py", "--match-dir", str(match_dir), "--out-dir", str(output_root)],
            root,
        ),
        _run(
            [sys.executable, "active_match_analyst_report_lite.py", str(match_dir), "--out-dir", str(output_root)],
            root,
        ),
    ]

    report = _write_manifest(output_root, match_dir, surfaces, steps, cleared_artifacts)
    zip_path = _write_zip(output_root)
    print(json.dumps({
        "status": report["status"],
        "decision": report["decision"],
        "surface_file_count": report["surface_file_count"],
        "output_root": str(output_root),
        "evidence_zip": str(zip_path),
    }, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "ACTIVE_MATCH_EVIDENCE_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

