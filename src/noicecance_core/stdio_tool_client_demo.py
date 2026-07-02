"""Small client demo for the dependency-free stdio tool bridge."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Demo the NoiceCance stdio bridge.")
    parser.add_argument(
        "--scenario",
        default="high_frequency",
        help="Scenario used for generate/check demo requests.",
    )
    args = parser.parse_args(argv)

    script = Path(__file__).with_name("stdio_tool_server.py")
    requests = [
        {"id": "tools", "method": "list_tools"},
        {
            "id": "generate",
            "method": "call_tool",
            "params": {
                "name": "generate_mitigation_plan",
                "payload": {"scenario": args.scenario},
            },
        },
        {
            "id": "check",
            "method": "call_tool",
            "params": {
                "name": "check_safety_limits",
                "payload": {"scenario": args.scenario},
            },
        },
    ]
    input_text = "".join(json.dumps(request) + "\n" for request in requests)

    completed = subprocess.run(
        [sys.executable, str(script)],
        input=input_text,
        capture_output=True,
        text=True,
        check=True,
    )

    responses: list[dict[str, Any]] = [
        json.loads(line) for line in completed.stdout.splitlines() if line.strip()
    ]
    print(json.dumps(responses, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
