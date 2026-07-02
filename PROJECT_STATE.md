# NoiceCance Project State

Last updated: 2026-06-29

## Purpose

NoiceCance is a mitigation-first AI agent prototype for residents exposed to transportation noise. The first MVP scenarios are:

- Homes facing a two-way six-lane intersection.
- Homes near an airport.
- A high-frequency or impulsive noise rejection case used to prove that the system blocks unsuitable ANC proposals.

The project is intended for the Kaggle AI Agents: Intensive Vibe Coding Capstone Project, likely under the Agents for Good track.

## Core Positioning

NoiceCance is not a universal active-noise-control generator.

The stable output is `mitigation_plan.json`. An `anc_policy` section is optional and should appear only when local low-frequency near-field ANC is plausible. If the noise profile is high-frequency, impulsive, unpredictable, or strongly reverberant, the system should disable ANC and recommend non-ANC controls such as passive insulation, room changes, source control, masking, or certified hearing protection.

The real-time acoustic path is local-first. LLMs or agents should not run the low-latency audio loop. Agents operate at the supervisory layer: intent interpretation, scene analysis, policy planning, safety review, reporting, and future tool orchestration.

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
  - `Policy Planning Agent`
  - `Safety & Privacy Agent`
  - `Report Agent`
  - revision loop for unsafe plans

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

The web demo is static and has no build step. It supports scenario switching, free-text complaint input, an agent trace, sound-field visualization, control suitability, recommended and blocked controls, and exportable `mitigation_plan.json`.

### Schemas and Examples

- `schemas/mitigation_plan.schema.json`
- `examples/intersection_plan.json`
- `examples/airport_plan.json`
- `examples/high_frequency_rejected_plan.json`

### Tests

- `tests/test_tools.py`
- `tests/test_agent_loop.py`
- `tests/test_stdio_tool_server.py`

Current expected result: 13 tests pass.

## Verified Commands

Run from repository root:

```powershell
node --check noicecance-capstone\web\app.js
conda run -n cvuni python -m unittest discover -s noicecance-capstone\tests
conda run -n cvuni python -m compileall noicecance-capstone\src noicecance-capstone\tests
```

Useful demos:

```powershell
conda run -n cvuni python noicecance-capstone\src\noicecance_core\demo.py --scenario intersection
conda run -n cvuni python noicecance-capstone\src\noicecance_core\tools_demo.py check --scenario high_frequency
conda run -n cvuni python noicecance-capstone\src\noicecance_core\agent_loop_demo.py --scenario high_frequency --force-unsafe-first-draft
conda run -n cvuni python noicecance-capstone\src\noicecance_core\stdio_tool_client_demo.py --scenario high_frequency
```

Static web demo:

```text
noicecance-capstone/web/index.html
```

Browser verification already confirmed:

- Desktop page renders.
- Initial intersection scenario shows 5 trace steps and `ANC limited`.
- High-frequency scenario shows `ANC blocked`.
- No console errors during tested interactions.
- Mobile-width check had no horizontal overflow.

## Known Environment Notes

- Use conda environment `cvuni` for Python commands.
- No new dependencies have been installed.
- `git status` currently fails with `fatal: not a git repository`, even though a `.git` directory is visible. Do not rely on Git status until this is investigated.
- Python `compileall` has created `__pycache__` directories. They were not deleted because no destructive cleanup was requested.

## Handoff Rule

If context is compressed or a new agent takes over, read these files first:

1. `PROJECT_STATE.md`
2. `README.md`
3. `.agents-cli-spec.md`

After meaningful project changes, update `PROJECT_STATE.md` in the same turn.

## Not Implemented Yet

- Official MCP SDK server.
- ADK / Agents CLI scaffold.
- LLM-backed agents.
- Real audio recording ingestion.
- Real DSP or hardware integration.
- Sound-field physics simulation beyond the current planning visualization.
- Docker or cloud deployment.
- Kaggle Writeup.
- YouTube video script.
- Polished project README for final submission.

## Recommended Next Steps

1. Decide whether to upgrade the MCP-like stdio bridge to an official MCP server. This may require a dependency approval step.
2. Decide whether to scaffold an ADK project with Agents CLI or keep the current lightweight structure until the web demo is stronger.
3. Improve the static web demo with stronger visual polish and a clearer first-run narrative for judges.
4. Add a simple local audio feature extractor that stores only derived features, not raw audio.
5. Start `docs/writeup-draft.md` and `docs/video-script.md` for Kaggle submission materials.

## Current Best Story for Judges

NoiceCance helps transportation-noise residents understand what can and cannot be mitigated. It uses an agentic workflow to turn a complaint into a structured mitigation plan, rejects unsafe or physically unsuitable ANC proposals, and produces an exportable plan that can later drive calibrated local hardware. The project is deliberately honest about limits: ANC is optional, local, low-frequency, and safety-gated rather than universal.
