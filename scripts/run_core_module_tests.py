from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FUSION_SOURCE = REPO_ROOT / "hpfa" / "modules" / "core" / "multi_signal_evidence_fusion_lite" / "src" / "multi_signal_evidence_fusion.py"
FUSION_TESTS = REPO_ROOT / "hpfa" / "modules" / "core" / "multi_signal_evidence_fusion_lite" / "tests"


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def main() -> int:
    run([sys.executable, "-m", "py_compile", str(FUSION_SOURCE)])
    run([sys.executable, "-m", "pytest", str(FUSION_TESTS), "-q"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
