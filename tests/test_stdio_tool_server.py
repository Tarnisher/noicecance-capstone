import io
import json
import sys
import unittest
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from noicecance_core.stdio_tool_server import handle_request, serve  # noqa: E402


class StdioToolServerTests(unittest.TestCase):
    def test_list_tools_returns_expected_tool_names(self) -> None:
        response = handle_request({"id": "1", "method": "list_tools"})

        self.assertTrue(response["ok"])
        tool_names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            tool_names,
            {
                "analyze_noise_profile",
                "assess_control_suitability",
                "generate_mitigation_plan",
                "check_safety_limits",
            },
        )

    def test_call_tool_high_frequency_check_blocks_anc(self) -> None:
        response = handle_request(
            {
                "id": "2",
                "method": "call_tool",
                "params": {
                    "name": "check_safety_limits",
                    "payload": {"scenario": "high_frequency"},
                },
            }
        )

        self.assertTrue(response["ok"])
        result = response["result"]["result"]
        self.assertFalse(result["anc_enabled"])
        self.assertIn("ultrasonic_cancellation", result["blocked_controls"])

    def test_unknown_tool_returns_structured_error(self) -> None:
        response = handle_request(
            {
                "id": "3",
                "method": "call_tool",
                "params": {"name": "does_not_exist", "payload": {}},
            }
        )

        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "unknown_tool")
        self.assertIn("available_tools", response["error"]["data"])

    def test_serve_processes_newline_delimited_json(self) -> None:
        input_stream = io.StringIO(
            json.dumps({"id": "a", "method": "list_tools"})
            + "\n"
            + json.dumps(
                {
                    "id": "b",
                    "method": "call_tool",
                    "params": {
                        "name": "generate_mitigation_plan",
                        "payload": {"scenario": "airport"},
                    },
                }
            )
            + "\n"
        )
        output_stream = io.StringIO()

        exit_code = serve(input_stream, output_stream)
        responses = [
            json.loads(line)
            for line in output_stream.getvalue().splitlines()
            if line.strip()
        ]

        self.assertEqual(exit_code, 0)
        self.assertEqual(len(responses), 2)
        self.assertTrue(all(response["ok"] for response in responses))
        self.assertEqual(
            responses[1]["result"]["result"]["scenario"]["id"],
            "airport_adjacent_home",
        )


if __name__ == "__main__":
    unittest.main()
