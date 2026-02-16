from __future__ import annotations

import json
import hashlib
from pathlib import Path


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_canon_hash_gate():
    mf = Path("canon/canon_hashes.json")
    assert mf.exists(), "canon/canon_hashes.json must exist (fail-closed)"

    d = json.loads(mf.read_text(encoding="utf-8"))
    assert isinstance(d, dict), "manifest root must be dict"
    assert d.get("algo") == "sha256", "manifest algo must be sha256"

    files = d.get("files")
    assert isinstance(files, dict) and files, "manifest.files must be non-empty dict"

    for rel, expected in files.items():
        assert isinstance(rel, str) and rel.strip(), "manifest path keys must be non-empty strings"
        assert isinstance(expected, str) and expected.strip(), f"missing hash for {rel}"

        p = Path(rel)
        assert p.exists(), f"canon file missing: {rel}"

        actual = _sha256(p)
        assert actual == expected.strip(), f"hash mismatch for {rel}"
