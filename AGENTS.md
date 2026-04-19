# Agent Instructions for the `skills` Repository

## Workspace Overview

This repository has two parts:

### 1. Skill definitions (`skills/`)
Agent skill definitions, each in its own subfolder with a `SKILL.md` file.

Currently contains:
- `skills/dotnet-code-review/SKILL.md`
- `skills/dotnet-developer/SKILL.md`
- `skills/dotnet-version-checker/SKILL.md`
- `skills/write-skill/SKILL.md`
- `skills/technical-deep-dive/SKILL.md`

### 2. skillup CLI tool (`skillup/`)
A cross-platform Bun CLI tool that fetches and installs skills from GitHub repositories. See `skillup/AGENTS.md` for full details on working with that sub-project.

The top-level `README.md` is minimal and does not define build or test commands.

## Primary Task

Your job is to help create, update, and maintain agent skill definitions for this repo.
Focus on:
- Adding new skill directories and `SKILL.md` files when requested
- Updating existing skill definitions to reflect repository conventions
- Preserving and reusing existing frontmatter fields and section structure
- Keeping responses concise and directly related to the user request

## Conventions

Follow these conventions when editing or creating skills:
- Skill directory names should be lowercase, alphanumeric, and hyphen-separated
- Each skill directory should contain a single `SKILL.md` file
- `SKILL.md` files must include YAML frontmatter with fields like `name`, `description`, `applyTo`, and optional `compatibility`, `skills`, or `triggersOn`
- Use the `write-skill/SKILL.md` file as the canonical template for new skills
- Keep skill content under roughly 500 lines and avoid unnecessary duplication
- Prefer `applyTo` patterns that reflect file types or agent use cases
- When adding workflow steps, make them numbered and actionable
- Validate the skill by checking for clear purpose, specific workflow steps, and a validation section

## How to Add or Update Skills

When asked to create a new skill:
1. Create a new folder in `skills/` with the skill name
2. Add `SKILL.md` with frontmatter and sections such as Purpose, When to Use, Workflow, Validation, and Common Pitfalls
3. Keep the new skill focused on the requested capability
4. Reference existing skills when possible to align tone and structure

When asked to update an existing skill:
1. Read the current `SKILL.md` content first
2. Preserve existing meaningful sections and metadata
3. Add or modify workflow steps in a way that matches the current voice and structure
4. Do not remove unrelated useful guidance unless it is clearly outdated or incorrect

## Example Prompts

- "Create a new skill that checks .NET support policy and recommends upgrades"
- "Update `dotnet-code-review` to run `dotnet-version-checker` before review"
- "Add a new `skills` folder for a GitHub Actions skill with frontmatter and workflow steps"
- "Review `SKILL.md` files and align their descriptions with repository conventions"

## Notes

- For skill definition work: no build or test automation — focus on the `SKILL.md` documentation itself
- For `skillup/` CLI work: see `skillup/AGENTS.md` — it has its own build (`bun run build`) and test (`bun test tests/`) commands
- Any information written in skill definitions should be grounded in facts and include citation(s) or reference(s) whenever possible
- If user requests require broader repo changes, keep the change minimal and aligned with the skill definition pattern
- Use the `.github/copilot-instructions.md` file as the primary workspace bootstrap document
