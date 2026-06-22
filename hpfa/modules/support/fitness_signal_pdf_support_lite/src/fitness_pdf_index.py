from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "fitness_signal_pdf_support_lite_v1"
CLAIM_SAFETY = "SUPPORT_SIGNAL_ONLY"
OUTPUT_JSON = "fitness_signal_pdf_index_v1.json"
OUTPUT_TXT = "fitness_signal_pdf_index_v1.txt"


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def _ensure_module_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _spine_runner_module(root: Path):
    src = root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src"
    _ensure_module_path(src)
    import spine_runner  # type: ignore

    return spine_runner


def support_type_from_name(name: str) -> str:
    text = name.lower()
    if "gps" in text:
        return "GPS_SUPPORT_PDF"
    if "hrv" in text:
        return "HRV_SUPPORT_PDF"
    if "wellness" in text:
        return "WELLNESS_SUPPORT_PDF"
    if "rpe" in text:
        return "RPE_SUPPORT_PDF"
    if "load" in text or "fitness" in text or "physical" in text:
        return "LOAD_FITNESS_SUPPORT_PDF"
    return "UNCLASSIFIED_FITNESS_SUPPORT_PDF"


def build_index(active_match_dir: str | Path) -> dict[str, Any]:
    root = Path(active_match_dir).expanduser().resolve(strict=False)
    pdfs = sorted([p for p in root.rglob("*.pdf") if p.is_file()], key=lambda p: str(p).lower())
    rows = []
    for p in pdfs:
        stat = p.stat()
        rows.append({
            "source_file": p.name,
            "relative_path": str(p.relative_to(root)),
            "size_bytes": stat.st_size,
            "source_role": "ACTIVE_MATCH_ADJACENT_SUPPORT_DOCUMENT",
            "support_signal_type": support_type_from_name(p.name),
            "runtime_event_truth": False,
            "extraction_status": "PDF_PRESENT_EXTRACTION_PENDING",
            "claim_boundary": "support_signal_only_no_fatigue_truth_no_tactical_truth",
        })
    status = "PDF_INDEX_PASS" if rows else "NO_FITNESS_PDF_FOUND"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "claim_safety": CLAIM_SAFETY,
        "active_match_dir": str(root),
        "pdf_count": len(rows),
        "pdfs": rows,
        "runtime_event_truth": False,
        "allowed_use": [
            "file presence evidence",
            "support-signal availability",
            "later extraction candidate",
        ],
        "blocked_use": [
            "fatigue truth",
            "load truth",
            "injury truth",
            "tactical truth",
            "event truth override",
        ],
    }


def render_txt(index: dict[str, Any]) -> str:
    lines = [
        "HPFA FITNESS SIGNAL PDF SUPPORT LITE V1",
        "========================================",
        f"status={index.get('status')}",
        f"claim_safety={index.get('claim_safety')}",
        f"active_match_dir={index.get('active_match_dir')}",
        f"pdf_count={index.get('pdf_count')}",
        f"runtime_event_truth={index.get('runtime_event_truth')}",
        "",
        "[pdfs]",
    ]
    for row in index.get("pdfs", []):
        lines.append(json.dumps(row, ensure_ascii=False, sort_keys=True))
    lines.extend(["", "[allowed_use]"])
    for item in index.get("allowed_use", []):
        lines.append(f"- {item}")
    lines.extend(["", "[blocked_use]"])
    for item in index.get("blocked_use", []):
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(active_match_dir: str | Path, out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine_runner = _spine_runner_module(repo_root)
    output_root = spine_runner.validate_output_root(out_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    index = build_index(active_match_dir)
    json_out = output_root / OUTPUT_JSON
    txt_out = output_root / OUTPUT_TXT
    index["output_root"] = str(output_root)
    index["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(index), encoding="utf-8")
    return index
