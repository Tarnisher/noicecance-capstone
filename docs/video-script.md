# NoiceCance Demo Video Script

Target length: 4:30 to 5:00

Submission requirement: YouTube video, 5 minutes or less.

Goal: show that NoiceCance is a local-first agent workflow, not a generic ANC promise. The demo should make the agent roles, MCP server, CLI, safety/privacy choices, and web experience clear.

## Recording Setup

- Open the repository root in a terminal.
- Open `web/index.html` in a browser.
- Keep browser zoom at 90-100 percent so the dashboard fits.
- Keep a second terminal ready for CLI commands.
- Do not show private files, API keys, `.env` files, browser accounts, or unrelated folders.
- If a terminal path shows your local username, that is not ideal for a public video. Crop the terminal title bar or use a short prompt if possible.

## Commands to Prepare

```powershell
conda run -n cvuni python -m unittest discover -s tests
```

```powershell
conda run -n cvuni python src\noicecance_core\cli.py assess --complaint "A low hum appears after midnight near the bedroom wall."
```

```powershell
conda run -n cvuni python src\noicecance_core\cli.py assess --complaint "Sharp high-pitched unpredictable sound near the window."
```

```powershell
conda run -n cvuni python src\noicecance_core\cli.py assess --complaint "hello"
```

```powershell
conda run -n cvuni python src\noicecance_core\cli.py assess --complaint "Low hum after midnight near bedroom wall." --out outputs\mitigation_plan.json
```

Do not run the MCP server as a long manual demo unless you have an MCP client ready. In the video, show the MCP server code and the MCP tests instead.

## Timeline and Narration

### 0:00-0:25 - Title and Problem

Screen:
- README title or web demo header.

Narration:

NoiceCance is a local-first noise assessment agent workflow for the Agents for Good track. The problem is that people often know a room is too loud, but they do not know what to measure or which mitigation strategy is physically realistic. The project does not treat active noise cancellation as the default answer. It first asks what evidence is needed and whether ANC is safe or suitable.

### 0:25-0:55 - Architecture and Course Concepts

Screen:
- Show README `Architecture` or scroll to `Course Concepts`.

Narration:

The project demonstrates a multi-agent workflow with a User Intent Agent, Acoustic Scene Agent, Measurement Advisor Agent, Policy Planning Agent, Safety and Privacy Agent, and Report Agent. It also includes an official MCP server, a local CLI, structured JSON output, and security boundaries such as local-first operation and no raw-audio retention by default.

Key concepts to mention:

- Multi-agent system.
- MCP Server.
- Security features.
- CLI / agent skill style workflow.
- Deployability through local web and terminal commands.

### 0:55-1:45 - Web Demo: High-Frequency Rejection

Screen:
- Open `web/index.html`.
- Select `High-frequency rejection`.
- Point to `ANC blocked`, `Noise Profile`, `Measurement Plan`, `Recommended`, and `Blocked`.

Narration:

This scenario is intentionally a rejection case. The complaint is sharp, high-pitched, and unpredictable. NoiceCance classifies it as high-frequency noise and blocks near-field ANC and ultrasonic cancellation. It recommends passive or source-control options instead. This is important because the agent is allowed to say no when the physics or safety constraints do not support ANC.

### 1:45-2:35 - Web Demo: Custom Low-Hum Complaint

Screen:
- Select `Custom assessment`.
- Type or paste:

```text
A low hum appears after midnight near the bedroom wall.
```

- Click `Run agent loop`.
- Show `Agent Trace`, `Measurement Plan`, and `Evidence Conclusion`.

Narration:

For a low-frequency complaint, the project does not jump straight to hardware. It creates a measurement-first plan. It asks where and when to measure, what observations to log, and which derived features would be useful. Limited near-field ANC is only a possible future option after measurement confirms a stable low-frequency target.

### 2:35-3:00 - Web Demo: Irrelevant Input

Screen:
- In custom input, enter:

```text
hello
```

- Click `Run agent loop`.
- Show `Need noise details`, `clarify_noise_problem`, and `collect_basic_observations`.

Narration:

This is the input-quality gate. If the user enters irrelevant text, NoiceCance does not invent a mitigation plan. It asks for basic noise context instead: source, timing, room, and impact. This protects users from confident but unsupported recommendations.

### 3:00-3:45 - Local CLI Demo

Screen:
- Terminal.
- Run the low-hum command.
- Run the high-frequency command, or show prepared output if time is tight.
- Run the `hello` command.

Narration:

The web page is the inspection interface. The CLI is the local workflow entry point. The same agent loop can be run from the terminal, which makes the project easier to integrate with other tools. The low-hum case produces a measurement-first plan, the high-frequency case blocks ANC, and the `hello` case asks for noise details instead of making up a plan.

### 3:45-4:15 - JSON Export and MCP Server

Screen:
- Run the `--out outputs\mitigation_plan.json` command.
- Briefly open or show the first lines of `outputs\mitigation_plan.json`.
- Open `src/noicecance_core/mcp_server.py`.
- Show tool names:
  - `analyze_noise_profile`
  - `generate_mitigation_plan`
  - `run_agent_loop`
  - `check_safety_limits`

Narration:

The stable output is `mitigation_plan.json`, which contains the measurement plan, noise profile, recommended controls, blocked controls, safety rules, and conclusion. The same local tools are exposed through an official MCP server using the MCP Python SDK. The MCP server does not read arbitrary local files, execute shell commands, upload audio, or call external services.

### 4:15-4:40 - Tests and Build Quality

Screen:
- Run or show:

```powershell
conda run -n cvuni python -m unittest discover -s tests
```

- Show `Ran 22 tests` and `OK`.

Narration:

The deterministic test suite checks the safety gates, tool behavior, CLI behavior, MCP server tools, and the multi-agent revision path. This makes the demo repeatable and reviewable without requiring cloud credentials or API keys.

### 4:40-5:00 - Wrap-Up

Screen:
- Return to README or web demo.

Narration:

NoiceCance is still a capstone prototype. It does not yet ingest real audio files, run real DSP, or control hardware. The value is the local-first agent workflow: understand the complaint, recommend measurements, classify the profile, reject unsafe ANC claims, and export a structured plan. The next step is local audio feature extraction that stores only derived features, not raw recordings.

Optional closing line:

The same Git repository can be opened by tools such as Codex or Antigravity for further implementation, because the core logic, CLI, MCP server, tests, and documentation are all kept in one public project.

## Must Show Checklist

- Web demo high-frequency case blocks ANC.
- Web demo custom low-hum case creates a measurement-first plan.
- Web demo `hello` input asks for noise details.
- CLI runs at least one meaningful complaint.
- CLI or terminal shows JSON export.
- MCP server code is visible.
- Test result shows 22 tests OK.
- Safety/privacy limits are said out loud.

## Do Not Claim

- Do not claim real-time noise cancellation is implemented.
- Do not claim laptop speakers can cancel real traffic or aircraft noise.
- Do not claim real audio ingestion is implemented.
- Do not claim ADK scaffolding is implemented.
- Do not claim a cloud deployment exists unless one is added later.
- Do not claim ultrasonic cancellation can directly cancel audible environmental noise.

## Assets to Capture

- Web dashboard screenshot for Kaggle Media Gallery cover image.
- Screenshot of `ANC blocked` high-frequency scenario.
- Screenshot of CLI `hello` output showing `needs_noise_description`.
- Screenshot of test output showing 22 tests OK.
