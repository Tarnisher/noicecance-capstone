import sys
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from noicecance_core.agent_loop import run_agent_loop  # noqa: E402


class NoiceCanceAgentLoopTests(unittest.TestCase):
    def test_intersection_loop_completes_with_limited_anc(self) -> None:
        result = run_agent_loop(
            scenario="intersection",
            complaint="I need sleep protection from low engine rumble and horns.",
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["iterations"], 1)
        self.assertTrue(result["plan"]["anc_policy"]["enabled"])
        self.assertEqual(
            result["plan"]["control_suitability"]["near_field_anc"]["status"],
            "partial",
        )
        self.assertEqual(result["safety_review"]["decision"], "pass_with_warnings")

    def test_high_frequency_loop_blocks_anc(self) -> None:
        result = run_agent_loop(
            scenario="high_frequency",
            complaint="Sharp high-pitched unpredictable workshop noise.",
        )

        self.assertEqual(result["status"], "completed")
        self.assertFalse(result["plan"]["anc_policy"]["enabled"])
        self.assertEqual(result["safety_review"]["decision"], "blocked")
        self.assertIn(
            "ultrasonic_cancellation",
            result["safety_review"]["blocked_controls"],
        )

    def test_safety_revision_loop_fixes_unsafe_first_draft(self) -> None:
        result = run_agent_loop(
            scenario="high_frequency",
            complaint="Sharp high-pitched unpredictable workshop noise.",
            force_unsafe_first_draft=True,
        )

        self.assertEqual(result["status"], "completed")
        self.assertGreaterEqual(result["iterations"], 2)
        self.assertFalse(result["plan"]["anc_policy"]["enabled"])
        self.assertTrue(
            any(event["action"] == "request_revision" for event in result["events"])
        )

    def test_loop_trace_includes_expected_agents(self) -> None:
        result = run_agent_loop(scenario="airport")
        agents = [event["agent"] for event in result["events"]]

        self.assertIn("User Intent Agent", agents)
        self.assertIn("Acoustic Scene Agent", agents)
        self.assertIn("Measurement Advisor Agent", agents)
        self.assertIn("Policy Planning Agent", agents)
        self.assertIn("Safety & Privacy Agent", agents)
        self.assertIn("Report Agent", agents)

    def test_report_includes_measurement_objective_and_conclusion(self) -> None:
        result = run_agent_loop(
            scenario="custom",
            complaint="A repeating low hum appears after midnight near the bedroom wall.",
        )

        self.assertEqual(result["status"], "completed")
        self.assertIn("measurement_objective", result["report"])
        self.assertIn("conclusion", result["report"])
        self.assertEqual(
            result["plan"]["measurement_plan"]["privacy_mode"],
            "local_features_only",
        )


if __name__ == "__main__":
    unittest.main()
