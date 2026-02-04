from adapters.engine.engine_adapter import adapt_engine_events


def test_unmapped_goes_to_quarantine(tmp_path):
    m = tmp_path / "map.json"
    m.write_text('{"PASS": {"canon_action":"PASS","lossy": false, "assumption_id":"00000000-0000-0000-0000-000000000001"}}', encoding="utf-8")

    engine_events = [{"action": "UNKNOWN_THING", "x": 1}]
    canon_events, quarantine = adapt_engine_events(engine_events, str(m))

    assert canon_events == []
    assert len(quarantine) == 1
    assert quarantine[0].reason == "UNMAPPED_ACTION"
