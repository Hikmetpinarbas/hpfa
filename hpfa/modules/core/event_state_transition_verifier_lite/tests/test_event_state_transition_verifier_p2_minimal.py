import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
SRC = ROOT / "hpfa" / "modules" / "core" / "event_state_transition_verifier_lite" / "src"
sys.path.insert(0, str(SRC))

from event_state_transition_verifier import gate_blocks, normalize_state


def test_wait_status_blocks_upstream_gate():
    assert gate_blocks({"status": "WAIT", "decision": "PENDING"}) is True


def test_goal_kick_is_restart_before_goal_terminal():
    assert normalize_state("Goal Kick") == "restart"
