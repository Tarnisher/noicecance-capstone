"""Command-line demo for the deterministic multi-agent loop."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from noicecance_core.agent_loop import run_agent_loop
else:
    from .agent_loop import run_agent_loop


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the NoiceCance local agent loop.")
    parser.add_argument(
        "--scenario",
        default="intersection",
        help="Scenario id: intersection, airport, or high_frequency.",
    )
    parser.add_argument("--complaint", default=None, help="Optional user complaint.")
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=3,
        help="Maximum planner/safety iterations.",
    )
    parser.add_argument(
        "--force-unsafe-first-draft",
        action="store_true",
        help="Inject an unsafe first draft to demonstrate the revision loop.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional JSON output path. Prints to stdout when omitted.",
    )
    args = parser.parse_args(argv)

    result = run_agent_loop(
        scenario=args.scenario,
        complaint=args.complaint,
        max_iterations=args.max_iterations,
        force_unsafe_first_draft=args.force_unsafe_first_draft,
    )
    rendered = json.dumps(result, indent=2, ensure_ascii=True)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
