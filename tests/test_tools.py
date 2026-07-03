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
            "measurement_plan",
            "observed_features",
            "noise_profile",
            "control_suitability",
            "recommended_controls",
            "blocked_controls",
            "anc_policy",
            "analysis_conclusion",
            "safety",
            "privacy",
            "caveats",
        }

        self.assertTrue(required.issubset(plan))
        self.assertEqual(plan["schema_version"], "2.0")

    def test_plan_includes_local_measurement_workflow(self) -> None:
        plan = generate_mitigation_plan_tool(
            {
                "scenario": "custom",
                "complaint": "A low hum appears after midnight near the bedroom wall.",
            }
        )["result"]

        self.assertEqual(plan["scenario"]["id"], "custom_local_assessment")
        self.assertEqual(plan["measurement_plan"]["privacy_mode"], "local_features_only")
        self.assertIn("low_frequency", plan["noise_profile"]["dominant_bands"])
        self.assertEqual(
            plan["control_suitability"]["near_field_anc"]["status"],
            "partial",
        )
        self.assertIn(
            "median_dba",
            plan["measurement_plan"]["derived_features_to_extract"],
        )
        self.assertFalse(plan["observed_features"]["raw_audio_retained"])
        self.assertIn("summary", plan["analysis_conclusion"])

    def test_derived_audio_features_are_whitelisted(self) -> None:
        plan = generate_mitigation_plan_tool(
            {
                "scenario": "custom",
                "audio_features": {
                    "low_frequency_dominance": True,
                    "peak_db_a": 71.5,
                    "raw_audio_path": "private-bedroom.wav",
                },
            }
        )["result"]

        derived = plan["observed_features"]["derived_features"]
        self.assertTrue(plan["observed_features"]["provided"])
        self.assertEqual(derived["peak_db_a"], 71.5)
        self.assertNotIn("raw_audio_path", derived)

    def test_custom_irrelevant_input_requests_noise_details(self) -> None:
        plan = generate_mitigation_plan_tool(
            {
                "scenario": "custom",
                "complaint": "你好",
            }
        )["result"]

        self.assertEqual(plan["noise_profile"]["confidence"], "low")
        self.assertEqual(
            plan["noise_profile"]["input_quality"]["status"],
            "needs_noise_description",
        )
        self.assertFalse(plan["anc_policy"]["enabled"])
        self.assertEqual(
            plan["analysis_conclusion"]["summary"],
            "This input does not describe a noise problem yet, so NoiceCance is asking for measurement context instead of choosing controls.",
        )
        self.assertIn(
            "clarify_noise_problem",
            {control["type"] for control in plan["recommended_controls"]},
        )
        self.assertNotIn(
            "passive_insulation",
            {control["type"] for control in plan["recommended_controls"]},
        )

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
