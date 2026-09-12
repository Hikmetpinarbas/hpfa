from __future__ import annotations

import inspect
import json

import trackable_action_trace_candidates_current_v1 as current


def test_current_runtime_binds_interval_after_temporal_admission_before_trace_write() -> None:
    source = inspect.getsource(current.runtime_write_outputs)
    temporal_pos = source.index("bind_temporal_relation_admission")
    interval_pos = source.index("_write_interval_projection")
    trace_write_pos = source.index("trackable.write_outputs")

    assert temporal_pos < interval_pos < trace_write_pos
    assert "current_actor_acquisition_release_interval_projection_bound" in source
    assert "observed_actor_acquisition_release_interval_projection_v1.json" not in source


def test_interval_binding_writes_sidecar_and_lightweight_runtime_metadata(
    tmp_path, monkeypatch
) -> None:
    projection = {
        "status": "REVIEW_REQUIRED",
        "observed_actor_acquisition_release_interval_candidate_count": 2,
        "claim_ceiling": "OBSERVED_ACTOR_ACQUISITION_TO_RELEASE_START_INTERVAL_CANDIDATE_ONLY",
        "projection_creates_new_evidence": False,
        "projection_reconstructs_sequences": False,
        "canonical_event_count": "UNKNOWN",
        "true_action_count": "UNKNOWN",
        "production_release": False,
    }
    monkeypatch.setattr(
        current,
        "build_observed_actor_acquisition_release_interval_projection",
        lambda payload: dict(projection),
    )
    payload = {"status": "PASS", "module_status": "PASS", "review_hits": []}

    report = current._write_interval_projection(payload, tmp_path)

    sidecar = tmp_path / current.INTERVAL_OUTPUT_JSON
    assert sidecar.is_file()
    assert json.loads(sidecar.read_text(encoding="utf-8")) == projection
    assert report == projection
    assert payload["current_actor_acquisition_release_interval_projection_bound"] is True
    assert payload["current_actor_acquisition_release_interval_status"] == "REVIEW_REQUIRED"
    assert payload["current_actor_acquisition_release_interval_candidate_count"] == 2
    assert payload["current_actor_acquisition_release_interval_projection_creates_new_evidence"] is False
    assert payload["current_actor_acquisition_release_interval_projection_reconstructs_sequences"] is False
    assert payload["status"] == "PASS"


def test_interval_projection_fail_closed_is_lane_local_not_trace_hard_block(
    tmp_path, monkeypatch
) -> None:
    projection = {
        "status": "FAIL_CLOSED",
        "observed_actor_acquisition_release_interval_candidate_count": 0,
        "claim_ceiling": "OBSERVED_ACTOR_ACQUISITION_TO_RELEASE_START_INTERVAL_CANDIDATE_ONLY",
        "projection_creates_new_evidence": False,
        "projection_reconstructs_sequences": False,
    }
    monkeypatch.setattr(
        current,
        "build_observed_actor_acquisition_release_interval_projection",
        lambda payload: dict(projection),
    )
    payload = {"status": "PASS", "module_status": "PASS", "review_hits": []}

    current._write_interval_projection(payload, tmp_path)

    assert payload["status"] == "REVIEW_REQUIRED"
    assert payload["module_status"] == "REVIEW_REQUIRED"
    assert "actor_acquisition_release_interval_projection_fail_closed" in payload["review_hits"]
