# NoiceCance: Local-First Noise Assessment Agents

Track: Agents for Good

NoiceCance is a local-first agent workflow for people trying to understand and reduce unwanted environmental noise. Instead of treating active noise cancellation as a universal answer, the project helps a user describe a noise problem, decide what to measure, classify the acoustic situation, and produce an evidence-based mitigation plan with clear safety boundaries.

The project is designed around a practical observation: many noise complaints start as vague experiences. A person may know that a bedroom has a low hum after midnight, that aircraft events wake a family, or that a sharp high-frequency source is painful and unpredictable. They often do not know which evidence to collect or which control strategy is physically realistic. NoiceCance turns that vague complaint into a structured local assessment.

## Problem

Noise mitigation advice often jumps too quickly to products or generic advice. For active noise cancellation, that can be misleading. Open-air whole-room cancellation is not realistic for most traffic, aircraft, voices, reflected room noise, or high-frequency impulsive sources. Some active control may be plausible only for limited low-frequency quiet zones with calibrated microphones, speakers, and local DSP.

The better task for an agent system is not "generate ANC." The better task is:

1. Understand the user's goal and context.
2. Recommend what to measure, where to measure, and when to measure.
3. Analyze the likely noise profile from complaint text and future local derived features.
4. Decide which controls are physically appropriate.
5. Block unsafe or exaggerated recommendations.
6. Export a plan that a user, judge, or future hardware layer can inspect.

This fits the Agents for Good track because the user need is practical, safety-sensitive, and privacy-sensitive. Raw recordings may reveal private home life, so the intended workflow keeps raw audio local and stores only derived acoustic features by default.

## What I Built

NoiceCance currently has four working layers:

- A deterministic Python planning core in `src/noicecance_core/core.py`.
- JSON-like tool adapters, an official MCP server, and a dependency-free stdio bridge.
- A deterministic local multi-agent loop that models the intended agent responsibilities.
- A static browser demo plus a local CLI for free-text assessment.

The stable output is `mitigation_plan.json`. It includes:

- `measurement_plan`: what to measure, where to measure, and which derived features to extract.
- `observed_features`: privacy-preserving feature summaries, not raw audio.
- `noise_profile`: source classes, dominant frequency bands, event pattern, and confidence.
- `control_suitability`: suitability judgments for ANC, passive insulation, masking, and hearing protection.
- `recommended_controls` and `blocked_controls`: practical choices and refused options.
- `analysis_conclusion`: a plain-language decision and next step.
- optional `anc_policy`: included only when limited low-frequency near-field ANC is plausible.

The web demo is the judge-facing inspection surface. It shows four modes: six-lane intersection, airport-adjacent home, high-frequency rejection, and custom local assessment. The CLI is the local workflow entry point. It runs the same agent loop from the terminal:

```powershell
conda run -n cvuni python src\noicecance_core\cli.py assess --complaint "Low hum after midnight near the bedroom wall."
```

It can also export the full agent-loop result:

```powershell
conda run -n cvuni python src\noicecance_core\cli.py assess --complaint "Sharp high-pitched unpredictable sound near the window." --out outputs\mitigation_plan.json
```

## Agent Workflow

The current implementation uses deterministic agents so that the capstone demo is repeatable, testable, and easy to inspect. These agents are intentionally shaped like the future ADK-style architecture:

- User Intent Agent: infers the user goal, privacy preference, and safety assumptions.
- Acoustic Scene Agent: classifies the complaint and optional local features into a noise profile.
- Measurement Advisor Agent: recommends the measurement objective, sample timing, and local observations.
- Policy Planning Agent: generates the mitigation plan and optional ANC policy.
- Safety & Privacy Agent: blocks unsafe ANC, unsupported frequency targets, raw-audio retention, and missed safety sounds.
- Report Agent: produces the final user-facing explanation and exportable JSON.

The loop also supports revision. For example, the high-frequency scenario can intentionally inject an unsafe active-cancellation draft. The Safety & Privacy Agent rejects it and forces a revised non-ANC plan. This is important because the project is not trying to make every case fit ANC. It is trying to make the refusal path explicit and inspectable.

## Safety and Privacy

The safety policy is central to the project:

- No medical diagnosis.
- No claim that laptop speakers can cancel real traffic or aircraft noise at room scale.
- No claim that ultrasonic transducers directly cancel audible environmental noise.
- No default raw-audio upload or retention.
- No active playback unless future hardware is calibrated and safety-limited.
- Alarms, sirens, smoke detectors, urgent speech, and other safety-critical sounds must be preserved.

The privacy model is local-first. The current prototype does not ingest real audio files yet. Future audio support should extract only derived local features such as median dBA, peak dBA, dominant frequency, event count, and frequency-band dominance. The raw recording should remain on the user's machine unless they explicitly opt in.

## Course Concepts Demonstrated

Multi-agent design: NoiceCance separates intent, acoustic scene classification, measurement planning, policy planning, safety review, and reporting into distinct roles with a shared state object and event trace.

Tool use and structured outputs: The deterministic core is wrapped as JSON-like tools, and output follows a structured mitigation-plan schema. The same core powers the web demo, CLI, tool demos, and stdio bridge.

MCP Server: The project includes an official MCP server built with the MCP Python SDK. It exposes `analyze_noise_profile`, `generate_mitigation_plan`, `run_agent_loop`, and `check_safety_limits` as MCP tools. This is the capstone-facing MCP integration, while the older dependency-free stdio bridge remains as a transparent teaching adapter.

Safety guardrails: The Safety & Privacy Agent can reject physically unsupported or unsafe control plans. Irrelevant custom input such as "hello" produces `needs_noise_description` and asks for more noise context instead of inventing a mitigation plan.

Deployability: The current prototype runs locally with no API keys, no cloud account, no network dependency, and no build step for the static web demo. That makes it easier for judges to inspect the project and for future tools such as Antigravity to take over the same Git repository.

## Validation

The current deterministic test suite covers:

- high-frequency ANC rejection
- partial low-frequency ANC suitability
- local measurement workflow fields
- irrelevant custom input handling
- tool chaining
- safety summaries
- stdio bridge behavior
- local CLI behavior
- official MCP server tool registration and tool calls
- safety revision loop behavior

Verification commands:

```powershell
node --check web\app.js
conda run -n cvuni python -m unittest discover -s tests
conda run -n cvuni python -m compileall src tests
```

Current result: 22 Python tests pass.

Manual CLI checks:

```powershell
conda run -n cvuni python src\noicecance_core\cli.py assess --complaint "A low hum appears after midnight near the bedroom wall."
conda run -n cvuni python src\noicecance_core\cli.py assess --complaint "Sharp high-pitched unpredictable sound near the window."
conda run -n cvuni python src\noicecance_core\cli.py assess --complaint "hello"
```

The low-hum case produces a measurement-first low-frequency plan with limited near-field ANC as a possible future control. The high-frequency case blocks ANC. The irrelevant input case asks for noise details and does not invent a plan.

## Demo Flow

A short demo can show:

1. Open the static web demo and select the high-frequency rejection scenario. The page shows `ANC blocked`.
2. Enter a custom low-hum complaint. The page updates the agent trace, measurement plan, evidence conclusion, and recommended controls.
3. Enter `hello`. The page asks for noise details instead of producing a fake control plan.
4. Run the CLI low-hum, high-frequency, and `hello` examples.
5. Export `outputs\mitigation_plan.json` with `--out` and show the structured agent-loop result.

This demonstrates both faces of the project: the web demo is the inspection interface, while the CLI is the local agent workflow entry point.

## Limitations

The project is still a capstone prototype. It does not yet include real audio ingestion, a local `.wav` feature extractor, ADK scaffolding, LLM-backed agents, Docker deployment, cloud deployment, real-time DSP, or hardware control. The sound-field visualization is explanatory rather than a physics simulation.

These limitations are intentional for the current phase. The goal is to demonstrate the reasoning workflow, safety gates, local-first design, and honest refusal of unsupported ANC claims before adding heavier infrastructure.

## Next Steps

The next technical step is a simple local audio feature extractor that stores only derived features, not raw audio. After that, the existing MCP tools can be consumed by ADK agents. A later hardware phase could use the exported `mitigation_plan.json` to configure a calibrated local DSP system for limited low-frequency quiet-zone testing.

The next submission step is to publish the cleaned repository, add the final GitHub URL, record a short demo video if needed, and replace the placeholders below.

## Project Links

Public project link: https://github.com/Tarnisher/noicecance-capstone

Video: https://youtu.be/giKIYIX2Uxw
