from adapters.engine.engine_adapter import adapt_engine_events


def test_lossy_mapping_sets_signal(tmp_path):
    m = tmp_path / "map.json"
    m.write_text('{"PRESSURE": {"canon_action":"PRESSURE","lossy": true, "assumption_id":"00000000-0000-0000-0000-000000000003"}}', encoding="utf-8")

    engine_events = [{"action": "PRESSURE", "p": 1}]
    canon_events, quarantine = adapt_engine_events(engine_events, str(m))

    assert len(quarantine) == 0
    assert len(canon_events) == 1
    assert canon_events[0].meta.epistemic_status.value == "signal"
    assert canon_events[0].meta.lossy_mapping is True
