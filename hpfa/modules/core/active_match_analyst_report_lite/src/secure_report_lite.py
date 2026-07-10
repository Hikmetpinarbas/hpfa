from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import report_lite as legacy

OUTPUT_JSON = legacy.OUTPUT_JSON
OUTPUT_TXT = legacy.OUTPUT_TXT


def _secure_manifest_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "canonical_ingest_surface_manifest" / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import secure_surface_manifest  # type: ignore

    return secure_surface_manifest


def write_report(active_match_dir: str | Path, out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else legacy.repo_root_from_file()
    active_path = Path(active_match_dir).expanduser().resolve(strict=False)
    secure_manifest = _secure_manifest_module(repo_root).build_manifest(str(active_path))
    if secure_manifest.get("status") == "FAIL_CLOSED" and secure_manifest.get("security_failures"):
        spine = legacy._spine_runner_module(repo_root)
        output_root = spine.validate_output_root(out_dir)
        output_root.mkdir(parents=True, exist_ok=True)
        report = {
            "module_id": legacy.MODULE_ID,
            "status": "FAIL_CLOSED",
            "claim_safety": legacy.CLAIM_SAFETY,
            "active_match_dir": str(active_path),
            "canonical_event_count": "UNKNOWN",
            "security_failures": secure_manifest.get("security_failures", []),
            "analyst_reading": [],
            "technical_limits": ["surface_security_gate_failed"],
            "engineering_evidence": {
                "surface_manifest_status": "FAIL_CLOSED",
                "output_root": str(output_root),
                "out_json": str(output_root / OUTPUT_JSON),
                "out_txt": str(output_root / OUTPUT_TXT),
            },
        }
        (output_root / OUTPUT_JSON).write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        (output_root / OUTPUT_TXT).write_text(
            "HPFA ACTIVE_MATCH ANALYST REPORT LITE V1\nstatus=FAIL_CLOSED\nreason=surface_security_gate_failed\n",
            encoding="utf-8",
        )
        return report
    return legacy.write_report(active_match_dir, out_dir, root=repo_root)
