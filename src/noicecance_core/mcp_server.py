"""Official MCP server wrapper for the local NoiceCance tools."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover - exercised only without the extra dep
    raise RuntimeError(
        "The official MCP server requires mcp==1.28.1. "
        "Install project dependencies with: python -m pip install -r requirements.txt"
    ) from exc

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from noicecance_core.agent_loop import run_agent_loop as _run_agent_loop
    from noicecance_core.tools import (
        analyze_noise_profile_tool,
        check_safety_limits_tool,
        generate_mitigation_plan_tool,
    )
else:
    from .agent_loop import run_agent_loop as _run_agent_loop
    from .tools import (
        analyze_noise_profile_tool,
        check_safety_limits_tool,
        generate_mitigation_plan_tool,
    )


JsonDict = dict[str, Any]


def create_server() -> FastMCP:
    server = FastMCP(
        "NoiceCance",
        instructions=(
            "Local-first noise assessment tools. Do not request or retain raw audio. "
            "Use these tools to classify noise complaints, generate measurement plans, "
            "and block physically unsuitable or unsafe ANC recommendations."
        ),
        json_response=True,
    )

    @server.tool()
    def analyze_noise_profile(
        complaint: str,
        scenario: str = "custom",
        audio_features: JsonDict | None = None,
    ) -> JsonDict:
        """Classify a noise complaint and optional local derived features."""

        return analyze_noise_profile_tool(
            {
                "complaint": complaint,
                "scenario": scenario,
                "audio_features": audio_features,
            }
        )["result"]

    @server.tool()
    def generate_mitigation_plan(
        complaint: str | None = None,
        scenario: str = "custom",
        audio_features: JsonDict | None = None,
    ) -> JsonDict:
        """Generate an evidence-based mitigation plan as structured JSON."""

        return generate_mitigation_plan_tool(
            {
                "complaint": complaint,
                "scenario": scenario,
                "audio_features": audio_features,
            }
        )["result"]

    @server.tool()
    def run_agent_loop(
        complaint: str,
        scenario: str = "custom",
        max_iterations: int = 3,
    ) -> JsonDict:
        """Run the deterministic NoiceCance multi-agent assessment loop."""

        return _run_agent_loop(
            complaint=complaint,
            scenario=scenario,
            max_iterations=max_iterations,
        )

    @server.tool()
    def check_safety_limits(
        plan: JsonDict | None = None,
        complaint: str | None = None,
        scenario: str = "custom",
    ) -> JsonDict:
        """Audit a supplied or generated mitigation plan for safety limits."""

        payload: JsonDict = {"plan": plan} if plan is not None else {}
        if plan is None:
            payload.update({"complaint": complaint, "scenario": scenario})
        return check_safety_limits_tool(payload)["result"]

    return server


mcp = create_server()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the NoiceCance MCP server.")
    parser.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help="MCP transport to run. Stdio is best for local MCP clients.",
    )
    args = parser.parse_args(argv)

    mcp.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
