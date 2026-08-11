from __future__ import annotations

import hashlib
import pathlib
import sys

import pytest

SRC = pathlib.Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import runtime_source_guard as guard


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def runtime(tmp_path: pathlib.Path) -> pathlib.Path:
    root = tmp_path / "runtime" / "active_single_match" / "current"
    root.mkdir(parents=True)
    return root


def payloads(root: pathlib.Path):
    xlsx_bytes = b"xlsx-current"
    csv_bytes = b"csv-current"
    xml_bytes = b"xml-current"
    (root / "players.xlsx").write_bytes(xlsx_bytes)
    (root / "players.csv").write_bytes(csv_bytes)
    (root / "players.xml").write_bytes(xml_bytes)
    xlsx = {
        "files": [{"sheets": [{"rows": [{
            "relative_path": "players.xlsx",
            "source_sha256": digest(xlsx_bytes),
        }]}]}]
    }
    evidence = {
        "evidence_atoms": [{
            "source_relative_paths": ["players.csv", "players.xml"],
            "source_sha256_lineage": [digest(csv_bytes), digest(xml_bytes)],
        }]
    }
    return xlsx, evidence


def test_current_active_match_sources_pass(tmp_path):
    root = runtime(tmp_path)
    xlsx, evidence = payloads(root)
    out = guard.verify_runtime_sources(root, xlsx, evidence)
    assert out["runtime_source_rehash_status"] == "PASS"
    assert out["runtime_source_file_count"] == 3


def test_stale_xlsx_prerequisite_rejected(tmp_path):
    root = runtime(tmp_path)
    xlsx, evidence = payloads(root)
    (root / "players.xlsx").write_bytes(b"new-match-xlsx")
    with pytest.raises(ValueError, match="prerequisite_source_sha_mismatch:players.xlsx"):
        guard.verify_runtime_sources(root, xlsx, evidence)


def test_stale_event_prerequisite_rejected(tmp_path):
    root = runtime(tmp_path)
    xlsx, evidence = payloads(root)
    (root / "players.csv").write_bytes(b"new-match-csv")
    with pytest.raises(ValueError, match="prerequisite_source_sha_mismatch:players.csv"):
        guard.verify_runtime_sources(root, xlsx, evidence)


def test_missing_current_source_rejected(tmp_path):
    root = runtime(tmp_path)
    xlsx, evidence = payloads(root)
    (root / "players.xml").unlink()
    with pytest.raises(ValueError, match="prerequisite_source_missing:players.xml"):
        guard.verify_runtime_sources(root, xlsx, evidence)


def test_path_escape_rejected(tmp_path):
    root = runtime(tmp_path)
    outside = root.parent / "outside.csv"
    outside.write_bytes(b"outside")
    xlsx, evidence = payloads(root)
    evidence["evidence_atoms"][0]["source_relative_paths"][0] = "../outside.csv"
    evidence["evidence_atoms"][0]["source_sha256_lineage"][0] = digest(b"outside")
    with pytest.raises(ValueError, match="prerequisite_source_path_escape"):
        guard.verify_runtime_sources(root, xlsx, evidence)


def test_non_authority_path_rejected(tmp_path):
    root = tmp_path / "not_current"
    root.mkdir()
    with pytest.raises(ValueError, match="active_match_runtime_authority_mismatch"):
        guard.verify_runtime_sources(root, {}, {})
