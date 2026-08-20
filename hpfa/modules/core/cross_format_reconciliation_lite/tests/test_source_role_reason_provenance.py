from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]


def test_source_role_reason_provenance_isolated_from_core_test_process() -> None:
    code = r'''
import importlib.util
from pathlib import Path

root = Path.cwd()
wrapper_path = root / "cross_format_reconciliation_lite.py"
spec = importlib.util.spec_from_file_location("cross_format_reconciliation_runtime_wrapper", wrapper_path)
assert spec and spec.loader
wrapper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrapper)

relational = {
    "resolution_status": "ROLE_CANDIDATE_ADMITTED",
    "resolution_reasons": [
        "CONTENT_ROLE_EVIDENCE_INSUFFICIENT",
        "AGGREGATE_SEMANTIC_UNIQUE_BEST_SUPPORT",
    ],
}
assert wrapper.admitted_role_reasons(relational) == [
    "AGGREGATE_SEMANTIC_UNIQUE_BEST_SUPPORT"
]

unresolved = {
    "resolution_status": "REVIEW_REQUIRED",
    "resolution_reasons": ["CONTENT_ROLE_EVIDENCE_INSUFFICIENT"],
}
assert wrapper.admitted_role_reasons(unresolved) == [
    "CONTENT_ROLE_EVIDENCE_INSUFFICIENT"
]

admitted_direct = {
    "resolution_status": "ROLE_CANDIDATE_ADMITTED",
    "resolution_reasons": [
        "CONTENT_ROLE_EVIDENCE_INSUFFICIENT",
        "REVIEWED_PROVIDER_ROLE_SEMANTICS",
    ],
}
assert wrapper.admitted_role_reasons(admitted_direct) == [
    "CONTENT_ROLE_EVIDENCE_INSUFFICIENT",
    "REVIEWED_PROVIDER_ROLE_SEMANTICS",
]

payload = {
    "files": [
        {
            "relative_path": "generic.csv",
            "source_role": "UNRESOLVED_SOURCE_ROLE_CANDIDATE",
        }
    ]
}
role_index = {
    "generic.csv": {
        "resolution_status": "ROLE_CANDIDATE_ADMITTED",
        "resolved_source_role": "PLAYER_SURFACE_CANDIDATE",
        "resolution_reasons": [
            "CONTENT_ROLE_EVIDENCE_INSUFFICIENT",
            "CROSS_FORMAT_UNIQUE_BEST_VISIBLE_FINGERPRINT_SUPPORT",
        ],
    }
}
result = wrapper._overlay_resolved_roles(payload, role_index)
row = result["files"][0]
assert row["source_role"] == "PLAYER_SURFACE_CANDIDATE"
assert row["inventory_source_role"] == "UNRESOLVED_SOURCE_ROLE_CANDIDATE"
assert row["source_role_resolution_reasons"] == [
    "CROSS_FORMAT_UNIQUE_BEST_VISIBLE_FINGERPRINT_SUPPORT"
]
assert row["filename_support_used_for_role_admission"] is False
'''
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
