from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "composite_integration_office" / "src"
sys.path.insert(0, str(SRC))

from boundary_analysis_scorer import score_candidate, score_registry, write_score_registry


def candidate(capability="sequence_engine", source_count=2, sources=None, members=None, active=True):
    return {
        "composite_id": "COMP-TEST",
        "dominant_capability": capability,
        "source_count": source_count,
        "sources": sources or ["TERMUX", "GITHUB"],
        "active_match_validation_required": active,
        "members": members if members is not None else [
            {
                "file_name": "sequence_engine.py",
                "normalized_name": "sequence_engine",
                "source_path": "/tmp/sequence_engine.py",
                "symbols": ["def:step"],
                "dependency_flags": [],
            }
        ],
    }


def test_adapt_ready_for_clean_high_value_candidate():
    scored = score_candidate(candidate(capability="canonical_ingest", source_count=4))

    assert scored["readiness_band"] == "ADAPT_READY"
    assert scored["recommended_action"] == "adapt_candidate"
    assert scored["claim_safety"] == "NO_TRUTH_UNTIL_ACTIVE_MATCH_VALIDATION"
    assert scored["active_match_validation_required"] is True


def test_boundary_review_when_review_terms_present():
    scored = score_candidate(candidate(members=[
        {
            "file_name": "video_control_model.py",
            "normalized_name": "video_control_model",
            "source_path": "/tmp/video_control_model.py",
            "symbols": ["def:estimate"],
            "dependency_flags": [],
        }
    ]))

    assert scored["readiness_band"] == "BOUNDARY_REVIEW"
    assert scored["recommended_action"] == "review_boundary"
    assert scored["risk_flags"]


def test_reference_only_for_unknown_low_score_candidate():
    scored = score_candidate(candidate(capability="unknown", source_count=1, sources=["TERMUX"], members=[]))

    assert scored["readiness_band"] == "REFERENCE_ONLY"
    assert scored["recommended_action"] == "keep_reference_only"


def test_blocked_when_active_match_validation_not_required():
    scored = score_candidate(candidate(active=False))

    assert scored["readiness_band"] == "BLOCKED"
    assert scored["recommended_action"] == "block_candidate"


def test_score_registry_sorts_by_score_from_dict_input():
    registry = {
        "composites": [
            candidate(capability="unknown", source_count=1, sources=["TERMUX"], members=[]),
            candidate(capability="canonical_ingest", source_count=4),
        ]
    }
    scored = score_registry(registry)

    assert scored["status"] == "PASS"
    assert scored["score_count"] == 2
    assert scored["scores"][0]["readiness_score"] >= scored["scores"][1]["readiness_score"]


def test_score_registry_accepts_legacy_list_input():
    scored = score_registry([
        candidate(capability="unknown", source_count=1, sources=["TERMUX"], members=[]),
        candidate(capability="canonical_ingest", source_count=4),
    ])

    assert scored["status"] == "PASS"
    assert scored["score_count"] == 2
    assert scored["scores"][0]["readiness_score"] >= scored["scores"][1]["readiness_score"]


def test_write_score_registry_accepts_list_input(tmp_path):
    src = tmp_path / "composite_registry.json"
    out = tmp_path / "boundary_scores.json"
    src.write_text(json.dumps([candidate(capability="canonical_ingest", source_count=4)]), encoding="utf-8")

    scored = write_score_registry(src, out)
    saved = json.loads(out.read_text(encoding="utf-8"))

    assert scored["status"] == "PASS"
    assert saved["score_count"] == 1
    assert saved["scores"][0]["readiness_band"] == "ADAPT_READY"
