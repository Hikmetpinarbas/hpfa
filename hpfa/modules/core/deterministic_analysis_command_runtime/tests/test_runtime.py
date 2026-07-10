import importlib.util
import math
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "runtime.py"
SPEC = importlib.util.spec_from_file_location("deterministic_runtime", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def event(event_id, event_type, team, player, timestamp, x, y, **extra):
    row = {
        "event_id": event_id,
        "event_type": event_type,
        "team_id": team,
        "player_id": player,
        "timestamp_s": timestamp,
        "x": x,
        "y": y,
    }
    row.update(extra)
    return row


class DeterministicAnalysisRuntimeTests(unittest.TestCase):
    def test_parser_quarantines_invalid_and_calculates_pass_rate(self):
        rows = [
            event("1", "pass", "A", "p1", 10, 10, 20, end_x=20, end_y=20, outcome="success"),
            event("2", "pass", "A", "p1", 20, 20, 20, end_x=30, end_y=20, outcome="failure"),
            {"event_type": "shot", "team_id": "A", "timestamp_s": 30, "x": 90, "y": 34},
        ]
        report = MODULE.parse_events(rows)
        self.assertEqual(report["status"], "DEGRADED")
        self.assertEqual(report["valid_event_record_count"], 2)
        self.assertEqual(report["invalid_event_record_count"], 1)
        self.assertEqual(report["pass_summary"]["success_rate"], 0.5)
        self.assertEqual(report["canonical_event_count"], "UNKNOWN")

    def test_touch_timeline_is_time_sorted(self):
        rows = [
            event("2", "shot", "A", "p1", 20, 90, 34, outcome="failure"),
            event("1", "pass", "A", "p1", 10, 20, 20, end_x=30, end_y=20, outcome="success"),
        ]
        timeline = MODULE.parse_events(rows)["player_touch_timeline"]["p1"]
        self.assertEqual([item["event_id"] for item in timeline], ["1", "2"])

    def test_shot_geometry_returns_bounded_probability(self):
        result = MODULE.shot_geometry(94, 34)
        self.assertTrue(result["distance_to_goal_center_m"] > 0)
        self.assertTrue(0 < result["shot_angle_rad"] < math.pi)
        self.assertTrue(0 <= result["heuristic_xg_candidate"] <= 1)
        self.assertEqual(result["model_status"], "HEURISTIC_UNCALIBRATED")

    def test_nearer_central_shot_has_higher_heuristic_xg(self):
        near = MODULE.shot_geometry(94, 34)["heuristic_xg_candidate"]
        far = MODULE.shot_geometry(70, 10)["heuristic_xg_candidate"]
        self.assertGreater(near, far)

    def test_ppda_uses_equivalent_actor_frames(self):
        rows = [
            event("p1", "pass", "B", "b1", 1, 20, 20, end_x=30, end_y=20, outcome="success"),
            event("p2", "pass", "B", "b1", 2, 50, 20, end_x=55, end_y=20, outcome="success"),
            event("d1", "tackle", "A", "a1", 3, 80, 30, outcome="success"),
            event("d2", "interception", "A", "a2", 4, 70, 30, outcome="success"),
        ]
        parsed = MODULE.parse_events(rows)
        result = MODULE.calculate_ppda(parsed["valid_events"], "A", "attacking_normalized")
        self.assertEqual(result["opponent_passes_in_build_zone"], 2)
        self.assertEqual(result["defensive_actions_in_equivalent_zone"], 2)
        self.assertEqual(result["value"], 1.0)
        self.assertIn("proxy", result["claim_boundary"])

    def test_ppda_zero_denominator_is_null(self):
        rows = [event("p1", "pass", "B", "b1", 1, 20, 20, end_x=30, end_y=20, outcome="success")]
        result = MODULE.calculate_ppda(MODULE.parse_events(rows)["valid_events"], "A", "attacking_normalized")
        self.assertIsNone(result["value"])
        self.assertEqual(result["status"], "INSUFFICIENT_DENOMINATOR")

    def test_defensive_action_height_is_proxy(self):
        rows = [
            event("d1", "tackle", "A", "a1", 1, 60, 20, outcome="success"),
            event("d2", "foul", "A", "a2", 2, 80, 20, outcome="failure"),
        ]
        result = MODULE.defensive_action_height_proxy(
            MODULE.parse_events(rows)["valid_events"], "A", "attacking_normalized"
        )
        self.assertEqual(result["value_m"], 70)
        self.assertIn("not_defensive_line_height", result["claim_boundary"])

    def test_xt_ranks_positive_progressor(self):
        rows = [
            event("x1", "pass", "A", "creator", 1, 20, 34, end_x=90, end_y=34, outcome="success"),
            event("x2", "pass", "A", "safe", 2, 20, 34, end_x=25, end_y=34, outcome="success"),
        ]
        result = MODULE.calculate_xt(MODULE.parse_events(rows)["valid_events"], "attacking_normalized")
        self.assertEqual(result["player_ranking"][0]["player_id"], "creator")
        self.assertGreater(result["player_ranking"][0]["positive_xt"], 0)
        self.assertEqual(len(result["matrix"]), 8)
        self.assertEqual(len(result["matrix"][0]), 12)

    def test_router_dispatches_all_core_commands(self):
        parser_report = MODULE.execute_command({
            "command": "RAW-PARSER",
            "events": [event("1", "shot", "A", "p1", 1, 90, 34, outcome="failure")],
        })
        self.assertEqual(parser_report["command"], "RAW-PARSER")
        math_report = MODULE.execute_command({"command": "MATH-METRIC", "shot": {"x": 90, "y": 34}})
        self.assertEqual(math_report["status"], "SMOKE_PASS")
        debug_report = MODULE.execute_command({
            "command": "RAW-DEBUG",
            "raw_event": {"event_type": "pass"},
            "error": "TypeError NoneType",
        })
        self.assertIn("null_access_candidate", debug_report["diagnostic_categories"])

    def test_unknown_command_fails_closed(self):
        result = MODULE.execute_command({"command": "MAGIC"})
        self.assertEqual(result["status"], "FAIL_CLOSED")

    def test_no_sample_match_identity_leak(self):
        source = MODULE_PATH.read_text(encoding="utf-8").lower()
        for token in ("australia", "turkey", "united states", "world cup"):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()

