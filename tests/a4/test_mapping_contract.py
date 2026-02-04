import json
import tempfile
from adapters.engine.mapping_contract import load_action_map


def test_mapping_requires_keys():
    bad = {"PASS": {"canon_action": "PASS", "lossy": False}}  # missing assumption_id
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=True) as f:
        json.dump(bad, f)
        f.flush()
        try:
            load_action_map(f.name)
            raise AssertionError("Expected ValueError for missing key")
        except ValueError:
            pass
