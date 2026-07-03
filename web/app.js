const scenarioDefaults = {
  intersection: {
    complaint:
      "I live on the second floor facing a two-way six-lane intersection. At night I hear braking, horns, motorcycles, and a low engine rumble. I want to sleep but still hear alarms.",
    id: "intersection_resident",
    name: "Six-lane intersection resident",
    primaryGoal: "sleep_protection",
    sourceLabel: "Traffic source",
    waves: "traffic",
  },
  airport: {
    complaint:
      "I live near an airport. Several times per hour, aircraft create loud low-frequency waves that wake my family. We need a plan for nighttime sleep.",
    id: "airport_adjacent_home",
    name: "Airport-adjacent home",
    primaryGoal: "nighttime_sleep_protection",
    sourceLabel: "Aircraft path",
    waves: "airport",
  },
  high_frequency: {
    complaint:
      "The main noise is sharp, high-pitched, and unpredictable. I want to know whether a speaker or ultrasonic array can cancel it.",
    id: "high_frequency_impulsive_noise",
    name: "High-frequency impulsive noise",
    primaryGoal: "avoid_bad_anc_recommendation",
    sourceLabel: "Sharp source",
    waves: "blocked",
  },
  custom: {
    complaint:
      "My apartment has a repeating low hum after midnight near the bedroom wall. I need to know what to measure before choosing insulation, masking, or any active control.",
    id: "custom_local_assessment",
    name: "Custom local noise assessment",
    primaryGoal: "evidence_based_mitigation",
    sourceLabel: "Suspected source",
    waves: "traffic",
  },
};

const safetyEvents = ["alarm", "siren", "smoke_detector", "urgent_speech"];
let activeScenario = "intersection";
let currentResult = null;

const elements = {
  tabs: Array.from(document.querySelectorAll(".scenario-tab")),
  complaint: document.getElementById("complaintInput"),
  run: document.getElementById("runButton"),
  export: document.getElementById("exportButton"),
  statusDecision: document.getElementById("statusDecision"),
  trace: document.getElementById("agentTrace"),
  noiseProfile: document.getElementById("noiseProfile"),
  suitability: document.getElementById("suitabilityList"),
  recommended: document.getElementById("recommendedControls"),
  blocked: document.getElementById("blockedControls"),
  measurement: document.getElementById("measurementPlan"),
  conclusion: document.getElementById("conclusionPanel"),
  json: document.getElementById("jsonOutput"),
  iterationBadge: document.getElementById("iterationBadge"),
  confidenceBadge: document.getElementById("confidenceBadge"),
  ancBadge: document.getElementById("ancBadge"),
  measurementBadge: document.getElementById("measurementBadge"),
  conclusionBadge: document.getElementById("conclusionBadge"),
  privacyBadge: document.getElementById("privacyBadge"),
  mapBadge: document.getElementById("mapBadge"),
  sourceLabel: document.getElementById("sourceLabel"),
  noiseWaves: document.getElementById("noiseWaves"),
};

function analyzeNoiseProfile(scenario, complaint) {
  const text = complaint.toLowerCase();
  const flags = {
    low: false,
    high: false,
    impulsive: false,
    intermittent: false,
    broadband: false,
  };
  const classes = [];
  const bands = new Set();

  if (scenario === "intersection") {
    classes.push("road_traffic", "engine_rumble", "horns_or_braking");
    ["low_frequency", "mid_frequency", "broadband"].forEach((band) => bands.add(band));
    Object.assign(flags, { low: true, impulsive: true, broadband: true });
  }
  if (scenario === "airport") {
    classes.push("aircraft_overflight", "low_frequency_rumble", "intermittent_peak_events");
    ["low_frequency", "broadband"].forEach((band) => bands.add(band));
    Object.assign(flags, { low: true, intermittent: true, broadband: true });
  }
  if (scenario === "high_frequency") {
    classes.push("high_frequency_noise", "impulsive_events");
    ["high_frequency", "broadband"].forEach((band) => bands.add(band));
    Object.assign(flags, { high: true, impulsive: true, broadband: true });
  }

  const lowWords = [
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
  ];
  const highWords = ["high-pitched", "sharp", "squeal", "whine", "hiss", "ultrasonic"];
  const impulsiveWords = ["horn", "brake", "bang", "impact", "sudden", "impulsive"];
  const intermittentWords = ["takeoff", "landing", "passes", "several times", "per hour"];
  const contextWords = [
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
  ];
  const hasTextSignal = containsAny(text, [
    ...lowWords,
    ...highWords,
    ...impulsiveWords,
    ...intermittentWords,
    ...contextWords,
  ]);

  if (scenario === "custom" && !hasTextSignal) {
    return {
      noise_classes: ["insufficient_noise_description"],
      dominant_bands: ["broadband"],
      event_pattern: "continuous",
      source_model: "insufficient information to classify a noise source",
      confidence: "low",
      input_quality: {
        status: "needs_noise_description",
        reason: "The custom input does not describe a noise source, timing, impact, or measurement.",
      },
      flags,
    };
  }

  if (
    containsAny(text, lowWords)
  ) {
    flags.low = true;
    bands.add("low_frequency");
    appendUnique(classes, "low_frequency_rumble");
  }
  if (containsAny(text, highWords)) {
    flags.high = true;
    bands.add("high_frequency");
    appendUnique(classes, "high_frequency_noise");
  }
  if (containsAny(text, impulsiveWords)) {
    flags.impulsive = true;
    appendUnique(classes, "impulsive_events");
  }
  if (containsAny(text, intermittentWords)) {
    flags.intermittent = true;
    appendUnique(classes, "intermittent_peak_events");
  }

  if (!bands.size) bands.add("broadband");

  return {
    noise_classes: classes.length ? classes : ["unspecified_environmental_noise"],
    dominant_bands: Array.from(bands).sort(),
    event_pattern: eventPattern(flags),
    source_model: sourceModel(scenario, flags),
    confidence: complaint.trim() ? "medium" : "low",
    flags,
  };
}

function assessControlSuitability(profile) {
  if (profile.input_quality?.status === "needs_noise_description") {
    const reason = "No noise-specific evidence was provided, so controls should not be selected yet.";
    return {
      near_field_anc: {
        status: "not_recommended",
        score: 0,
        reason,
      },
      passive_insulation: {
        status: "not_recommended",
        score: 0,
        reason: "Physical controls need a described or measured noise source first.",
      },
      masking_sound: {
        status: "not_recommended",
        score: 0,
        reason: "Masking should not be recommended before the target noise is described.",
      },
      hearing_protection: {
        status: "not_recommended",
        score: 0,
        reason: "Hearing protection guidance requires exposure context or measured levels.",
      },
    };
  }

  const bands = new Set(profile.dominant_bands);
  const hasLow = profile.flags.low || bands.has("low_frequency");
  const hasHigh = profile.flags.high || bands.has("high_frequency");
  const isImpulsive = profile.flags.impulsive || profile.event_pattern === "impulsive";
  const isIntermittent = profile.flags.intermittent || profile.event_pattern === "intermittent";

  let anc;
  if (hasHigh && (isImpulsive || !hasLow)) {
    anc = {
      status: "blocked",
      score: 0.08,
      reason:
        "High-frequency or impulsive noise is a poor open-air ANC target; phase cancellation can fail or create louder hot spots.",
    };
  } else if (hasLow && isIntermittent) {
    anc = {
      status: "partial",
      score: 0.52,
      reason:
        "Low-frequency event tails may be reduced in a small quiet zone, but intermittent peaks require conservative handling.",
    };
  } else if (hasLow) {
    anc = {
      status: "partial",
      score: 0.62,
      reason:
        "Stable low-frequency components may be reduced near a pillow with calibrated microphones, speakers, and local DSP.",
    };
  } else {
    anc = {
      status: "not_recommended",
      score: 0.2,
      reason: "The profile does not show a strong low-frequency ANC target.",
    };
  }

  return {
    near_field_anc: anc,
    passive_insulation: {
      status: "recommended",
      score: hasHigh || isImpulsive ? 0.9 : 0.82,
      reason:
        "Passive controls reduce airborne and reflected noise without depending on phase cancellation.",
    },
    masking_sound: {
      status: "partial",
      score: isIntermittent || isImpulsive ? 0.48 : 0.4,
      reason:
        "Masking can reduce perceived residual events, but it must not cover safety-critical sounds or replace hearing protection.",
    },
    hearing_protection: {
      status: hasHigh ? "recommended" : "partial",
      score: hasHigh ? 0.82 : 0.45,
      reason:
        "Certified protection may be needed for high-frequency or occupational exposure; for sleep it is optional only if safety alerts remain audible.",
    },
  };
}

function generatePlan(scenario, complaint) {
  const profile = analyzeNoiseProfile(scenario, complaint);
  const suitability = assessControlSuitability(profile);
  const ancStatus = suitability.near_field_anc.status;
  const { recommended, blocked } = controlsForProfile(profile, suitability);
  const ancPolicy = ancPolicyFor(scenario, suitability, profile);
  const safety = safetyDecision(ancStatus, ancPolicy);
  const scenarioInfo = scenarioDefaults[scenario];
  const measurementPlan = measurementPlanFor(scenario, profile, suitability);

  return {
    schema_version: "2.0",
    plan_id: `web-plan-${scenario}`,
    scenario: {
      id: scenarioInfo.id,
      name: scenarioInfo.name,
      primary_goal: scenarioInfo.primaryGoal,
    },
    input_summary: {
      complaint,
      recording_used: false,
      hardware_assumption: "future calibrated quiet-zone hardware",
    },
    measurement_plan: measurementPlan,
    observed_features: observedFeatures(),
    noise_profile: stripFlags(profile),
    control_suitability: suitability,
    recommended_controls: recommended,
    blocked_controls: blocked,
    anc_policy: ancPolicy,
    analysis_conclusion: analysisConclusion(profile, suitability, ancPolicy),
    safety,
    privacy: {
      raw_audio_retained: false,
      notes: ["Default mode keeps only derived acoustic features."],
    },
    caveats: caveatsFor(ancStatus, profile),
  };
}

function runAgentLoop() {
  const complaint = elements.complaint.value.trim() || scenarioDefaults[activeScenario].complaint;
  const plan = generatePlan(activeScenario, complaint);
  const safetyReview = checkSafety(plan);
  const events = [
    {
      agent: "User Intent Agent",
      action: "interpret_user_request",
      summary: `Goal inferred as ${plan.scenario.primary_goal}.`,
    },
    {
      agent: "Acoustic Scene Agent",
      action: "classify_noise_scene",
      summary: `Classified ${plan.noise_profile.noise_classes.join(", ")}.`,
    },
    {
      agent: "Measurement Advisor Agent",
      action: "draft_measurement_targets",
      summary: plan.measurement_plan.objective,
    },
    {
      agent: "Policy Planning Agent",
      action: "generate_mitigation_plan",
      summary: `Generated plan with ANC ${plan.anc_policy.enabled ? "enabled" : "disabled"}.`,
    },
    {
      agent: "Safety & Privacy Agent",
      action: "audit_plan",
      summary: `Safety review ${safetyReview.decision}; revision required: false.`,
    },
    {
      agent: "Report Agent",
      action: "render_report",
      summary: headlineFor(plan, safetyReview),
    },
  ];

  currentResult = {
    status: "completed",
    iterations: 1,
    events,
    plan,
    safety_review: safetyReview,
    report: {
      headline: headlineFor(plan, safetyReview),
      scenario: plan.scenario.name,
      anc_status: plan.anc_policy.enabled ? "enabled" : "disabled",
      measurement_objective: plan.measurement_plan.objective,
      conclusion: plan.analysis_conclusion.summary,
      top_recommendations: plan.recommended_controls.slice(0, 3).map((item) => item.type),
      blocked_controls: safetyReview.blocked_controls,
      privacy: "raw audio not retained by default",
    },
  };

  render(currentResult);
}

function controlsForProfile(profile, suitability) {
  if (profile.input_quality?.status === "needs_noise_description") {
    return {
      recommended: [
        {
          type: "clarify_noise_problem",
          target: "noise source, timing, room, and user goal",
          reason: "The input does not yet describe a noise problem, so the next step is structured intake rather than mitigation.",
          priority: "high",
        },
        {
          type: "collect_basic_observations",
          target: "first local observation",
          reason: "Record when the noise occurs, where it is heard, what it sounds like, and what activity it affects.",
          priority: "high",
        },
      ],
      blocked: [
        {
          type: "near_field_anc",
          target: "unknown noise profile",
          reason: "Active control cannot be assessed without a described or measured noise target.",
          priority: "high",
        },
        {
          type: "whole_room_anc",
          target: "unknown room noise",
          reason: "Whole-room cancellation is not a valid default when the noise source is unknown.",
          priority: "high",
        },
      ],
    };
  }

  const recommended = [
    {
      type: "passive_insulation",
      target: "airborne and reflected noise paths",
      reason: "Passive treatment works across frequency bands and does not depend on a clean phase model.",
      priority: "high",
    },
    {
      type: "safety_pass_through",
      target: "alarms, sirens, smoke detectors, urgent speech",
      reason: "Mitigation must preserve safety-critical sounds.",
      priority: "high",
    },
  ];
  const blocked = [
    {
      type: "whole_room_anc",
      target: "entire room",
      reason: "Open-air whole-room cancellation is not realistic for reflected environmental noise.",
      priority: "high",
    },
  ];

  if (["partial", "recommended"].includes(suitability.near_field_anc.status)) {
    recommended.push({
      type: "near_field_anc",
      target: "low-frequency quiet zone near pillow",
      reason: suitability.near_field_anc.reason,
      priority: "medium",
    });
  } else {
    blocked.push({
      type: "near_field_anc",
      target: "dominant noise profile",
      reason: suitability.near_field_anc.reason,
      priority: "high",
    });
  }

  if (profile.dominant_bands.includes("high_frequency") || profile.event_pattern === "impulsive") {
    recommended.push({
      type: "hearing_protection_or_source_control",
      target: "high-frequency or impulsive events",
      reason: "High-frequency impulsive noise should be handled with passive, engineering, or certified protective controls.",
      priority: "high",
    });
    blocked.push({
      type: "ultrasonic_cancellation",
      target: "audible environmental noise",
      reason: "Ultrasonic transducers do not directly cancel audible noise and can introduce distortion or safety concerns.",
      priority: "high",
    });
  }

  if (["intermittent", "mixed"].includes(profile.event_pattern)) {
    recommended.push({
      type: "controlled_masking_sound",
      target: "perceived residual event contrast",
      reason: "Low-level masking can reduce annoyance when it stays below safe levels and preserves alerts.",
      priority: "low",
    });
  }

  return { recommended, blocked };
}

function ancPolicyFor(scenario, suitability, profile) {
  if (["blocked", "not_recommended"].includes(suitability.near_field_anc.status)) {
    return { enabled: false, reason: suitability.near_field_anc.reason };
  }

  return {
    enabled: true,
    reason: "Enable only as a limited low-frequency local quiet-zone strategy.",
    target_bands_hz: [scenario === "airport" ? { min: 35, max: 180 } : { min: 45, max: 250 }],
    quiet_zone: "bedside_pillow_area",
    microphone_strategy: "reference microphone near likely entry path and error microphone near sleep position",
    speaker_strategy: "calibrated low-frequency-capable bedside speaker array",
    preserve_events: safetyEvents,
    limits: {
      max_output_mode: "conservative",
      requires_calibration: true,
      disable_for_impulsive_events: ["impulsive", "mixed"].includes(profile.event_pattern),
    },
  };
}

function safetyDecision(ancStatus, ancPolicy) {
  if (ancStatus === "blocked") {
    return {
      decision: "blocked",
      rules: [
        "Do not enable ANC for this profile.",
        "Recommend passive, engineering, or certified protective controls instead.",
        "Do not use ultrasonic cancellation claims for audible noise.",
      ],
    };
  }

  const rules = [
    "Do not claim medical diagnosis or guaranteed sleep improvement.",
    "Do not claim whole-room cancellation.",
    "Preserve alarms, sirens, smoke detectors, and urgent speech.",
    "Do not retain raw audio by default.",
  ];
  if (ancPolicy.enabled) rules.push("Require calibrated hardware and conservative output limits before real playback.");
  return { decision: "pass_with_warnings", rules };
}

function checkSafety(plan) {
  return {
    decision: plan.safety.decision,
    anc_enabled: Boolean(plan.anc_policy.enabled),
    blocked_controls: plan.blocked_controls.map((item) => item.type),
    raw_audio_retained: Boolean(plan.privacy.raw_audio_retained),
    rules: plan.safety.rules,
    warnings: plan.caveats,
  };
}

function render(result) {
  const { plan, safety_review: safety, events } = result;
  const needsNoiseDetails = plan.noise_profile.input_quality?.status === "needs_noise_description";
  renderTrace(events);
  renderProfile(plan.noise_profile);
  renderMeasurement(plan.measurement_plan);
  renderSuitability(plan.control_suitability);
  renderControls(plan.recommended_controls, plan.blocked_controls);
  renderConclusion(plan.analysis_conclusion);
  renderMap(activeScenario, plan);

  elements.json.textContent = JSON.stringify(plan, null, 2);
  elements.iterationBadge.textContent = `${result.iterations} iteration`;
  elements.confidenceBadge.textContent = plan.noise_profile.confidence;
  elements.measurementBadge.textContent = plan.measurement_plan.privacy_mode;
  elements.privacyBadge.textContent = plan.privacy.raw_audio_retained ? "raw audio retained" : "raw audio off";

  const ancText = needsNoiseDetails ? "Need details" : plan.anc_policy.enabled ? "ANC limited" : "ANC blocked";
  elements.ancBadge.textContent = ancText;
  elements.ancBadge.className = `badge ${needsNoiseDetails || plan.anc_policy.enabled ? "warn" : "blocked"}`;
  elements.mapBadge.textContent = ancText;
  elements.mapBadge.className = elements.ancBadge.className;
  elements.conclusionBadge.textContent = plan.analysis_conclusion.anc_decision;
  elements.conclusionBadge.className = elements.ancBadge.className;
  elements.statusDecision.textContent = needsNoiseDetails ? "Need noise details" : safety.decision === "blocked" ? "ANC blocked" : "Plan ready";
}

function renderTrace(events) {
  elements.trace.innerHTML = "";
  events.forEach((event, index) => {
    const li = document.createElement("li");
    li.className = "trace-item";
    li.innerHTML = `
      <div class="trace-step">${index + 1}</div>
      <div>
        <strong>${escapeHtml(event.agent)}</strong>
        <span>${escapeHtml(event.summary)}</span>
      </div>
    `;
    elements.trace.appendChild(li);
  });
}

function renderProfile(profile) {
  const rows = [
    ["Classes", profile.noise_classes.join(", ")],
    ["Bands", profile.dominant_bands.join(", ")],
    ["Pattern", profile.event_pattern],
    ["Source", profile.source_model],
  ];
  elements.noiseProfile.innerHTML = rows
    .map(
      ([label, value]) => `
        <div class="metric-card">
          <span>${escapeHtml(label)}</span>
          <strong>${escapeHtml(value)}</strong>
        </div>
      `,
    )
    .join("");
}

function renderMeasurement(measurementPlan) {
  const blocks = [
    ["Objective", [measurementPlan.objective]],
    ["Where and when to measure", measurementPlan.recommended_windows],
    ["Mic or phone positions", measurementPlan.microphone_positions],
    ["Derived features", measurementPlan.derived_features_to_extract],
  ];

  elements.measurement.innerHTML = blocks
    .map(
      ([label, items]) => `
        <div class="measurement-block">
          <strong>${escapeHtml(label)}</strong>
          <ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </div>
      `,
    )
    .join("");
}

function renderSuitability(suitability) {
  const labels = {
    near_field_anc: "Near-field ANC",
    passive_insulation: "Passive insulation",
    masking_sound: "Masking sound",
    hearing_protection: "Hearing protection",
  };

  elements.suitability.innerHTML = Object.entries(labels)
    .map(([key, label]) => {
      const row = suitability[key];
      const width = Math.max(5, Math.round(row.score * 100));
      return `
        <div class="suitability-row">
          <div>
            <strong>${escapeHtml(label)}</strong>
            <p>${escapeHtml(row.status)}</p>
          </div>
          <div>
            <div class="meter ${escapeHtml(row.status)}"><span style="width:${width}%"></span></div>
            <p>${escapeHtml(row.reason)}</p>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderControls(recommended, blocked) {
  elements.recommended.innerHTML = recommended.map(controlItem).join("");
  elements.blocked.innerHTML = blocked.map(controlItem).join("");
}

function renderConclusion(conclusion) {
  elements.conclusion.innerHTML = `
    <div>
      <strong>Decision</strong>
      <p>${escapeHtml(conclusion.summary)}</p>
    </div>
    <div>
      <strong>Rationale</strong>
      <p>${escapeHtml(conclusion.rationale)}</p>
    </div>
    <div>
      <strong>Next step</strong>
      <p>${escapeHtml(conclusion.next_step)}</p>
    </div>
  `;
}

function controlItem(control) {
  return `
    <li>
      <strong>${escapeHtml(control.type)}</strong>
      <span>${escapeHtml(control.reason)}</span>
    </li>
  `;
}

function renderMap(scenario, plan) {
  const config = scenarioDefaults[scenario];
  elements.sourceLabel.textContent = config.sourceLabel;
  elements.noiseWaves.innerHTML = wavePaths(config.waves);

  const quiet = document.getElementById("quietZone");
  quiet.style.opacity = plan.anc_policy.enabled ? "1" : "0.38";
}

function wavePaths(kind) {
  const cls = kind === "airport" ? "airport" : kind === "blocked" ? "blocked" : "noise";
  const paths =
    kind === "airport"
      ? [
          "M92 118 C188 70, 292 86, 392 142 C468 184, 534 210, 628 220",
          "M88 176 C210 134, 294 150, 402 202 C488 244, 546 256, 626 266",
          "M90 238 C206 210, 304 228, 410 276 C482 310, 552 318, 626 330",
        ]
      : [
          "M78 94 C178 92, 240 128, 324 168 C402 206, 500 220, 626 218",
          "M78 166 C168 168, 246 188, 330 222 C422 260, 512 276, 626 282",
          "M78 238 C160 240, 246 254, 340 300 C420 338, 520 342, 626 332",
        ];

  return paths.map((path) => `<path class="wave ${cls}" d="${path}" />`).join("");
}

function headlineFor(plan, safety) {
  if (plan.noise_profile.input_quality?.status === "needs_noise_description") {
    return "Need a noise description before choosing controls.";
  }
  if (safety.decision === "blocked") return "ANC is blocked for this profile; use non-ANC controls first.";
  if (plan.anc_policy.enabled) return "Use a mitigation-first plan with limited local low-frequency ANC.";
  return "Use non-ANC mitigation controls for this noise profile.";
}

function caveatsFor(ancStatus, profile) {
  const caveats = [
    "This plan is not a medical diagnosis.",
    "A laptop speaker is not a valid actuator for real traffic or aircraft ANC.",
    "Real deployment requires calibrated microphones, speakers, and local DSP.",
  ];
  if (profile.input_quality?.status === "needs_noise_description") {
    caveats.push("No mitigation controls were selected because the input does not describe a noise problem.");
  }
  if (["blocked", "not_recommended"].includes(ancStatus)) {
    caveats.push("ANC is disabled because the profile is not a suitable active-control target.");
  }
  if (["impulsive", "mixed"].includes(profile.event_pattern)) {
    caveats.push("Impulsive events may be better handled by passive controls and alert-aware policies.");
  }
  return caveats;
}

function measurementPlanFor(scenario, profile, suitability) {
  const bands = new Set(profile.dominant_bands);
  const ancStatus = suitability.near_field_anc.status;

  if (profile.input_quality?.status === "needs_noise_description") {
    return {
      objective: "Describe the noise problem before choosing mitigation controls.",
      privacy_mode: "local_features_only",
      recommended_windows: [
        "Wait for an actual noise event before measuring.",
        "Write down when it happens, how long it lasts, and whether it repeats.",
      ],
      microphone_positions: [
        "Main place where the noise bothers you, such as bed, desk, or sofa.",
        "Suspected entry point if known, such as window, wall, door gap, or vent.",
      ],
      observations_to_log: [
        "what the noise sounds like",
        "time of day and duration",
        "room and likely source",
        "impact such as sleep, focus, stress, or safety concern",
      ],
      derived_features_to_extract: [
        "median_dba",
        "peak_dba",
        "dominant_frequency_band",
        "event_pattern",
      ],
      minimum_sample_count: 1,
      safety_notes: [
        "Do not select ANC, masking, or insulation until a real noise target is described.",
        "Keep raw audio local by default; retain only derived acoustic features in the report.",
      ],
    };
  }

  const windows = [
    "Capture one quiet baseline when the target noise is absent.",
    "Capture one representative period when the target noise is present.",
  ];
  if (scenario === "airport" || ["intermittent", "mixed"].includes(profile.event_pattern)) {
    windows.push("Log at least three peak events with timestamps.");
  }
  if (scenario === "intersection" || ["continuous", "mixed"].includes(profile.event_pattern)) {
    windows.push("Measure a 10 to 15 minute nighttime window near the sleep area.");
  }

  const positions = [
    "At the main listener position, such as pillow, desk, or chair.",
    "Near the likely entry path, such as window, wall vent, door gap, or facade.",
  ];
  if (scenario === "custom") positions.push("At one comparison point away from the suspected source.");

  const derived = [
    "median_dba",
    "peak_dba",
    "dominant_frequency_band",
    "event_pattern",
    "low_frequency_dominance",
    "high_frequency_dominance",
  ];
  if (bands.has("high_frequency")) derived.push("impulsive_event_count");

  const safetyNotes = [
    "Keep raw audio local by default; retain only derived acoustic features in the report.",
    "Record whether alarms, sirens, smoke detectors, or urgent speech must remain audible.",
  ];
  if (["partial", "recommended"].includes(ancStatus)) {
    safetyNotes.push("Before active playback, repeat measurements with calibrated microphones and output limits.");
  }

  return {
    objective: measurementObjective(scenario, ancStatus),
    privacy_mode: "local_features_only",
    recommended_windows: windows,
    microphone_positions: positions,
    observations_to_log: [
      "time of day and duration",
      "room, window, and door state",
      "source notes such as traffic, aircraft, machinery, voices, or unknown",
      "user impact such as sleep, focus, stress, or safety concern",
    ],
    derived_features_to_extract: derived,
    minimum_sample_count: scenario === "airport" ? 4 : 2,
    safety_notes: safetyNotes,
  };
}

function measurementObjective(scenario, ancStatus) {
  if (["partial", "recommended"].includes(ancStatus)) {
    return "Confirm whether low-frequency content is stable enough for a limited quiet-zone policy.";
  }
  if (scenario === "custom") return "Collect enough local evidence to classify the noise before choosing controls.";
  return "Confirm the noise profile and collect evidence for non-ANC mitigation.";
}

function observedFeatures() {
  return {
    provided: false,
    raw_audio_retained: false,
    derived_features: {},
    notes: ["No measured features were provided; conclusion is based on complaint and scenario templates."],
  };
}

function analysisConclusion(profile, suitability, ancPolicy) {
  const ancStatus = suitability.near_field_anc.status;
  if (profile.input_quality?.status === "needs_noise_description") {
    return {
      summary: "This input does not describe a noise problem yet, so NoiceCance is asking for measurement context instead of choosing controls.",
      confidence: "low",
      anc_decision: "not_recommended",
      rationale: suitability.near_field_anc.reason,
      next_step: "Describe the noise source, timing, location, and impact, or provide local derived audio features.",
    };
  }

  if (ancPolicy.enabled) {
    return {
      summary: "Limited local ANC may be considered only after measurement confirms the low-frequency target.",
      confidence: profile.confidence,
      anc_decision: ancStatus,
      rationale: suitability.near_field_anc.reason,
      next_step: "Run the measurement plan, then validate calibration before any active playback.",
    };
  }
  if (ancStatus === "blocked") {
    return {
      summary: "ANC is not suitable for the current profile; prioritize passive or source controls.",
      confidence: profile.confidence,
      anc_decision: ancStatus,
      rationale: suitability.near_field_anc.reason,
      next_step: "Document peaks, entry paths, and non-ANC control priorities using the measurement plan.",
    };
  }
  return {
    summary: "More local evidence is needed before recommending active control.",
    confidence: profile.confidence,
    anc_decision: ancStatus,
    rationale: suitability.near_field_anc.reason,
    next_step: "Collect derived features and rerun the planner with measured observations.",
  };
}

function setScenario(scenario) {
  activeScenario = scenario;
  elements.tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.scenario === scenario));
  elements.complaint.value = scenarioDefaults[scenario].complaint;
  runAgentLoop();
}

function exportJson() {
  if (!currentResult) runAgentLoop();
  const blob = new Blob([JSON.stringify(currentResult.plan, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${currentResult.plan.plan_id}.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function stripFlags(profile) {
  const { flags, ...rest } = profile;
  return rest;
}

function eventPattern(flags) {
  if (flags.impulsive && flags.intermittent) return "mixed";
  if (flags.impulsive) return "impulsive";
  if (flags.intermittent) return "intermittent";
  return "continuous";
}

function sourceModel(scenario, flags) {
  if (scenario === "intersection") return "outdoor traffic transmitted through window and room reflections";
  if (scenario === "airport") return "outdoor aircraft noise transmitted through building envelope with room reflections";
  if (scenario === "custom" && flags.low) return "local low-frequency source hypothesis requires measurement";
  if (scenario === "custom" && !flags.high) return "local source hypothesis requires measurement";
  if (flags.high) return "unpredictable high-frequency source with reflections";
  return "environmental noise with unknown source geometry";
}

function containsAny(text, words) {
  return words.some((word) => text.includes(word));
}

function appendUnique(items, value) {
  if (!items.includes(value)) items.push(value);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

elements.tabs.forEach((tab) => tab.addEventListener("click", () => setScenario(tab.dataset.scenario)));
elements.run.addEventListener("click", runAgentLoop);
elements.export.addEventListener("click", exportJson);
elements.complaint.addEventListener("input", () => {
  elements.statusDecision.textContent = "Input changed";
});

setScenario(activeScenario);
