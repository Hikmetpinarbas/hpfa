from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

MODULE_ID = "reasoning_grammar_spine_lite_v1"
OUTPUT_JSON = "reasoning_grammar_spine_lite_v1.json"
OUTPUT_TXT = "reasoning_grammar_spine_lite_v1.txt"

ACTION_TO_PRIMITIVE = {
    "PASS": "pass_surface_candidate",
    "CARRY_DRIBBLE": "carry_progression_surface_candidate",
    "RECOVERY": "recovery_surface_candidate",
    "BALL_LOSS": "loss_surface_candidate",
    "SHOT": "terminal_action_surface_candidate",
}


def repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[5]


def ensure_path(path: Path) -> None:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


def spine_runner_module(root: Path):
    ensure_path(root / "hpfa" / "modules" / "core" / "active_match_spine_runner" / "src")
    import spine_runner  # type: ignore
    return spine_runner


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def confidence(count: int) -> str:
    if count >= 500:
        return "strong"
    if count >= 50:
        return "medium"
    return "weak"


def build_report(out_dir: str | Path) -> dict[str, Any]:
    out = Path(out_dir)
    postmatch = read_json(out / "postmatch_analyst_report_lite_v1.json")
    tc = postmatch.get("team_comparison") or {}
    teams = [("left", str(tc.get("left_team", "TEAM_A"))), ("right", str(tc.get("right_team", "TEAM_B")))]
    rows = postmatch.get("action_family_comparison") or []
    candidates = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        metric = str(row.get("metric"))
        primitive = ACTION_TO_PRIMITIVE.get(metric)
        if not primitive:
            continue
        for side, team in teams:
            key = "left" if side == "left" else "right"
            count = int(row.get(key, 0) or 0)
            if count > 0:
                candidates.append({
                    "team": team,
                    "primitive_candidate": primitive,
                    "source_metric": metric,
                    "evidence_count": count,
                    "confidence": confidence(count),
                    "falsifier": "Candidate weakens if later source evidence shows the primitive surface is not repeated.",
                    "claim_boundary": "primitive evidence only",
                })
    candidates.sort(key=lambda item: int(item["evidence_count"]), reverse=True)
    return {
        "module_id": MODULE_ID,
        "status": "REVIEW_REQUIRED",
        "claim_safety": "PRIMITIVE_EVIDENCE_ONLY",
        "stage": "primitive_only",
        "canonical_event_count": "UNKNOWN",
        "candidate_count": len(candidates),
        "primitive_candidates": candidates,
        "stage_gate": {
            "sequence_candidate_allowed": False,
            "behaviour_candidate_allowed": False,
            "pattern_candidate_allowed": False,
            "identity_candidate_allowed": False,
            "match_story_allowed": False,
        },
    }


def render_txt(report: dict[str, Any]) -> str:
    lines = ["HPFA REASONING GRAMMAR SPINE LITE V1", f"status={report['status']}", f"stage={report['stage']}", f"candidate_count={report['candidate_count']}", "", "[primitive_candidates]"]
    for item in report.get("primitive_candidates", [])[:10]:
        lines.append(f"- {item['team']}: {item['primitive_candidate']} {item['evidence_count']} confidence={item['confidence']}")
    lines.append("")
    return "\n".join(lines)


def write_outputs(out_dir: str | Path, root: str | Path | None = None) -> dict[str, Any]:
    repo_root = Path(root).resolve() if root is not None else repo_root_from_file()
    out = spine_runner_module(repo_root).validate_output_root(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = build_report(out)
    json_out = out / OUTPUT_JSON
    txt_out = out / OUTPUT_TXT
    report["outputs"] = {"json": str(json_out), "txt": str(txt_out)}
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    txt_out.write_text(render_txt(report), encoding="utf-8")
    return report
