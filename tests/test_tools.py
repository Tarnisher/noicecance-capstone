import sys
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from noicecance_core.tools import (  # noqa: E402
    analyze_noise_profile_tool,
    assess_control_suitability_tool,
    check_safety_limits_tool,
    generate_mitigation_plan_tool,
)


class NoiceCanceToolTests(unittest.TestCase):
    def test_high_frequency_noise_blocks_anc(self) -> None:
        response = generate_mitigation_plan_tool({"scenario": "high_frequency"})
        plan = response["result"]

        self.assertFalse(plan["anc_policy"]["enabled"])
        self.assertEqual(plan["safety"]["decision"], "blocked")
        self.assertIn(
            "near_field_anc",
            {control["type"] for control in plan["blocked_controls"]},
        )
        self.assertFalse(plan["privacy"]["raw_audio_retained"])

    def test_transportation_scenarios_only_allow_partial_anc(self) -> None:
        for scenario in ("intersection", "airport"):
            with self.subTest(scenario=scenario):
                response = generate_mitigation_plan_tool({"scenario": scenario})
                plan = response["result"]

                self.assertTrue(plan["anc_policy"]["enabled"])
                self.assertEqual(
                    plan["control_suitability"]["near_field_anc"]["status"],
                    "partial",
                )
                self.assertIn(
                    "whole_room_anc",
                    {control["type"] for control in plan["blocked_controls"]},
                )

    def test_plan_contains_required_top_level_fields(self) -> None:
        plan = generate_mitigation_plan_tool({"scenario": "intersection"})["result"]
        required = {
            "schema_version",
            "plan_id",
            "scenario",
            "input_summary",
            "noise_profile",
            "control_suitability",
            "recommended_controls",
            "blocked_controls",
            "anc_policy",
            "safety",
            "privacy",
            "caveats",
        }

        self.assertTrue(required.issubset(plan))
        self.assertEqual(plan["schema_version"], "2.0")

    def test_analyze_and_assess_tools_can_chain_payloads(self) -> None:
        analyzed = analyze_noise_profile_tool(
            {
                "scenario": "intersection",
                "complaint": "I hear low engine rumble and horns at night.",
            }
        )["result"]
        assessed = assess_control_suitability_tool({"noise_profile": analyzed})[
            "result"
        ]

        self.assertEqual(assessed["near_field_anc"]["status"], "partial")
        self.assertEqual(assessed["passive_insulation"]["status"], "recommended")

    def test_safety_tool_summarizes_generated_plan(self) -> None:
        safety = check_safety_limits_tool({"scenario": "high_frequency"})["result"]

        self.assertEqual(safety["decision"], "blocked")
        self.assertFalse(safety["anc_enabled"])
        self.assertIn("ultrasonic_cancellation", safety["blocked_controls"])
        self.assertFalse(safety["raw_audio_retained"])


if __name__ == "__main__":
    unittest.main()
