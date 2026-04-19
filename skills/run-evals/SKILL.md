---
name: run-evals
description: "Run a full eval pipeline for any skill that has an evals.json. Creates an iteration workspace, runs each eval with and without the skill using sub-agents, grades outputs with LLM-as-judge, compiles benchmark.json, fills prose insights, and generates the dashboard HTML. WHEN: run evals, evaluate skill, benchmark skill, measure skill performance, start evaluation iteration."
applyTo: [copilot-agent]
compatibility:
  - Python 3.x (stdlib only — no third-party dependencies)
  - Scripts: .agents/skills/run-evals/scripts/
  - Dashboard asset: .agents/skills/run-evals/scripts/assets/dashboard.html
skills: [create-skill]
triggersOn:
  - User asks to run evals or benchmark a skill
  - User provides a skill name with an evals.json
---

# Run Evals — Skill Eval Pipeline Orchestrator

Drives the full evaluation pipeline for any skill with an `evals.json`. Orchestrates sub-agents for eval runs and LLM-as-judge grading, captures session metrics, compiles a benchmark, fills prose insights, and generates the dashboard — all in a single skill invocation.

---

## When to Use

- Running a new evaluation iteration for a skill
- Benchmarking skill performance vs. no-skill baseline
- Adding an iteration to the unified workspace `dashboard.html`

## When Not to Use

- Reviewing or editing an existing benchmark (edit `benchmark.json` directly)
- Skills that do not have an `evals.json` (create one first)

---

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| Skill name | Yes | Name of the skill to evaluate (e.g., `create-skill`). Must have `evals/evals.json`. |

## Concurrency

**Always run evals sequentially.** Session-metrics capture uses "most recent session" detection (`--current`), so concurrent sub-agents collide. This is the only sequencing constraint — everything else is done inline by the orchestrator.

---

## Workflow

Let `SKILL = <skill name>`, `SROOT = .agents\skills\run-evals`, `EVALS = .agents\skills\{SKILL}\evals\evals.json`.

### Step 0 — Detect host agent

```
python {SROOT}\scripts\detect_host_agent.py
```

Prints one of `copilot | claude | codex | unknown`. Remember this value as `HOST`. If `unknown`, stop and ask the user to set `EVAL_HOST_AGENT` (e.g., `copilot`).

### Step 1 — Validate evals.json

```
python {SROOT}\scripts\validate_evals_json.py {EVALS}
```

Exits non-zero with precise errors if the file is malformed. Fix and retry before continuing.

### Step 2 — Create iteration workspace

```
python {SROOT}\scripts\setup_iteration.py {SKILL} {EVALS}
```

Emits JSON describing the new `ITER_DIR` and every `eval-{id}-{slug}` folder (with `with_skill/` and `without_skill/` subfolders already created). Iteration numbering, slug generation, and folder creation are all handled by the script — no manual scanning.

### Step 3 — Run each eval (sequential)

For each eval in the plan, perform **three sub-agent calls in order**:

1. **Run with skill** — launch a `general-purpose` sub-agent with the prompt template `{SROOT}\prompts\run_eval.md`, substituting:
   - `{{CONDITION}}` = `with_skill`
   - `{{SKILL_NAME}}` = `{SKILL}`
   - `{{TASK}}` = the eval's `prompt`
   - `{{OUT_DIR}}` = `{ITER_DIR}\eval-{id}-{slug}\with_skill`
   - `{{HOST}}` = value from Step 0

2. **Run without skill** — same template, but `{{CONDITION}}` = `without_skill`, `{{OUT_DIR}}` = the `without_skill` folder, and the sub-agent must not use any skill.

3. **Grade both conditions** — one grading sub-agent per eval using `{SROOT}\prompts\grade_eval.md`, substituting the two output folders and the eval's `assertions`. It writes `grading.json` to **both** `with_skill/` and `without_skill/`.

Wait for each sub-agent to complete before launching the next.

### Step 4 — Compile benchmark

```
python {SROOT}\scripts\compile_benchmark.py
```

With no arguments it auto-picks the latest `iteration-*` under the current workspace and writes `benchmark.json`. It tolerates missing `duration_seconds`/`api_duration_ms` and records `host_agent` from the first `timing.json`.

### Step 5 — Fill FILL fields

Open `{ITER_DIR}\benchmark.json` and replace every `"FILL: ..."` placeholder inline (you have full run context — no sub-agent needed):

| Field | Content |
|-------|---------|
| `note` | 1–2 sentences on iteration intent |
| `evals[*].prompt_summary` | One-line summary of the eval prompt |
| `run_summary.key_insight` | One sentence on the most important delta |
| `run_summary.with_skill.insight` | One sentence on skill performance pattern |
| `run_summary.without_skill.insight` | One sentence on baseline pattern |

Then verify none remain:

```
python {SROOT}\scripts\compile_benchmark.py --check
```

Exits 0 when `FILL:` count is zero.

### Step 6 — Refresh unified dashboard

```
python {SROOT}\scripts\refresh_dashboard.py
```

Auto-detects the workspace (latest `*-workspace` under CWD), copies the static `dashboard.html` asset into the workspace root (only if missing or the packaged asset is newer), and rewrites `iterations.json` with all `iteration-*/benchmark.json` entries sorted newest-first.

Because the dashboard loads JSON via `fetch()`, it must be served over HTTP — from the workspace root:

```
python -m http.server 8000
```

Then open <http://localhost:8000/dashboard.html>. Use the **Iteration** picker to switch, and **Compare to** to diff any two iterations side-by-side.

> The legacy `generate_dashboard.py` still works and forwards to `refresh_dashboard.py`.

### Step 7 — Summarize

Report to the user: iteration number, host agent, number of evals, mean pass rates (with_skill vs without_skill), and the serve command from Step 6.

---

## Validation

- [ ] Every `eval-*` has `with_skill/{timing.json,grading.json}` and `without_skill/{timing.json,grading.json}`
- [ ] `benchmark.json` has no `FILL:` strings (`compile_benchmark.py --check` returns 0)
- [ ] Workspace-level `dashboard.html` + `iterations.json` exist and show the correct host agent pill when served over HTTP
- [ ] Evals ran sequentially
- [ ] `timing.json` was written by each eval sub-agent itself (never by the orchestrator)

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Parallel eval sub-agents | Always sequential — `--current` session capture breaks with concurrency |
| Orchestrator runs metrics itself | The eval sub-agent writes its own `timing.json` as its final step (template enforces this) |
| Wrong iteration number | Use `setup_iteration.py` — do not compute by hand |
| `FILL:` left in benchmark.json | Run `compile_benchmark.py --check`; it exits non-zero until clean |
| `HOST=unknown` | Set `EVAL_HOST_AGENT=copilot` (or claude/codex) and retry Step 0 |
| Missing `timing.json` | Re-run capture: `python {SROOT}\scripts\capture_metrics.py --host {HOST} --session <id> --json <out>\timing.json` |
