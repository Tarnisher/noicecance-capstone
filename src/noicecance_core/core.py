"""Deterministic mitigation planning logic.

This module intentionally uses only the Python standard library. It is the
offline core that future MCP tools and ADK agents can call.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


ScenarioInput = dict[str, Any]
Plan = dict[str, Any]


SCENARIOS: dict[str, dict[str, str]] = {
    "intersection": {
        "id": "intersection_resident",
        "name": "Six-lane intersection resident",
        "primary_goal": "sleep_protection",
        "default_complaint": (
            "Second-floor bedroom facing a two-way six-lane intersection with "
            "braking, horns, motorcycles, and low engine rumble at night."
        ),
    },
    "airport": {
        "id": "airport_adjacent_home",
        "name": "Airport-adjacent home",
        "primary_goal": "nighttime_sleep_protection",
        "default_complaint": (
            "Several aircraft events per hour create low-frequency rumble and "
            "loud peaks that wake the family."
        ),
    },
    "high_frequency": {
        "id": "high_frequency_impulsive_noise",
        "name": "High-frequency impulsive noise",
        "primary_goal": "avoid_bad_anc_recommendation",
        "default_complaint": (
            "Sharp, high-pitched, unpredictable noise is the main problem."
        ),
    },
    "custom": {
        "id": "custom_local_assessment",
        "name": "Custom local noise assessment",
        "primary_goal": "evidence_based_mitigation",
        "default_complaint": (
            "Describe the noise source, room, time pattern, and what you need to protect."
        ),
    },
}

SAFETY_EVENTS = ["alarm", "siren", "smoke_detector", "urgent_speech"]


def analyze_noise_profile(
    complaint: str,
    scenario: str = "intersection",
    audio_features: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify a complaint and optional feature summary into a noise profile."""

    scenario_key = _normalize_scenario(scenario)
    text = complaint.lower()
    features = audio_features or {}

    noise_classes: list[str] = []
    bands: set[str] = set()
    flags = {
        "low": False,
        "high": False,
        "impulsive": False,
        "intermittent": False,
        "broadband": False,
    }

    if scenario_key == "intersection":
        noise_classes.extend(["road_traffic", "engine_rumble", "horns_or_braking"])
        bands.update(["low_frequency", "mid_frequency", "broadband"])
        flags.update({"low": True, "impulsive": True, "broadband": True})
    elif scenario_key == "airport":
        noise_classes.extend(
            ["aircraft_overflight", "low_frequency_rumble", "intermittent_peak_events"]
        )
        bands.update(["low_frequency", "broadband"])
        flags.update({"low": True, "intermittent": True, "broadband": True})
    elif scenario_key == "high_frequency":
        noise_classes.extend(["high_frequency_noise", "impulsive_events"])
        bands.update(["high_frequency", "broadband"])
        flags.update({"high": True, "impulsive": True, "broadband": True})

    low_words = [
        "rumble",
        "engine",
        "truck",
        "aircraft",
        "plane",
        "low frequency",
        "low-frequency",
        "low hum",
        "hum",
        "humming",
        "drone",
        "droning",
        "buzz",
        "buzzing",
        "vibration",
        "vibrating",
        "bass",
    ]
    high_words = ["high-pitched", "sharp", "squeal", "whine", "hiss", "ultrasonic"]
    impulsive_words = ["horn", "brake", "bang", "impact", "sudden", "impulsive"]
    intermittent_words = ["takeoff", "landing", "passes", "several times", "per hour"]
    context_words = [
        "noise",
        "sound",
        "loud",
        "quiet",
        "bedroom",
        "wall",
        "window",
        "door",
        "room",
        "sleep",
        "study",
        "work",
        "measure",
        "record",
        "dba",
        "decibel",
        "噪音",
        "噪声",
        "声音",
        "吵",
        "响",
        "嗡",
        "轰鸣",
        "低频",
        "高频",
        "振动",
        "震动",
        "刺耳",
        "机场",
        "飞机",
        "交通",
        "马路",
        "汽车",
        "卡车",
        "喇叭",
    ]
    has_feature_signal = any(
        features.get(key)
        for key in (
            "low_frequency_dominance",
            "high_frequency_dominance",
            "impulsive_events",
            "intermittent_events",
            "median_db_a",
            "peak_db_a",
            "dominant_frequency_hz",
            "event_count",
        )
    )
    has_text_signal = _contains_any(
        text,
        low_words + high_words + impulsive_words + intermittent_words + context_words,
    )

    if scenario_key == "custom" and not has_text_signal and not has_feature_signal:
        return {
            "noise_classes": ["insufficient_noise_description"],
            "dominant_bands": ["broadband"],
            "event_pattern": "continuous",
            "source_model": "insufficient information to classify a noise source",
            "confidence": "low",
            "input_quality": {
                "status": "needs_noise_description",
                "reason": "The custom input does not describe a noise source, timing, impact, or measurement.",
            },
            "flags": flags,
        }

    if _contains_any(text, low_words) or features.get("low_frequency_dominance"):
        flags["low"] = True
        bands.add("low_frequency")
        _append_unique(noise_classes, "low_frequency_rumble")
    if _contains_any(text, high_words) or features.get("high_frequency_dominance"):
        flags["high"] = True
        bands.add("high_frequency")
        _append_unique(noise_classes, "high_frequency_noise")
    if _contains_any(text, impulsive_words) or features.get("impulsive_events"):
        flags["impulsive"] = True
        _append_unique(noise_classes, "impulsive_events")
    if _contains_any(text, intermittent_words) or features.get("intermittent_events"):
        flags["intermittent"] = True
        _append_unique(noise_classes, "intermittent_peak_events")

    if not bands:
        bands.add("broadband")

    event_pattern = _event_pattern(flags)
    confidence = "medium" if complaint.strip() else "low"

    return {
        "noise_classes": noise_classes or ["unspecified_environmental_noise"],
        "dominant_bands": sorted(bands),
        "event_pattern": event_pattern,
        "source_model": _source_model(scenario_key, flags),
        "confidence": confidence,
        "flags": flags,
    }


def assess_control_suitability(
    noise_profile: dict[str, Any],
    user_goal: str = "sleep_protection",
    hardware_assumption: str = "future calibrated quiet-zone hardware",
) -> dict[str, Any]:
    """Score mitigation control families for the classified profile."""

    flags = noise_profile.get("flags", {})
    bands = set(noise_profile.get("dominant_bands", []))
    event_pattern = noise_profile.get("event_pattern", "mixed")
    input_quality = noise_profile.get("input_quality", {})

    if input_quality.get("status") == "needs_noise_description":
        reason = "No noise-specific evidence was provided, so controls should not be selected yet."
        return {
            "near_field_anc": {
                "status": "not_recommended",
                "score": 0.0,
                "reason": reason,
            },
            "passive_insulation": {
                "status": "not_recommended",
                "score": 0.0,
                "reason": "Physical controls need a described or measured noise source first.",
            },
            "masking_sound": {
                "status": "not_recommended",
                "score": 0.0,
                "reason": "Masking should not be recommended before the target noise is described.",
            },
            "hearing_protection": {
                "status": "not_recommended",
                "score": 0.0,
                "reason": "Hearing protection guidance requires exposure context or measured levels.",
            },
            "metadata": {
                "user_goal": user_goal,
                "hardware_assumption": hardware_assumption,
            },
        }

    has_low = flags.get("low") or "low_frequency" in bands
    has_high = flags.get("high") or "high_frequency" in bands
    is_impulsive = flags.get("impulsive") or event_pattern == "impulsive"
    is_intermit = flags.get("intermittent") or event_pattern == "intermittent"

    if has_high and (is_impulsive or not has_low):
        anc_status = "blocked"
        anc_score = 0.08
        anc_reason = (
            "High-frequency or impulsive noise is a poor open-air ANC target; "
            "phase cancellation can fail or create louder hot spots."
        )
    elif has_low and is_intermit:
        anc_status = "partial"
        anc_score = 0.52
        anc_reason = (
            "Low-frequency event tails may be reduced in a small quiet zone, "
            "but intermittent peaks require conservative handling."
        )
    elif has_low:
        anc_status = "partial"
        anc_score = 0.62
        anc_reason = (
            "Stable low-frequency components may be reduced near a pillow with "
            "calibrated microphones, speakers, and local DSP."
        )
    else:
        anc_status = "not_recommended"
        anc_score = 0.2
        anc_reason = "The profile does not show a strong low-frequency ANC target."

    return {
        "near_field_anc": {
            "status": anc_status,
            "score": anc_score,
            "reason": anc_reason,
        },
        "passive_insulation": {
            "status": "recommended",
            "score": 0.9 if has_high or is_impulsive else 0.82,
            "reason": (
                "Passive controls reduce airborne and reflected noise without "
                "depending on phase cancellation."
            ),
        },
        "masking_sound": {
            "status": "partial",
            "score": 0.48 if is_intermit or is_impulsive else 0.4,
            "reason": (
                "Masking can reduce perceived residual events, but it must not "
                "cover safety-critical sounds or replace hearing protection."
            ),
        },
        "hearing_protection": {
            "status": "recommended" if has_high else "partial",
            "score": 0.82 if has_high else 0.45,
            "reason": (
                "Certified protection may be needed for high-frequency or "
                "occupational exposure; for sleep it is optional only if safety "
                "alerts remain audible."
            ),
        },
        "metadata": {
            "user_goal": user_goal,
            "hardware_assumption": hardware_assumption,
        },
    }


def generate_mitigation_plan(
    scenario: str = "intersection",
    complaint: str | None = None,
    audio_features: dict[str, Any] | None = None,
    hardware_assumption: str = "future calibrated quiet-zone hardware",
) -> Plan:
    """Generate a mitigation-first plan with optional ANC policy."""

    scenario_key = _normalize_scenario(scenario)
    scenario_info = SCENARIOS[scenario_key]
    complaint_text = complaint or scenario_info["default_complaint"]
    profile = analyze_noise_profile(complaint_text, scenario_key, audio_features)
    suitability = assess_control_suitability(
        profile,
        user_goal=scenario_info["primary_goal"],
        hardware_assumption=hardware_assumption,
    )
    anc_status = suitability["near_field_anc"]["status"]

    recommended, blocked = _controls_for_profile(profile, suitability)
    anc_policy = _anc_policy_for(scenario_key, suitability, profile)
    safety = _safety_decision(anc_status, anc_policy)
    measurement_plan = _measurement_plan_for(scenario_key, profile, suitability)
    observed_features = _observed_features(audio_features)
    analysis_conclusion = _analysis_conclusion(profile, suitability, anc_policy)

    return {
        "schema_version": "2.0",
        "plan_id": _plan_id(scenario_key),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "scenario": {
            "id": scenario_info["id"],
            "name": scenario_info["name"],
            "primary_goal": scenario_info["primary_goal"],
        },
        "input_summary": {
            "complaint": complaint_text,
            "recording_used": bool(audio_features),
            "hardware_assumption": hardware_assumption,
        },
        "measurement_plan": measurement_plan,
        "observed_features": observed_features,
        "noise_profile": {k: v for k, v in profile.items() if k != "flags"},
        "control_suitability": {
            k: deepcopy(v)
            for k, v in suitability.items()
            if k != "metadata"
        },
        "recommended_controls": recommended,
        "blocked_controls": blocked,
        "anc_policy": anc_policy,
        "analysis_conclusion": analysis_conclusion,
        "safety": safety,
        "privacy": {
            "raw_audio_retained": False,
            "notes": [
                "Default mode keeps only derived acoustic features.",
                "Raw recordings should not be uploaded or stored unless the user explicitly opts in.",
            ],
        },
        "caveats": _caveats(anc_status, profile),
    }


def _controls_for_profile(
    profile: dict[str, Any],
    suitability: dict[str, Any],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    anc_status = suitability["near_field_anc"]["status"]
    event_pattern = profile.get("event_pattern", "mixed")
    bands = set(profile.get("dominant_bands", []))
    input_quality = profile.get("input_quality", {})

    if input_quality.get("status") == "needs_noise_description":
        return (
            [
                {
                    "type": "clarify_noise_problem",
                    "target": "noise source, timing, room, and user goal",
                    "reason": "The input does not yet describe a noise problem, so the next step is structured intake rather than mitigation.",
                    "priority": "high",
                },
                {
                    "type": "collect_basic_observations",
                    "target": "first local observation",
                    "reason": "Record when the noise occurs, where it is heard, what it sounds like, and what activity it affects.",
                    "priority": "high",
                },
            ],
            [
                {
                    "type": "near_field_anc",
                    "target": "unknown noise profile",
                    "reason": "Active control cannot be assessed without a described or measured noise target.",
                    "priority": "high",
                },
                {
                    "type": "whole_room_anc",
                    "target": "unknown room noise",
                    "reason": "Whole-room cancellation is not a valid default when the noise source is unknown.",
                    "priority": "high",
                },
            ],
        )

    recommended = [
        {
            "type": "passive_insulation",
            "target": "airborne and reflected noise paths",
            "reason": "Passive treatment works across frequency bands and does not depend on a clean phase model.",
            "priority": "high",
        },
        {
            "type": "safety_pass_through",
            "target": "alarms, sirens, smoke detectors, urgent speech",
            "reason": "Mitigation must preserve safety-critical sounds.",
            "priority": "high",
        },
    ]
    blocked = [
        {
            "type": "whole_room_anc",
            "target": "entire room",
            "reason": "Open-air whole-room cancellation is not realistic for reflected environmental noise.",
            "priority": "high",
        }
    ]

    if anc_status in {"partial", "recommended"}:
        recommended.append(
            {
                "type": "near_field_anc",
                "target": "low-frequency quiet zone near pillow",
                "reason": suitability["near_field_anc"]["reason"],
                "priority": "medium",
            }
        )
    else:
        blocked.append(
            {
                "type": "near_field_anc",
                "target": "dominant noise profile",
                "reason": suitability["near_field_anc"]["reason"],
                "priority": "high",
            }
        )

    if "high_frequency" in bands or event_pattern == "impulsive":
        recommended.append(
            {
                "type": "hearing_protection_or_source_control",
                "target": "high-frequency or impulsive events",
                "reason": "High-frequency impulsive noise should be handled with passive, engineering, or certified protective controls.",
                "priority": "high",
            }
        )
        blocked.append(
            {
                "type": "ultrasonic_cancellation",
                "target": "audible environmental noise",
                "reason": "Ultrasonic transducers do not directly cancel audible noise and can introduce distortion or safety concerns.",
                "priority": "high",
            }
        )

    if event_pattern in {"intermittent", "mixed"}:
        recommended.append(
            {
                "type": "controlled_masking_sound",
                "target": "perceived residual event contrast",
                "reason": "Low-level masking can reduce annoyance when it stays below safe levels and preserves alerts.",
                "priority": "low",
            }
        )

    return recommended, blocked


def _anc_policy_for(
    scenario_key: str,
    suitability: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    anc_status = suitability["near_field_anc"]["status"]
    if anc_status in {"blocked", "not_recommended"}:
        return {
            "enabled": False,
            "reason": suitability["near_field_anc"]["reason"],
        }

    target_band = {"min": 35, "max": 180} if scenario_key == "airport" else {"min": 45, "max": 250}
    return {
        "enabled": True,
        "reason": "Enable only as a limited low-frequency local quiet-zone strategy.",
        "target_bands_hz": [target_band],
        "quiet_zone": "bedside_pillow_area",
        "microphone_strategy": (
            "reference microphone near likely entry path and error microphone near sleep position"
        ),
        "speaker_strategy": "calibrated low-frequency-capable bedside speaker array",
        "preserve_events": SAFETY_EVENTS,
        "limits": {
            "max_output_mode": "conservative",
            "requires_calibration": True,
            "disable_for_impulsive_events": profile.get("event_pattern") in {"impulsive", "mixed"},
        },
    }


def _measurement_plan_for(
    scenario_key: str,
    profile: dict[str, Any],
    suitability: dict[str, Any],
) -> dict[str, Any]:
    bands = set(profile.get("dominant_bands", []))
    event_pattern = str(profile.get("event_pattern", "mixed"))
    anc_status = suitability["near_field_anc"]["status"]
    input_quality = profile.get("input_quality", {})

    if input_quality.get("status") == "needs_noise_description":
        return {
            "objective": "Describe the noise problem before choosing mitigation controls.",
            "privacy_mode": "local_features_only",
            "recommended_windows": [
                "Wait for an actual noise event before measuring.",
                "Write down when it happens, how long it lasts, and whether it repeats.",
            ],
            "microphone_positions": [
                "Main place where the noise bothers you, such as bed, desk, or sofa.",
                "Suspected entry point if known, such as window, wall, door gap, or vent.",
            ],
            "observations_to_log": [
                "what the noise sounds like",
                "time of day and duration",
                "room and likely source",
                "impact such as sleep, focus, stress, or safety concern",
            ],
            "derived_features_to_extract": [
                "median_dba",
                "peak_dba",
                "dominant_frequency_band",
                "event_pattern",
            ],
            "minimum_sample_count": 1,
            "safety_notes": [
                "Do not select ANC, masking, or insulation until a real noise target is described.",
                "Keep raw audio local by default; retain only derived acoustic features in the report.",
            ],
        }

    windows = [
        "Collect one quiet baseline when the target noise is absent.",
        "Collect one representative period when the target noise is present.",
    ]
    if scenario_key == "airport" or event_pattern in {"intermittent", "mixed"}:
        windows.append("Log at least three peak events with timestamps.")
    if scenario_key == "intersection" or event_pattern in {"continuous", "mixed"}:
        windows.append("Measure a 10 to 15 minute nighttime window near the sleep area.")

    positions = [
        "At the main listener position, such as pillow, desk, or chair.",
        "Near the likely entry path, such as window, wall vent, door gap, or facade.",
    ]
    if scenario_key == "custom":
        positions.append("At one comparison point farther from the suspected source.")

    derived_features = [
        "median_dba",
        "peak_dba",
        "dominant_frequency_band",
        "event_pattern",
        "low_frequency_dominance",
        "high_frequency_dominance",
    ]
    if "high_frequency" in bands:
        derived_features.append("impulsive_event_count")

    notes = [
        "Keep raw audio local by default; retain only derived acoustic features in the report.",
        "Record whether alarms, sirens, smoke detectors, or urgent speech must remain audible.",
    ]
    if anc_status in {"partial", "recommended"}:
        notes.append(
            "Before any active playback, repeat measurements with calibrated microphones and output limits."
        )

    return {
        "objective": _measurement_objective(scenario_key, anc_status),
        "privacy_mode": "local_features_only",
        "recommended_windows": windows,
        "microphone_positions": positions,
        "observations_to_log": [
            "time of day and duration",
            "room, window, and door state",
            "source notes such as traffic, aircraft, machinery, voices, or unknown",
            "user impact such as sleep, focus, stress, or safety concern",
        ],
        "derived_features_to_extract": derived_features,
        "minimum_sample_count": 2 if scenario_key != "airport" else 4,
        "safety_notes": notes,
    }


def _measurement_objective(scenario_key: str, anc_status: str) -> str:
    if anc_status in {"partial", "recommended"}:
        return "Confirm whether low-frequency content is stable enough for a limited quiet-zone policy."
    if scenario_key == "custom":
        return "Collect enough local evidence to classify the noise before choosing controls."
    return "Confirm the noise profile and collect evidence for non-ANC mitigation."


def _observed_features(audio_features: dict[str, Any] | None) -> dict[str, Any]:
    allowed = {
        "low_frequency_dominance",
        "high_frequency_dominance",
        "impulsive_events",
        "intermittent_events",
        "median_db_a",
        "peak_db_a",
        "dominant_frequency_hz",
        "event_count",
    }
    derived = {}
    for key, value in (audio_features or {}).items():
        if key in allowed and isinstance(value, (bool, int, float, str)):
            derived[key] = value

    return {
        "provided": bool(derived),
        "raw_audio_retained": False,
        "derived_features": derived,
        "notes": (
            ["No measured features were provided; conclusion is based on complaint and scenario templates."]
            if not derived
            else ["Only privacy-preserving derived features are included in this plan."]
        ),
    }


def _analysis_conclusion(
    profile: dict[str, Any],
    suitability: dict[str, Any],
    anc_policy: dict[str, Any],
) -> dict[str, Any]:
    anc_status = suitability["near_field_anc"]["status"]
    input_quality = profile.get("input_quality", {})
    if input_quality.get("status") == "needs_noise_description":
        return {
            "summary": "This input does not describe a noise problem yet, so NoiceCance is asking for measurement context instead of choosing controls.",
            "confidence": "low",
            "anc_decision": "not_recommended",
            "rationale": suitability["near_field_anc"]["reason"],
            "next_step": "Describe the noise source, timing, location, and impact, or provide local derived audio features.",
        }

    if anc_policy.get("enabled"):
        summary = "Limited local ANC may be considered only after measurement confirms the low-frequency target."
        next_step = "Run the measurement plan, then validate calibration before any active playback."
    elif anc_status == "blocked":
        summary = "ANC is not suitable for the current profile; prioritize passive or source controls."
        next_step = "Use the measurement plan to document peaks, entry paths, and non-ANC control priorities."
    else:
        summary = "More local evidence is needed before recommending active control."
        next_step = "Collect derived features and rerun the planner with measured observations."

    return {
        "summary": summary,
        "confidence": profile.get("confidence", "low"),
        "anc_decision": anc_status,
        "rationale": suitability["near_field_anc"]["reason"],
        "next_step": next_step,
    }


def _safety_decision(anc_status: str, anc_policy: dict[str, Any]) -> dict[str, Any]:
    if anc_status == "blocked":
        return {
            "decision": "blocked",
            "rules": [
                "Do not enable ANC for this profile.",
                "Recommend passive, engineering, or certified protective controls instead.",
                "Do not use ultrasonic cancellation claims for audible noise.",
            ],
        }

    rules = [
        "Do not claim medical diagnosis or guaranteed sleep improvement.",
        "Do not claim whole-room cancellation.",
        "Preserve alarms, sirens, smoke detectors, and urgent speech.",
        "Do not retain raw audio by default.",
    ]
    if anc_policy.get("enabled"):
        rules.append("Require calibrated hardware and conservative output limits before real playback.")
    return {
        "decision": "pass_with_warnings",
        "rules": rules,
    }


def _caveats(anc_status: str, profile: dict[str, Any]) -> list[str]:
    caveats = [
        "This plan is not a medical diagnosis.",
        "A laptop speaker is not a valid actuator for real traffic or aircraft ANC.",
        "Real deployment requires calibrated microphones, speakers, and local DSP.",
    ]
    if profile.get("input_quality", {}).get("status") == "needs_noise_description":
        caveats.append("No mitigation controls were selected because the input does not describe a noise problem.")
    if anc_status in {"blocked", "not_recommended"}:
        caveats.append("ANC is disabled because the profile is not a suitable active-control target.")
    if profile.get("event_pattern") in {"impulsive", "mixed"}:
        caveats.append("Impulsive events may be better handled by passive controls and alert-aware policies.")
    return caveats


def _normalize_scenario(scenario: str) -> str:
    normalized = scenario.strip().lower().replace("-", "_")
    aliases = {
        "intersection_resident": "intersection",
        "six_lane_intersection": "intersection",
        "traffic": "intersection",
        "airport_adjacent_home": "airport",
        "airport_home": "airport",
        "aircraft": "airport",
        "general": "custom",
        "local": "custom",
        "custom_assessment": "custom",
        "high": "high_frequency",
        "high_frequency_noise": "high_frequency",
        "rejected": "high_frequency",
        "workshop": "high_frequency",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in SCENARIOS:
        raise ValueError(
            f"Unknown scenario '{scenario}'. Choose one of: {', '.join(sorted(SCENARIOS))}."
        )
    return normalized


def _event_pattern(flags: dict[str, bool]) -> str:
    if flags["impulsive"] and flags["intermittent"]:
        return "mixed"
    if flags["impulsive"]:
        return "impulsive"
    if flags["intermittent"]:
        return "intermittent"
    return "continuous"


def _source_model(scenario_key: str, flags: dict[str, bool]) -> str:
    if scenario_key == "intersection":
        return "outdoor traffic transmitted through window and room reflections"
    if scenario_key == "airport":
        return "outdoor aircraft noise transmitted through building envelope with room reflections"
    if scenario_key == "custom" and flags["low"]:
        return "local low-frequency source hypothesis requires measurement"
    if flags["high"]:
        return "unpredictable high-frequency source with reflections"
    return "environmental noise with unknown source geometry"


def _contains_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def _append_unique(items: list[str], value: str) -> None:
    if value not in items:
        items.append(value)


def _plan_id(scenario_key: str) -> str:
    return f"plan-{scenario_key}"
