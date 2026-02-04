import json
from pathlib import Path
from typing import Set


def load_baseline_actions(path: Path) -> Set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    actions = data.get("provider_actions", [])
    return set(str(a) for a in actions)


def current_report_actions(path: Path) -> Set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: Set[str] = set()
    for row in data.get("unmapped_actions", []):
        out.add(str(row.get("provider_action", "")).strip())
    return {a for a in out if a}


def assert_no_new_actions(*, report_path: Path, baseline_path: Path) -> None:
    baseline = load_baseline_actions(baseline_path)
    current = current_report_actions(report_path)
    new = sorted(a for a in current if a not in baseline)
    if new:
        raise AssertionError(
            "New provider_action(s) not in baseline:\n- "
            + "\n- ".join(new)
            + "\n\nIf intentional, add them to reports/unmapped_actions.baseline.json"
        )
