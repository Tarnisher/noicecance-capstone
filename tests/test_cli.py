import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path


SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

from noicecance_core.cli import main  # noqa: E402


class NoiceCanceCliTests(unittest.TestCase):
    def test_assess_writes_agent_loop_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "mitigation_plan.json"
            stdout = io.StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "assess",
                        "--complaint",
                        "A low hum appears after midnight near the bedroom wall.",
                        "--out",
                        str(output_path),
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertTrue(output_path.exists())
            result = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["plan"]["scenario"]["id"], "custom_local_assessment")
            self.assertEqual(
                result["plan"]["input_summary"]["complaint"],
                "A low hum appears after midnight near the bedroom wall.",
            )
            self.assertFalse(result["plan"]["privacy"]["raw_audio_retained"])
            self.assertIn("Noise profile:", stdout.getvalue())
            self.assertIn("JSON written to:", stdout.getvalue())

    def test_assess_defaults_to_custom_input_quality_gate(self) -> None:
        stdout = io.StringIO()

        with redirect_stdout(stdout):
            exit_code = main(["assess", "--complaint", "hello"])

        output = stdout.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("needs_noise_description", output)
        self.assertIn("clarify_noise_problem", output)
        self.assertIn("near_field_anc", output)

    def test_assess_requires_complaint(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            main(["assess"])

        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
