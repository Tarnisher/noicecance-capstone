"""JSON-like tool adapters for future MCP and ADK integration."""

from __future__ import annotations

from typing import Any

from .core import (
    analyze_noise_profile,
    assess_control_suitability,
    generate_mitigation_plan,
)


JsonDict = dict[str, Any]


def analyze_noise_profile_tool(payload: JsonDict) -> JsonDict:
    """Analyze a complaint and optional derived audio features.

    Expected payload keys:
    - `complaint`: user complaint text
    - `scenario`: optional scenario id, defaults to `intersection`
    - `audio_features`: optional privacy-preserving feature dictionary
    """

    data = _require_dict(payload)
    complaint = str(data.get("complaint") or "")
    scenario = str(data.get("scenario") or "intersection")
    audio_features = _optional_dict(data.get("audio_features"), "audio_features")

    return {
        "tool": "analyze_noise_profile",
        "result": analyze_noise_profile(
            complaint=complaint,
            scenario=scenario,
            audio_features=audio_features,
        ),
    }


def assess_control_suitability_tool(payload: JsonDict) -> JsonDict:
    """Assess which mitigation controls are suitable.

    The caller may provide a `noise_profile` directly. If omitted, this tool
    first analyzes `complaint`, `scenario`, and optional `audio_features`.
    """

    data = _require_dict(payload)
    noise_profile = data.get("noise_profile")
    if noise_profile is None:
        noise_profile = analyze_noise_profile_tool(data)["result"]
    else:
        noise_profile = _require_dict(noise_profile, "noise_profile")

    return {
        "tool": "assess_control_suitability",
        "result": assess_control_suitability(
            noise_profile=noise_profile,
            user_goal=str(data.get("user_goal") or "sleep_protection"),
            hardware_assumption=str(
                data.get("hardware_assumption")
                or "future calibrated quiet-zone hardware"
            ),
        ),
    }


def generate_mitigation_plan_tool(payload: JsonDict) -> JsonDict:
    """Generate a full mitigation plan with optional ANC policy."""

    data = _require_dict(payload)
    return {
        "tool": "generate_mitigation_plan",
        "result": generate_mitigation_plan(
            scenario=str(data.get("scenario") or "intersection"),
            complaint=_optional_str(data.get("complaint")),
            audio_features=_optional_dict(data.get("audio_features"), "audio_features"),
            hardware_assumption=str(
                data.get("hardware_assumption")
                or "future calibrated quiet-zone hardware"
            ),
        ),
    }


def check_safety_limits_tool(payload: JsonDict) -> JsonDict:
    """Check safety constraints on a mitigation plan or generated scenario.

    Expected payload keys:
    - `plan`: optional full mitigation plan. If omitted, a plan is generated
      from the same payload accepted by `generate_mitigation_plan_tool`.
    """

    data = _require_dict(payload)
    plan = data.get("plan")
    if plan is None:
        plan = generate_mitigation_plan_tool(data)["result"]
    else:
        plan = _require_dict(plan, "plan")

    blocked_types = [
        str(control.get("type"))
        for control in plan.get("blocked_controls", [])
        if isinstance(control, dict) and control.get("type")
    ]
    anc_policy = _require_dict(plan.get("anc_policy", {}), "anc_policy")
    safety = _require_dict(plan.get("safety", {}), "safety")

    return {
        "tool": "check_safety_limits",
        "result": {
            "decision": safety.get("decision", "blocked"),
            "anc_enabled": bool(anc_policy.get("enabled")),
            "blocked_controls": blocked_types,
            "raw_audio_retained": bool(
                _require_dict(plan.get("privacy", {}), "privacy").get(
                    "raw_audio_retained", True
                )
            ),
            "rules": list(safety.get("rules", [])),
            "warnings": list(plan.get("caveats", [])),
        },
    }


TOOLS = {
    "analyze_noise_profile": analyze_noise_profile_tool,
    "assess_control_suitability": assess_control_suitability_tool,
    "generate_mitigation_plan": generate_mitigation_plan_tool,
    "check_safety_limits": check_safety_limits_tool,
}


def _require_dict(value: Any, name: str = "payload") -> JsonDict:
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a JSON-like object")
    return value


def _optional_dict(value: Any, name: str) -> JsonDict | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a JSON-like object when provided")
    return value


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
