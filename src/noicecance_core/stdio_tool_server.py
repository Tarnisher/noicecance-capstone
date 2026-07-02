"""Dependency-free stdio bridge for NoiceCance tools.

This is MCP-like, not an official MCP SDK implementation. It keeps the same
tool boundary while avoiding new dependencies during early prototyping.

Protocol: newline-delimited JSON. Each input line is one request and each
output line is one response.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from noicecance_core.tools import TOOLS
else:
    from .tools import TOOLS


JsonDict = dict[str, Any]

TOOL_DESCRIPTIONS: dict[str, str] = {
    "analyze_noise_profile": "Classify a complaint and optional derived audio features.",
    "assess_control_suitability": "Score mitigation control families for a noise profile.",
    "generate_mitigation_plan": "Generate mitigation_plan.json with optional anc_policy.",
    "check_safety_limits": "Summarize safety and privacy checks for a plan.",
}


def handle_request(request: JsonDict) -> JsonDict:
    """Handle one MCP-like request."""

    request_id = request.get("id")
    method = request.get("method")
    try:
        if method == "list_tools":
            return _ok(
                request_id,
                {
                    "tools": [
                        {
                            "name": name,
                            "description": TOOL_DESCRIPTIONS.get(name, ""),
                        }
                        for name in sorted(TOOLS)
                    ]
                },
            )

        if method == "call_tool":
            params = _require_dict(request.get("params", {}), "params")
            tool_name = str(params.get("name") or "")
            payload = _require_dict(params.get("payload", {}), "payload")
            if tool_name not in TOOLS:
                return _error(
                    request_id,
                    "unknown_tool",
                    f"Unknown tool '{tool_name}'.",
                    {"available_tools": sorted(TOOLS)},
                )
            return _ok(request_id, TOOLS[tool_name](payload))

        return _error(
            request_id,
            "unknown_method",
            f"Unknown method '{method}'.",
            {"available_methods": ["list_tools", "call_tool"]},
        )
    except Exception as exc:  # keep the bridge robust for agent callers
        return _error(
            request_id,
            "tool_error",
            str(exc),
            {"exception_type": type(exc).__name__},
        )


def serve(input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout) -> int:
    """Serve newline-delimited JSON requests until EOF."""

    for line in input_stream:
        raw = line.strip()
        if not raw:
            continue
        try:
            request = json.loads(raw)
            if not isinstance(request, dict):
                response = _error(None, "invalid_request", "Request must be a JSON object.")
            else:
                response = handle_request(request)
        except json.JSONDecodeError as exc:
            response = _error(None, "invalid_json", str(exc))

        output_stream.write(json.dumps(response, ensure_ascii=True) + "\n")
        output_stream.flush()
    return 0


def _ok(request_id: Any, result: JsonDict) -> JsonDict:
    return {
        "id": request_id,
        "ok": True,
        "result": result,
    }


def _error(
    request_id: Any,
    code: str,
    message: str,
    data: JsonDict | None = None,
) -> JsonDict:
    error: JsonDict = {
        "code": code,
        "message": message,
    }
    if data:
        error["data"] = data
    return {
        "id": request_id,
        "ok": False,
        "error": error,
    }


def _require_dict(value: Any, name: str) -> JsonDict:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a JSON-like object")
    return value


if __name__ == "__main__":
    raise SystemExit(serve())
