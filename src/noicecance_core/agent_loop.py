"""Deterministic multi-agent loop for the NoiceCance prototype.

The classes in this module are intentionally lightweight stand-ins for a
future ADK multi-agent implementation. They validate the state contract,
iteration flow, and safety gate before LLM-backed agents are introduced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .tools import (
    analyze_noise_profile_tool,
    assess_control_suitability_tool,
    check_safety_limits_tool,
    generate_mitigation_plan_tool,
)


JsonDict = dict[str, Any]


@dataclass
class AgentEvent:
    agent: str
    action: str
    summary: str
    tool: str | None = None
    data: JsonDict = field(default_factory=dict)

    def as_dict(self) -> JsonDict:
        return {
            "agent": self.agent,
            "action": self.action,
            "tool": self.tool,
            "summary": self.summary,
            "data": self.data,
        }


class UserIntentAgent:
    name = "User Intent Agent"

    def run(self, state: JsonDict) -> AgentEvent:
        complaint = str(state.get("complaint") or "")
        scenario = str(state.get("scenario") or "intersection")
        goal = _infer_goal(complaint, scenario)
        state["user_intent"] = {
            "goal": goal,
            "privacy_preference": "do_not_retain_raw_audio",
            "hardware_assumption": state.get(
                "hardware_assumption",
                "future calibrated quiet-zone hardware",
            ),
            "requires_safety_sounds": True,
        }
        return AgentEvent(
            agent=self.name,
            action="interpret_user_request",
            summary=f"Goal inferred as {goal}.",
            data={"goal": goal, "scenario": scenario},
        )


class AcousticSceneAgent:
    name = "Acoustic Scene Agent"

    def run(self, state: JsonDict) -> AgentEvent:
        payload = {
            "scenario": state.get("scenario", "intersection"),
            "complaint": state.get("complaint", ""),
            "audio_features": state.get("audio_features"),
        }
        result = analyze_noise_profile_tool(payload)["result"]
        state["noise_profile"] = result
        return AgentEvent(
            agent=self.name,
            action="classify_noise_scene",
            tool="analyze_noise_profile",
            summary=(
                "Classified noise as "
                f"{', '.join(result.get('noise_classes', []))}."
            ),
            data={
                "dominant_bands": result.get("dominant_bands", []),
                "event_pattern": result.get("event_pattern"),
            },
        )


class PolicyPlanningAgent:
    name = "Policy Planning Agent"

    def run(self, state: JsonDict) -> AgentEvent:
        user_intent = state.get("user_intent", {})
        payload = {
            "scenario": state.get("scenario", "intersection"),
            "complaint": state.get("complaint", ""),
            "audio_features": state.get("audio_features"),
            "hardware_assumption": user_intent.get(
                "hardware_assumption",
                "future calibrated quiet-zone hardware",
            ),
        }

        overrides = state.get("planner_overrides", {})
        if overrides:
            payload.update(overrides)

        plan = generate_mitigation_plan_tool(payload)["result"]
        if state.get("force_unsafe_first_draft") and not state.get(
            "unsafe_draft_created"
        ):
            plan = _inject_unsafe_anc_draft(plan)
            state["unsafe_draft_created"] = True

        state["plan"] = plan
        return AgentEvent(
            agent=self.name,
            action="generate_mitigation_plan",
            tool="generate_mitigation_plan",
            summary=(
                "Generated plan with ANC "
                f"{'enabled' if plan['anc_policy'].get('enabled') else 'disabled'}."
            ),
            data={
                "plan_id": plan.get("plan_id"),
                "anc_enabled": plan.get("anc_policy", {}).get("enabled"),
                "recommended_count": len(plan.get("recommended_controls", [])),
                "blocked_count": len(plan.get("blocked_controls", [])),
            },
        )


class SafetyPrivacyAgent:
    name = "Safety & Privacy Agent"

    def run(self, state: JsonDict) -> AgentEvent:
        plan = state.get("plan")
        result = check_safety_limits_tool({"plan": plan})["result"]
        revision = _revision_request(result, plan)
        state["safety_review"] = result
        state["revision_request"] = revision
        return AgentEvent(
            agent=self.name,
            action="audit_plan",
            tool="check_safety_limits",
            summary=(
                "Safety review "
                f"{result['decision']}; revision required: {revision['required']}."
            ),
            data={
                "decision": result["decision"],
                "anc_enabled": result["anc_enabled"],
                "revision_required": revision["required"],
                "blocked_controls": result["blocked_controls"],
            },
        )


class ReportAgent:
    name = "Report Agent"

    def run(self, state: JsonDict) -> AgentEvent:
        plan = state["plan"]
        safety = state["safety_review"]
        report = {
            "headline": _headline(plan, safety),
            "scenario": plan["scenario"]["name"],
            "anc_status": "enabled" if plan["anc_policy"].get("enabled") else "disabled",
            "top_recommendations": [
                control["type"] for control in plan.get("recommended_controls", [])[:3]
            ],
            "blocked_controls": safety.get("blocked_controls", []),
            "privacy": "raw audio not retained by default",
        }
        state["report"] = report
        return AgentEvent(
            agent=self.name,
            action="render_report",
            summary=report["headline"],
            data=report,
        )


def run_agent_loop(
    scenario: str = "intersection",
    complaint: str | None = None,
    audio_features: JsonDict | None = None,
    max_iterations: int = 3,
    force_unsafe_first_draft: bool = False,
) -> JsonDict:
    """Run the deterministic multi-agent planning loop."""

    if max_iterations < 1:
        raise ValueError("max_iterations must be at least 1")

    state: JsonDict = {
        "scenario": scenario,
        "complaint": complaint or "",
        "audio_features": audio_features,
        "force_unsafe_first_draft": force_unsafe_first_draft,
        "events": [],
        "iterations": 0,
        "status": "running",
        "started_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }

    agents = [
        UserIntentAgent(),
        AcousticSceneAgent(),
        PolicyPlanningAgent(),
        SafetyPrivacyAgent(),
    ]

    for agent in agents[:2]:
        _record(state, agent.run(state))

    for iteration in range(1, max_iterations + 1):
        state["iterations"] = iteration
        _record(state, agents[2].run(state))
        _record(state, agents[3].run(state))

        revision = state["revision_request"]
        if not revision["required"]:
            state["status"] = "completed"
            break

        _record(
            state,
            AgentEvent(
                agent="Loop Controller",
                action="request_revision",
                summary=revision["reason"],
                data=revision,
            ),
        )
        _apply_revision(state, revision)
    else:
        state["status"] = "max_iterations_reached"

    _record(state, ReportAgent().run(state))
    state["completed_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    return _public_result(state)


def _record(state: JsonDict, event: AgentEvent) -> None:
    state["events"].append(event.as_dict())


def _revision_request(safety: JsonDict, plan: JsonDict) -> JsonDict:
    blocked = set(safety.get("blocked_controls", []))
    anc_enabled = bool(safety.get("anc_enabled"))
    raw_audio_retained = bool(safety.get("raw_audio_retained"))

    if raw_audio_retained:
        return {
            "required": True,
            "reason": "Raw audio retention violates the privacy default.",
            "changes": {"raw_audio_retained": False},
        }

    if anc_enabled and "near_field_anc" in blocked:
        return {
            "required": True,
            "reason": "Unsafe active cancellation was proposed for a blocked profile.",
            "changes": {
                "disable_anc": True,
                "add_passive_controls": True,
            },
        }

    if anc_enabled and _policy_targets_unsupported_range(plan):
        return {
            "required": True,
            "reason": "ANC policy targets an unsupported frequency range.",
            "changes": {
                "disable_anc": True,
                "add_passive_controls": True,
            },
        }

    if plan.get("anc_policy", {}).get("enabled") and not _preserves_safety_events(plan):
        return {
            "required": True,
            "reason": "ANC policy must preserve safety-critical sounds.",
            "changes": {"restore_safety_events": True},
        }

    return {"required": False, "reason": "Plan passes deterministic safety gates.", "changes": {}}


def _apply_revision(state: JsonDict, revision: JsonDict) -> None:
    changes = revision.get("changes", {})
    overrides = state.setdefault("planner_overrides", {})

    if changes.get("disable_anc"):
        overrides["audio_features"] = {
            **(state.get("audio_features") or {}),
            "high_frequency_dominance": True,
            "impulsive_events": True,
        }
        if state.get("scenario") not in {"high_frequency", "high_frequency_noise"}:
            state["scenario"] = "high_frequency"

    if changes.get("restore_safety_events"):
        state["requires_safety_event_restore"] = True


def _inject_unsafe_anc_draft(plan: JsonDict) -> JsonDict:
    unsafe = {**plan}
    unsafe["anc_policy"] = {
        "enabled": True,
        "reason": "Unsafe draft: incorrectly attempts active cancellation.",
        "target_bands_hz": [{"min": 20, "max": 12000}],
        "quiet_zone": "entire_room",
        "preserve_events": [],
        "limits": {"max_output_mode": "unknown", "requires_calibration": False},
    }
    unsafe["blocked_controls"] = [
        *unsafe.get("blocked_controls", []),
        {
            "type": "near_field_anc",
            "target": "dominant unsafe profile",
            "reason": "Injected unsafe draft for loop testing.",
            "priority": "high",
        },
    ]
    unsafe["safety"] = {
        "decision": "blocked",
        "rules": [
            "Injected unsafe first draft must be revised by the safety agent.",
        ],
    }
    return unsafe


def _preserves_safety_events(plan: JsonDict) -> bool:
    events = set(plan.get("anc_policy", {}).get("preserve_events", []))
    required = {"alarm", "siren", "smoke_detector", "urgent_speech"}
    return required.issubset(events)


def _policy_targets_unsupported_range(plan: JsonDict) -> bool:
    for band in plan.get("anc_policy", {}).get("target_bands_hz", []):
        if not isinstance(band, dict):
            return True
        if float(band.get("max", 0)) > 500:
            return True
    return False


def _infer_goal(complaint: str, scenario: str) -> str:
    text = complaint.lower()
    if "sleep" in text or "night" in text or scenario == "airport":
        return "sleep_protection"
    if "work" in text or "study" in text:
        return "focus_protection"
    return "transportation_noise_mitigation"


def _headline(plan: JsonDict, safety: JsonDict) -> str:
    if safety["decision"] == "blocked":
        return "ANC is blocked for this profile; use non-ANC controls first."
    if plan["anc_policy"].get("enabled"):
        return "Use a mitigation-first plan with limited local low-frequency ANC."
    return "Use non-ANC mitigation controls for this noise profile."


def _public_result(state: JsonDict) -> JsonDict:
    return {
        "status": state["status"],
        "iterations": state["iterations"],
        "events": state["events"],
        "plan": state.get("plan"),
        "safety_review": state.get("safety_review"),
        "report": state.get("report"),
        "started_at": state["started_at"],
        "completed_at": state["completed_at"],
    }
