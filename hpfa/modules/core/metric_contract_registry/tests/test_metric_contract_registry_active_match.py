from hpfa.modules.core.metric_contract_registry.src.metric_required_column_gate import evaluate_required_columns
from hpfa.modules.core.metric_contract_registry.src.metric_status_policy_evaluator import evaluate_metric_status
from hpfa.modules.core.metric_contract_registry.src.metric_definition_confidence_audit import audit_definition_confidence


def test_required_column_gate_ok():
    metric = {
        "id": "M_PROG_PASS_COUNT",
        "required_columns": ["event_type", "start_x", "end_x"],
    }
    result = evaluate_required_columns(metric, ["event_type", "start_x", "end_x", "team_id"])
    assert result.status == "OK"
    assert result.missing_columns == ()


def test_required_column_gate_unknown_when_missing_columns():
    metric = {
        "id": "M_PROG_PASS_COUNT",
        "required_columns": ["event_type", "start_x", "end_x"],
    }
    result = evaluate_required_columns(metric, ["event_type", "start_x"])
    assert result.status == "UNKNOWN"
    assert result.missing_columns == ("end_x",)


def test_status_policy_evaluator_maps_unknown():
    metric = {
        "id": "M_PROG_PASS_COUNT",
        "status_policy": {"OK": "ready", "DEGRADED": "limited", "UNKNOWN": "missing"},
    }
    result = evaluate_metric_status(metric, "UNKNOWN")
    assert result["status"] == "UNKNOWN"
    assert result["policy_reason"] == "missing"


def test_definition_confidence_audit_ok():
    metric = {"id": "M_PASS_COUNT", "definition_confidence": 0.95}
    result = audit_definition_confidence(metric)
    assert result["status"] == "OK"
