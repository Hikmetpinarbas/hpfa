import json
import subprocess
import sys
from pathlib import Path


def test_root_boundary_scorer_cli_accepts_list_input(tmp_path):
    root = Path(__file__).resolve().parents[5]
    src = tmp_path / "composite_registry.json"
    out = tmp_path / "boundary_scores.json"

    src.write_text(json.dumps([
        {
            "composite_id": "COMP-ROOT-CLI",
            "dominant_capability": "canonical_ingest",
            "source_count": 4,
            "sources": ["TERMUX", "GITHUB"],
            "active_match_validation_required": True,
            "members": [
                {
                    "file_name": "canonical_ingest.py",
                    "normalized_name": "canonical_ingest",
                    "source_path": "/tmp/canonical_ingest.py",
                    "symbols": ["def:run"],
                    "dependency_flags": [],
                }
            ],
        }
    ]), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, "-m", "boundary_analysis_scorer", str(src), "--out", str(out)],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    saved = json.loads(out.read_text(encoding="utf-8"))
    assert "status=PASS" in result.stdout
    assert "score_count=1" in result.stdout
    assert saved["score_count"] == 1
    assert saved["scores"][0]["readiness_band"] == "ADAPT_READY"
