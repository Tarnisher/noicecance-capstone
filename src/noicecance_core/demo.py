"""Command-line demo for the deterministic NoiceCance core."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from noicecance_core.core import SCENARIOS, generate_mitigation_plan
else:
    from .core import SCENARIOS, generate_mitigation_plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a NoiceCance mitigation plan.")
    parser.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        default="intersection",
        help="Built-in scenario to plan for.",
    )
    parser.add_argument(
        "--complaint",
        default=None,
        help="Optional user complaint text. Defaults to the selected scenario.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional JSON output path. Prints to stdout when omitted.",
    )
    args = parser.parse_args(argv)

    plan = generate_mitigation_plan(
        scenario=args.scenario,
        complaint=args.complaint,
    )
    rendered = json.dumps(plan, indent=2, ensure_ascii=True)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
