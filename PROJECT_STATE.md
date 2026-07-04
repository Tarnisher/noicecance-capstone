# NoiceCance Project State

Last updated: 2026-07-04

## Purpose

NoiceCance is a local-first multi-agent noise assessment and mitigation prototype. It helps users describe a noise problem, plan safe measurements, analyze privacy-preserving derived acoustic features, and generate an evidence-based mitigation plan. The current judge-facing web demo includes:

- Homes facing a two-way six-lane intersection.
- Homes near an airport.
- A high-frequency or impulsive noise rejection case used to prove that the system blocks unsuitable ANC proposals.
- A custom local assessment mode for user-written complaints.

The project is intended for the Kaggle AI Agents: Intensive Vibe Coding Capstone Project, likely under the Agents for Good track.

## Core Positioning

NoiceCance is not a universal active-noise-control generator.

The stable output is `mitigation_plan.json`. It now includes `measurement_plan`, `observed_features`, `analysis_conclusion`, recommended controls, blocked controls, safety rules, privacy rules, and optional `anc_policy`. ANC is only one candidate control and should appear only when local low-frequency near-field ANC is plausible. If the noise profile is high-frequency, impulsive, unpredictable, or strongly reverberant, the system should disable ANC and recommend non-ANC controls such as passive insulation, room changes, source control, masking, or certified hearing protection.

The real-time acoustic path is local-first. LLMs or agents should not run the low-latency audio loop. Agents operate at the supervisory layer: intent interpretation, measurement planning, scene analysis, policy planning, safety review, reporting, and future tool orchestration.

## Safety Boundaries

- Do not claim medical diagnosis or guaranteed sleep improvement.
- Do not claim laptop speakers can cancel real traffic or aircraft noise at room scale.
- Do not claim ultrasonic transducers can directly cancel audible traffic or aircraft noise.
- Do not present ANC as a universal solution.
- Preserve alarms, sirens, smoke detectors, urgent speech, and other safety-critical sounds.
- Do not retain or upload raw audio by default.
- Real active playback requires calibrated microphones, speakers, and local DSP.
- Deployment, Docker, CI/CD, official MCP dependencies, and ADK scaffolding require explicit user approval before editing related files.

## Implemented Structure

### Specification and Docs

- `.agents-cli-spec.md`: project specification, scenarios, agent architecture, tools, safety rules, success criteria.
- `README.md`: current project overview and commands.
- `PROJECT_STATE.md`: authoritative handoff file. The project spec now requires this file to be updated after meaningful architecture, file, command, safety, dependency, test, deployment, or submission-plan changes.

### Deterministic Core

- `src/noicecance_core/core.py`
  - `analyze_noise_profile`
  - `assess_control_suitability`
  - `generate_mitigation_plan`
  - custom local assessment scenario
  - measurement-plan, observed-feature, and analysis-conclusion sections
  - input-quality gate for irrelevant custom text such as greetings

### Tool Adapter

- `src/noicecance_core/tools.py`
  - `analyze_noise_profile_tool`
  - `assess_control_suitability_tool`
  - `generate_mitigation_plan_tool`
  - `check_safety_limits_tool`
  - `TOOLS` registry

### Local Multi-Agent Loop

- `src/noicecance_core/agent_loop.py`
  - `User Intent Agent`
  - `Acoustic Scene Agent`
  - `Measurement Advisor Agent`
  - `Policy Planning Agent`
  - `Safety & Privacy Agent`
  - `Report Agent`
  - revision loop for unsafe plans

### Local CLI

- `src/noicecance_core/cli.py`
  - `assess` command for local free-text complaint assessment
  - `--complaint` input
  - `--out` full JSON export
  - defaults to the `custom` scenario so irrelevant input asks for noise details instead of inheriting a built-in scenario

### Official MCP Server

- `src/noicecance_core/mcp_server.py`
  - built with official `mcp==1.28.1`
  - exposes `analyze_noise_profile`, `generate_mitigation_plan`, `run_agent_loop`, and `check_safety_limits`
  - wraps existing local NoiceCance tools without raw-audio upload or external service calls

### MCP-Like Stdio Bridge

- `src/noicecance_core/stdio_tool_server.py`
  - dependency-free newline-delimited JSON bridge
  - methods: `list_tools`, `call_tool`
  - not an official MCP SDK server
- `src/noicecance_core/stdio_tool_client_demo.py`

### Static Web Demo

- `web/index.html`
- `web/styles.css`
- `web/app.js`

The web demo is static and has no build step. It supports scenario switching, custom complaint input, an agent trace, measurement targets, sound-field visualization, control suitability, recommended and blocked controls, an evidence conclusion, and exportable `mitigation_plan.json`. For irrelevant custom input, it now shows `Need noise details` and asks for structured noise context instead of selecting controls.

### Schemas and Examples

- `schemas/mitigation_plan.schema.json`
- `examples/intersection_plan.json`
- `examples/airport_plan.json`
- `examples/high_frequency_rejected_plan.json`

### Tests

- `tests/test_cli.py`
- `tests/test_mcp_server.py`
- `tests/test_tools.py`
- `tests/test_agent_loop.py`
- `tests/test_stdio_tool_server.py`

Current expected result after the measurement-workflow, CLI, MCP server, and input-quality updates: 22 tests pass.

## Verified Commands

Run from repository root:

```powershell
node --check web\app.js
conda run -n cvuni python -m unittest discover -s tests
conda run -n cvuni python -m compileall src tests
```

Useful demos:

```powershell
conda run -n cvuni python src\noicecance_core\demo.py --scenario intersection
conda run -n cvuni python src\noicecance_core\demo.py --scenario custom --complaint "Low hum after midnight near the bedroom wall."
conda run -n cvuni python src\noicecance_core\tools_demo.py check --scenario high_frequency
conda run -n cvuni python src\noicecance_core\agent_loop_demo.py --scenario high_frequency --force-unsafe-first-draft
conda run -n cvuni python src\noicecance_core\stdio_tool_client_demo.py --scenario high_frequency
```

The official MCP server command starts a stdio server for an MCP client and waits for protocol messages:

```powershell
conda run -n cvuni python src\noicecance_core\mcp_server.py --transport stdio
```

Static web demo:

```text
web/index.html
```

Browser verification confirmed after the latest measurement-workflow UI update:

- Desktop page renders.
- Initial intersection scenario shows 6 trace steps and `ANC limited`.
- High-frequency scenario shows `ANC blocked`.
- Irrelevant custom input such as a greeting shows `Need noise details`, low confidence, `clarify_noise_problem`, and `collect_basic_observations`.
- No console errors during tested interactions.
- Mobile-width check had no horizontal overflow.

## Known Environment Notes

- Use conda environment `cvuni` for Python commands.
- Official MCP dependency `mcp==1.28.1` is pinned in `requirements.txt` and was installed into `cvuni` for verification.
- `noicecance-capstone` is now its own Git repository on branch `main`.
- Python `compileall` has created `__pycache__` directories. They were not deleted because no destructive cleanup was requested.

## Handoff Rule

If context is compressed or a new agent takes over, read these files first:

1. `PROJECT_STATE.md`
2. `README.md`
3. `.agents-cli-spec.md`

After meaningful project changes, update `PROJECT_STATE.md` in the same turn.

## Not Implemented Yet

- ADK / Agents CLI scaffold.
- LLM-backed agents.
- Real audio recording ingestion.
- Real local audio feature extraction from `.wav` files.
- Real DSP or hardware integration.
- Sound-field physics simulation beyond the current planning visualization.
- Docker or cloud deployment.
- Kaggle Writeup final submission. Draft is organized in `docs/writeup-draft.md`.
- YouTube video recording and final link. Script draft is organized in `docs/video-script.md`.
- Final README screenshots and public submission links.

## Recommended Next Steps

1. Record the short demo video from `docs/video-script.md`.
2. Add final GitHub and video links to `README.md` and `docs/writeup-draft.md` when available.
3. Add cover image or screenshots for Kaggle Media Gallery if time allows.
4. Add a simple local audio feature extractor that stores only derived features, not raw audio.
5. Decide whether to scaffold ADK after explicit approval for any new dependencies.

## Current Best Story for Judges

NoiceCance helps users move from a vague noise complaint to an evidence-based action plan. It uses an agentic workflow to interpret the user goal, recommend safe local measurements, analyze derived acoustic features, reject unsafe or physically unsuitable ANC proposals, and export a structured mitigation plan. The project is deliberately honest about limits: ANC is optional, local, low-frequency, and safety-gated rather than universal.
