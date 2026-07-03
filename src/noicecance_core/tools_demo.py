"""Command-line wrapper around the local NoiceCance tool adapters."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from noicecance_core.tools import TOOLS
else:
    from .tools import TOOLS


COMMAND_TO_TOOL = {
    "analyze": "analyze_noise_profile",
    "assess": "assess_control_suitability",
    "generate": "generate_mitigation_plan",
    "check": "check_safety_limits",
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run NoiceCance local tools.")
    parser.add_argument(
        "command",
        choices=sorted(COMMAND_TO_TOOL),
        help="Tool command to run.",
    )
    parser.add_argument(
        "--scenario",
        default="intersection",
        help="Scenario id: intersection, airport, high_frequency, or custom.",
    )
    parser.add_argument(
        "--complaint",
        default=None,
        help="Optional user complaint text.",
    )
    parser.add_argument(
        "--payload",
        default=None,
        help="Optional JSON payload file. Use '-' to read JSON from stdin.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional JSON output path. Prints to stdout when omitted.",
    )
    args = parser.parse_args(argv)

    payload = _load_payload(args.payload)
    payload.setdefault("scenario", args.scenario)
    if args.complaint is not None:
        payload["complaint"] = args.complaint

    tool_name = COMMAND_TO_TOOL[args.command]
    result = TOOLS[tool_name](payload)
    rendered = json.dumps(result, indent=2, ensure_ascii=True)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)

    return 0


def _load_payload(path: str | None) -> dict[str, Any]:
    if path is None:
        return {}
    if path == "-":
        return _loads_json_object(sys.stdin.read(), "stdin")
    return _loads_json_object(Path(path).read_text(encoding="utf-8"), path)


def _loads_json_object(raw: str, source: str) -> dict[str, Any]:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise TypeError(f"{source} must contain a JSON object")
    return value


if __name__ == "__main__":
    raise SystemExit(main())
