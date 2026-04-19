<!--
Prompt template for a single-condition eval run.

Placeholders (substitute before launching the sub-agent):
  {{CONDITION}}     "with_skill" or "without_skill"
  {{SKILL_NAME}}    Name of the skill under test (e.g. create-skill)
  {{TASK}}          The eval's prompt verbatim
  {{OUT_DIR}}       Absolute path to the condition folder
                    (e.g. ...\iteration-N\eval-1-slug\with_skill)
-->

You are running an evaluation for the "{{SKILL_NAME}}" skill.

**Task:** {{TASK}}

**Instructions:**
- Condition: **{{CONDITION}}**
  - If condition is `with_skill`: use the "{{SKILL_NAME}}" skill to complete this task.
  - If condition is `without_skill`: **do not** use any skills — work entirely from your own knowledge and tools.
- Write all output files to: `{{OUT_DIR}}`

**Final actions (run these in order as your last steps):**

1. Save your session ID for recovery:
   ```
   python .agents\skills\run-evals\scripts\capture_metrics.py --current --save-id "{{OUT_DIR}}\session.txt"
   ```

2. Capture canonical timing metrics using the saved session ID:
   ```powershell
   $sessionId = Get-Content "{{OUT_DIR}}\session.txt"
   python .agents\skills\run-evals\scripts\capture_metrics.py --session $sessionId --json "{{OUT_DIR}}\timing.json"
   ```

If step 1 fails (no active session found), skip directly to:
```
python .agents\skills\run-evals\scripts\capture_metrics.py --json "{{OUT_DIR}}\timing.json"
```
(This falls back to the most recent session for the detected host agent.)
