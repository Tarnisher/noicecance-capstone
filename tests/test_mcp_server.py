import asyncio
import json
import sys
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from noicecance_core.mcp_server import mcp  # noqa: E402


def _tool_json(result: object) -> dict:
    if (
        isinstance(result, tuple)
        and len(result) >= 2
        and isinstance(result[1], dict)
    ):
        return result[1]

    if isinstance(result, tuple) and result:
        result = result[0]

    text = "".join(str(getattr(item, "text", "")) for item in result)
    return json.loads(text)


class NoiceCanceMcpServerTests(unittest.TestCase):
    def test_mcp_server_exposes_expected_tools(self) -> None:
        tools = asyncio.run(mcp.list_tools())
        names = {tool.name for tool in tools}

        self.assertIn("analyze_noise_profile", names)
        self.assertIn("generate_mitigation_plan", names)
        self.assertIn("run_agent_loop", names)
        self.assertIn("check_safety_limits", names)

    def test_mcp_tool_call_uses_input_quality_gate(self) -> None:
        result = asyncio.run(
            mcp.call_tool(
                "generate_mitigation_plan",
                {"scenario": "custom", "complaint": "hello"},
            )
        )
        plan = _tool_json(result)

        self.assertEqual(
            plan["noise_profile"]["input_quality"]["status"],
            "needs_noise_description",
        )
        self.assertFalse(plan["anc_policy"]["enabled"])
        self.assertIn(
            "clarify_noise_problem",
            {control["type"] for control in plan["recommended_controls"]},
        )


if __name__ == "__main__":
    unittest.main()
