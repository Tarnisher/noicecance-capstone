"""Local command-line interface for NoiceCance."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from noicecance_core.agent_loop import run_agent_loop
    from noicecance_core.core import SCENARIOS
else:
    from .agent_loop import run_agent_loop
    from .core import SCENARIOS


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "assess":
        return _run_assess(args)

    parser.error(f"unknown command: {args.command}")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="noicecance",
        description="Run local NoiceCance assessment workflows.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    assess = subparsers.add_parser(
        "assess",
        help="Assess a noise complaint with the local agent loop.",
    )
    assess.add_argument(
        "--complaint",
        required=True,
        help="Noise problem text supplied by the user.",
    )
    assess.add_argument(
        "--out",
        default=None,
        help="Optional path for the full JSON agent-loop result.",
    )
    assess.add_argument(
        "--scenario",
        choices=sorted(SCENARIOS),
        default="custom",
        help="Scenario context. Defaults to custom for free-text local assessment.",
    )
    assess.add_argument(
        "--max-iterations",
        type=_positive_int,
        default=3,
        help="Maximum planner/safety revision iterations.",
    )
    return parser


def _run_assess(args: argparse.Namespace) -> int:
    result = run_agent_loop(
        scenario=args.scenario,
        complaint=args.complaint,
        max_iterations=args.max_iterations,
    )

    output_path = Path(args.out) if args.out else None
    if output_path is not None:
        rendered = json.dumps(result, indent=2, ensure_ascii=True)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered + "\n", encoding="utf-8")

    print(_render_summary(result, output_path))
    return 0


def _render_summary(result: dict[str, Any], output_path: Path | None) -> str:
    plan = _as_dict(result.get("plan"))
    report = _as_dict(result.get("report"))
    profile = _as_dict(plan.get("noise_profile"))
    measurement_plan = _as_dict(plan.get("measurement_plan"))
    analysis_conclusion = _as_dict(plan.get("analysis_conclusion"))

    iterations = int(result.get("iterations") or 0)
    iteration_label = "iteration" if iterations == 1 else "iterations"
    lines = [
        "NoiceCance local assessment",
        f"Status: {result.get('status', 'unknown')} ({iterations} {iteration_label})",
        f"Headline: {report.get('headline', 'n/a')}",
        f"Scenario: {report.get('scenario', 'n/a')}",
        f"Noise profile: {_join_values(profile.get('noise_classes'))}",
        (
            "Bands: "
            f"{_join_values(profile.get('dominant_bands'))}; "
            f"confidence: {profile.get('confidence', 'unknown')}"
        ),
    ]

    input_quality = _as_dict(profile.get("input_quality"))
    if input_quality:
        lines.append(
            "Input quality: "
            f"{input_quality.get('status', 'unknown')} - "
            f"{input_quality.get('reason', 'n/a')}"
        )

    lines.extend(
        [
            f"Measurement objective: {measurement_plan.get('objective', 'n/a')}",
            (
                "Recommended controls: "
                f"{_join_control_types(plan.get('recommended_controls'))}"
            ),
            f"Blocked controls: {_join_control_types(plan.get('blocked_controls'))}",
            f"Conclusion: {analysis_conclusion.get('summary', 'n/a')}",
        ]
    )

    if output_path is not None:
        lines.append(f"JSON written to: {output_path}")

    return "\n".join(lines)


def _positive_int(raw: str) -> int:
    value = int(raw)
    if value < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return value


def _join_values(value: Any) -> str:
    if not isinstance(value, list):
        return "n/a"
    items = [str(item) for item in value if item]
    return ", ".join(items) if items else "n/a"


def _join_control_types(value: Any) -> str:
    if not isinstance(value, list):
        return "n/a"
    controls = [
        str(control.get("type"))
        for control in value
        if isinstance(control, dict) and control.get("type")
    ]
    return ", ".join(controls) if controls else "none"


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


if __name__ == "__main__":
    raise SystemExit(main())
