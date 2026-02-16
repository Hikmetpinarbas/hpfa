import json
from pathlib import Path

def test_ssot_version_gate_canon_hashes_version_is_v1_2_0():
    """
    Fail-closed SSOT version gate.
    If SSOT moves, this test forces an explicit bump and prevents silent drift.
    """
    p = Path("canon/canon_hashes.json")
    assert p.exists(), "canon_hashes.json missing (fail-closed)"

    data = json.loads(p.read_text(encoding="utf-8"))

    assert data.get("algo") == "sha256", "canon_hashes algo must be sha256 (fail-closed)"
    assert data.get("version") == "v1.2.0", "canon_hashes SSOT version drift (fail-closed)"

    files = data.get("files")
    assert isinstance(files, dict) and files, "canon_hashes files must be a non-empty dict (fail-closed)"
