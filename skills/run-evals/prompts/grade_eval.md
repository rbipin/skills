<!--
Prompt template for grading BOTH conditions of a single eval in one sub-agent.

Placeholders:
  {{EVAL_DIR}}    Absolute path to ...\eval-<id>-<slug>\ (has with_skill/ and without_skill/)
  {{ASSERTIONS}}  Numbered markdown list of assertions (same for both conditions)
-->

You are an LLM judge evaluating the outputs of an AI agent under two conditions.

**Eval directory:** `{{EVAL_DIR}}`
This directory contains two subfolders you will grade independently:
- `with_skill\`     — run that used the skill under test
- `without_skill\`  — baseline run that did not use the skill

**Assertions (identical for both conditions):**
{{ASSERTIONS}}

**Your job:**
1. Read every output file in `{{EVAL_DIR}}\with_skill\` (ignore `timing.json`, `session.txt`, and `grading.json`).
2. Evaluate each assertion against those outputs and write `{{EVAL_DIR}}\with_skill\grading.json`.
3. Repeat for `{{EVAL_DIR}}\without_skill\` → write `{{EVAL_DIR}}\without_skill\grading.json`.

**Schema for each grading.json:** follow `.agents\skills\run-evals\assets\grading.json` exactly (read that file for the canonical shape; do not inline it, do not add or remove fields). For each assertion provide:
- `text`: the assertion text (copied verbatim)
- `passed`: `true` or `false`
- `evidence`: one sentence citing specific content from the outputs that justifies your verdict

Compute `summary.passed`, `summary.failed`, `summary.total`, and `summary.pass_rate` (`passed / total`, 2 decimal places) for each condition.

**Rules:**
- Grade the two conditions independently — do not let with_skill results bias without_skill results, or vice versa.
- Do not modify any files other than the two `grading.json` outputs.
- Do not launch further sub-agents.
