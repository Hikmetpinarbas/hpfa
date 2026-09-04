from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import active_match_full_run as full_run
import context_action_semantics_rebind as semantics_wrapper


def test_projection_review_required_cannot_be_promoted_to_pass() -> None:
    report = {"status": "PASS", "review_hits": []}
    projected = {"status": "REVIEW_REQUIRED", "review_hits": ["identity_review_debt"]}

    semantics_wrapper._inherit_projection_status(report, projected)

    assert report["status"] == "REVIEW_REQUIRED"
    assert "team_attribution:identity_review_debt" in report["review_hits"]


def test_projection_fail_closed_remains_fail_closed() -> None:
    report = {"status": "PASS", "hard_block_hits": []}
    projected = {"status": "FAIL_CLOSED", "hard_block_hits": ["identity_binding_invalid"]}

    semantics_wrapper._inherit_projection_status(report, projected)

    assert report["status"] == "FAIL_CLOSED"
    assert "team_attribution:identity_binding_invalid" in report["hard_block_hits"]


def test_primary_identity_step_reuses_existing_row_payload_without_upstream_recompute(
    tmp_path: Path,
    monkeypatch,
) -> None:
    row_payload = {
        "module_id": "row_nucleus_inventory_lite_v1",
        "status": "PASS",
        "canonical_event_count": "UNKNOWN",
        "production_release": False,
    }
    row_path = tmp_path / full_run.ROW_NUCLEUS_JSON
    row_path.write_text(json.dumps(row_payload), encoding="utf-8")

    calls: list[tuple[str, object]] = []

    def write_atoms(existing_row_payload, input_dir, out_dir):
        calls.append(("atoms", existing_row_payload))
        assert existing_row_payload is not None
        return {
            "status": "REVIEW_REQUIRED",
            "evidence_atom_count": 3,
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        }

    def write_identity(existing_evidence, out_dir):
        calls.append(("identity", existing_evidence))
        assert existing_evidence["evidence_atom_count"] == 3
        return {
            "status": "REVIEW_REQUIRED",
            "identity_candidate_bound_atom_count": 2,
            "team_subject_code_prefix_bridge_applied_count": 1,
            "canonical_event_count": "UNKNOWN",
            "production_release": False,
        }

    fake_atoms = SimpleNamespace(
        write_outputs_from_existing_row_payload=write_atoms,
        runtime_write_outputs=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("upstream Row Nucleus must not be recomputed")
        ),
    )
    fake_identity = SimpleNamespace(
        write_outputs_from_existing_evidence=write_identity,
        runtime_write_outputs=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("Evidence Atom must not be recomputed")
        ),
    )
    monkeypatch.setitem(sys.modules, "evidence_atom_inventory_lite", fake_atoms)
    monkeypatch.setitem(sys.modules, "match_local_identity_candidates_lite", fake_identity)

    result = full_run.run_identity_inputs_step(tmp_path, tmp_path, tmp_path, row_path)

    assert result["passed"] is True
    assert result["returncode"] == 0
    assert [name for name, _payload in calls] == ["atoms", "identity"]


def test_core_loader_uses_distinct_module_identity() -> None:
    source = Path(semantics_wrapper.__file__).read_text(encoding="utf-8")
    assert "hpfa_context_action_semantics_rebind_core_v1" in source
    assert "hpfa_team_attribution_projection_core_v1" in source
    assert "import context_action_semantics_rebind as core" not in source


def test_no_sample_match_identity_leak() -> None:
    paths = [
        Path(full_run.__file__),
        Path(semantics_wrapper.__file__),
        Path("evidence_atom_inventory_lite.py"),
        Path("match_local_identity_candidates_lite.py"),
    ]
    text = "\n".join(path.read_text(encoding="utf-8").casefold() for path in paths)
    forbidden = ["fenerbah", "genclerbir", "15.08.2026", "27041", "29575"]
    assert not any(token in text for token in forbidden)
