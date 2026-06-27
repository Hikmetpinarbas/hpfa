from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

MODULE_ID = "active_match_identity_guard_lite_v1"
CLAIM_SAFETY = "RUNTIME_IDENTITY_CHECK_ONLY"
CANONICAL_EVENT_COUNT = "UNKNOWN"
OUTPUT_JSON = "active_match_identity_guard_lite_v1.json"
OUTPUT_TXT = "active_match_identity_guard_lite_v1.txt"
SURFACE_SUFFIXES = {".csv", ".xml", ".xlsx", ".pdf", ".json", ".txt"}
BLOCKED_TRUTH_FLAGS = {
    "event_truth": False,
    "phase_truth": False,
    "possession_truth": False,
    "sequence_truth": False,
    "rhythm_truth": False,
    "tactical_truth": False,
    "dominance_truth": False,
}


MONTH_PATTERN = re.compile(r"(?:19|20)\d{2}")
DATE_PATTERN = re.compile(r"(?:\d{4}[-_.]\d{2}[-_.]\d{2}|\d{2}[-_.]\d{2}[-_.]\d{4})")
SCORE_PATTERN = re.compile(r"\b\d+\s*[-–]\s*\d+\b")


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


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_identity_token(value: Any) -> str:
    raw = clean_text(value).lower()
    raw = re.sub(r"\.[a-z0-9]+$", "", raw)
    raw = re.sub(r"[^a-z0-9]+", " ", raw)
    raw = re.sub(r"\b(full|match|teams|players|goalkeepers|team|player|goalkeeper|csv|xml|xlsx|pdf|json|txt)\b", " ", raw)
    raw = re.sub(r"\b\d{1,6}\b", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw


def list_runtime_files(active_match_dir: str | Path) -> list[Path]:
    root = Path(active_match_dir)
    if not root.exists() or not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_file() and p.suffix.lower() in SURFACE_SUFFIXES)


def extract_identity_candidates_from_files(files: list[Path]) -> dict[str, Any]:
    label_counter: Counter[str] = Counter()
    date_counter: Counter[str] = Counter()
    score_counter: Counter[str] = Counter()
    competition_counter: Counter[str] = Counter()

    for path in files:
        stem = path.stem
        token = normalize_identity_token(stem)
        if token:
            label_counter[token] += 1
        for date in DATE_PATTERN.findall(path.name):
            date_counter[date] += 1
        for year in MONTH_PATTERN.findall(path.name):
            date_counter[year] += 0
        for score in SCORE_PATTERN.findall(path.name):
            score_counter[re.sub(r"\s+", "", score)] += 1
        lowered = path.name.lower()
        for word in ["world cup", "uefa", "fifa", "league", "cup", "qualifier"]:
            if word in lowered:
                competition_counter[word] += 1

    return {
        "source": "runtime_file_inventory",
        "surface_file_count": len(files),
        "match_label_candidates": [k for k, _ in label_counter.most_common(10)],
        "date_candidates": [k for k, _ in date_counter.most_common(10)],
        "score_candidates": [k for k, _ in score_counter.most_common(10)],
        "competition_candidates": [k for k, _ in competition_counter.most_common(10)],
    }


def read_declared_identity(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {"source": "UNKNOWN", "match_label": "UNKNOWN", "date": "UNKNOWN", "competition": "UNKNOWN"}
    p = Path(path)
    if not p.exists() or not p.is_file():
        return {"source": str(p), "match_label": "UNKNOWN", "date": "UNKNOWN", "competition": "UNKNOWN"}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        text = p.read_text(encoding="utf-8", errors="ignore")[:2000]
        return {
            "source": str(p),
            "match_label": clean_text(text.splitlines()[0] if text.splitlines() else "UNKNOWN") or "UNKNOWN",
            "date": "UNKNOWN",
            "competition": "UNKNOWN",
        }
    if not isinstance(data, dict):
        return {"source": str(p), "match_label": "UNKNOWN", "date": "UNKNOWN", "competition": "UNKNOWN"}
    nested = data.get("match") if isinstance(data.get("match"), dict) else data
    return {
        "source": str(p),
        "match_label": clean_text(nested.get("match_label") or nested.get("match") or nested.get("name") or "UNKNOWN") or "UNKNOWN",
        "date": clean_text(nested.get("date") or nested.get("match_date") or "UNKNOWN") or "UNKNOWN",
        "competition": clean_text(nested.get("competition") or nested.get("tournament") or "UNKNOWN") or "UNKNOWN",
    }


def compare_identity(declared: dict[str, Any], observed: dict[str, Any]) -> tuple[str, bool, list[str]]:
    reasons: list[str] = []
    declared_label = normalize_identity_token(declared.get("match_label"))
    declared_date = clean_text(declared.get("date"))
    declared_comp = normalize_identity_token(declared.get("competition"))
    labels = [normalize_identity_token(v) for v in observed.get("match_label_candidates", [])]
    dates = [clean_text(v) for v in observed.get("date_candidates", [])]
    comps = [normalize_identity_token(v) for v in observed.get("competition_candidates", [])]

    if observed.get("surface_file_count", 0) == 0:
        return "NO_RUNTIME_SURFACES_FOUND", False, ["active_match_dir_missing_or_empty"]

    if declared_label in {"", "unknown"} and declared_date in {"", "UNKNOWN"} and declared_comp in {"", "unknown"}:
        return "UNKNOWN_OR_REVIEW_REQUIRED", False, ["declared_identity_missing"]

    contradiction = False
    if declared_label and declared_label != "unknown" and labels:
        if not any(declared_label in label or label in declared_label for label in labels if label):
            contradiction = True
            reasons.append("match_label_contradiction")
    if declared_date and declared_date != "UNKNOWN" and dates:
        if declared_date not in dates:
            contradiction = True
            reasons.append("date_contradiction")
    if declared_comp and declared_comp != "unknown" and comps:
        if not any(declared_comp in comp or comp in declared_comp for comp in comps if comp):
            contradiction = True
            reasons.append("competition_contradiction")

    if contradiction:
        return "RUNTIME_IDENTITY_DRIFT_DETECTED", False, reasons
    if not labels:
        return "UNKNOWN_OR_REVIEW_REQUIRED", False, ["observed_identity_missing"]
    return "ACTIVE_MATCH_IDENTITY_COMPATIBLE_REVIEW_REQUIRED", True, ["no_identity_contradiction_detected"]


def build_report(active_match_dir: str | Path, declared_manifest_path: str | Path | None = None) -> dict[str, Any]:
    files = list_runtime_files(active_match_dir)
    observed = extract_identity_candidates_from_files(files)
    declared = read_declared_identity(declared_manifest_path)
    identity_status, allowed, reasons = compare_identity(declared, observed)
    if identity_status == "RUNTIME_IDENTITY_DRIFT_DETECTED" or identity_status == "NO_RUNTIME_SURFACES_FOUND":
        status = "FAIL_CLOSED"
    elif allowed:
        status = "REVIEW_REQUIRED"
    else:
        status = "REVIEW_REQUIRED"
    return {
        "module_id": MODULE_ID,
        "status": status,
        "claim_safety": CLAIM_SAFETY,
        "input_authority": "ACTIVE_MATCH_RUNTIME_AUTHORITY",
        "active_match_dir": str(Path(active_match_dir)),
        "declared_identity": declared,
        "observed_identity": observed,
        "identity_match_status": identity_status,
        "identity_reasons": reasons,
        "active_match_evidence_allowed": allowed,
        "canonical_event_count": CANONICAL_EVENT_COUNT,
        "claim_boundary": dict(BLOCKED_TRUTH_FLAGS),
        "blocked_claims": [
            "match truth validated",
            "event truth",
            "phase truth",
            "possession truth",
            "sequence truth",
            "rhythm truth",
            "tactical truth",
            "dominance truth",
        ],
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = [
        "HPFA ACTIVE MATCH IDENTITY GUARD LITE V1",
        "========================================",
        f"status={report.get('status')}",
        f"claim_safety={report.get('claim_safety')}",
        f"identity_match_status={report.get('identity_match_status')}",
        f"active_match_evidence_allowed={report.get('active_match_evidence_allowed')}",
        f"canonical_event_count={report.get('canonical_event_count')}",
        "",
        "[declared_identity]",
        json.dumps(report.get("declared_identity"), ensure_ascii=False, sort_keys=True),
        "",
        "[observed_identity]",
        json.dumps(report.get("observed_identity"), ensure_ascii=False, sort_keys=True),
        "",
        "[claim_boundary]",
        json.dumps(report.get("claim_boundary"), ensure_ascii=False, sort_keys=True),
        "",
        "[blocked_claims]",
    ]
    for claim in report.get("blocked_claims", []):
        lines.append(f"- {claim}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(active_match_dir: str | Path, out_dir: str | Path, declared_manifest_path: str | Path | None = None, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    spine_runner = _spine_runner_module(repo_root)
    out = spine_runner.validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_report(active_match_dir, declared_manifest_path)
    json_out = out / OUTPUT_JSON
    txt_out = out / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
