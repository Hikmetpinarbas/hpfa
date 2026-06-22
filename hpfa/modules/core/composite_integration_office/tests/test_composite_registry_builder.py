from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "composite_integration_office" / "src"
sys.path.insert(0, str(SRC))

from composite_registry_builder import build_composite_registry, write_composite_registry
from source_intake_normalizer import discovery_fingerprint, normalize_intake


def record(source_system, title, capability_family, hpfa_capability):
    return {
        "source_system": source_system,
        "title": title,
        "source_path": f"{source_system.lower()}://example",
        "capability_family": capability_family,
        "hpfa_capability": hpfa_capability,
        "claim_safety": "REFERENCE_ONLY",
    }


def test_normalize_intake_rejects_unknown_source():
    try:
        normalize_intake(record("UNKNOWN", "x", "sequence", "sequence_engine"))
    except ValueError as exc:
        assert "unsupported source_system" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_duplicate_discoveries_merge_under_one_composite():
    rows = [
        record("GOOGLE_DRIVE", "Sequence Donor", "sequence", "sequence_engine"),
        record("DROPBOX", "Sequence Donor", "sequence", "sequence_engine"),
        record("SIDER_SCHOLAR", "Sequence Donor", "sequence", "sequence_engine"),
    ]
    registry = build_composite_registry(rows)

    assert registry["status"] == "PASS"
    assert registry["composite_count"] == 1
    comp = registry["composites"][0]
    assert comp["source_count"] == 3
    assert comp["dominant_capability"] == "sequence_engine"
    assert comp["target_hpfa_engine"] == "Sequence Intelligence Engine"
    assert comp["active_match_validation_required"] is True
    assert comp["claim_safety"] == "NO_TRUTH_UNTIL_ACTIVE_MATCH_VALIDATION"


def test_distinct_discoveries_create_distinct_composites():
    rows = [
        record("GITHUB", "Metric Fusion", "metric", "metric_fusion"),
        record("DROPBOX", "Common Data Format", "ontology", "canonical_ingest"),
    ]
    registry = build_composite_registry(rows)

    assert registry["composite_count"] == 2
    engines = {c["target_hpfa_engine"] for c in registry["composites"]}
    assert "Metric Fusion Engine" in engines
    assert "Canonical Ingest Engine" in engines


def test_fingerprint_is_stable_for_same_capability():
    a = normalize_intake(record("GITHUB", "Same Name", "metric", "metric_fusion"))
    b = normalize_intake(record("DROPBOX", "Same Name", "metric", "metric_fusion"))

    assert discovery_fingerprint(a) == discovery_fingerprint(b)


def test_write_composite_registry(tmp_path):
    out = tmp_path / "composite_registry.json"
    registry = write_composite_registry([
        record("TERMUX", "Surface scan", "canonical", "canonical_ingest")
    ], out)

    assert out.exists()
    assert registry["composite_count"] == 1
    assert registry["runtime_truth_authority"] == "ACTIVE_MATCH_EXECUTION_ONLY"
