# Agent Instructions for `skillup`

## Overview

`skillup` is a cross-platform Bun CLI tool that fetches agent skill definitions from GitHub repositories and installs them into a local project directory. It resolves transitive skill dependencies (BFS), caches GitHub tree data per-SHA, and supports interactive multi-select or direct-name installation.

## Project Structure

```
skillup/
├── src/
│   ├── platform.ts     # Cross-platform config/cache/token paths
│   ├── errors.ts       # Friendly error messages → process.exit(1)
│   ├── banner.ts       # Optional terminal banner (assets/ninja.png) + ASCII fallback
│   ├── config.ts       # ConfigLoader — reads .skillup.{json,yaml,yml}
│   ├── cache.ts        # CacheStore — disk cache keyed by repo SHA
│   ├── auth.ts         # TokenResolver — env → file → gh CLI → prompt
│   ├── parser.ts       # SkillParser — gray-matter frontmatter → SkillMeta
│   ├── fetcher.ts      # GitHubFetcher — Octokit + cache integration
│   ├── resolver.ts     # SkillResolver — BFS transitive dependency resolver
│   ├── writer.ts       # SkillWriter — writes resolved skill files to disk
│   ├── interactive.ts  # InteractiveCLI — autocompleteMultiselect + listr2 UI
│   └── index.ts        # Entry point — commander CLI wiring
├── scripts/
│   └── build.ts        # Bun.build() → dist/index.js
├── tests/              # bun:test unit tests (37 tests, 0 failures)
├── package.json
├── tsconfig.json
└── plan.md             # Full design decisions and implementation notes
```

## Commands

```bash
bun src/index.ts            # Run in dev mode
bun src/index.ts --list     # List available skills
bun src/index.ts <name>     # Install a skill by name
bun test tests/             # Run all tests
bun run build               # Build dist/index.js via Bun.build()
```

## Key Design Decisions

### Cross-Platform Paths (`src/platform.ts`)
All config, cache, and token file paths go through `src/platform.ts`. Never hardcode `~/.config` — always call `getConfigDir()`, `getCacheDir()`, or `getTokenFile()`.

| Platform | Config directory |
|---|---|
| Windows | `%APPDATA%\skillup` |
| macOS/Linux | `~/.config/skillup` |

### Bun APIs
- File I/O: `Bun.file(path).text()` / `.json()` / `.exists()` and `Bun.write()`
- Child processes: `Bun.spawnSync()` (always wrap in try/catch — throws if binary not in PATH)
- `node:fs/promises` `mkdir` is still used for directory creation
- `path.join()` for all path construction — never string concatenation with `/`

### Auth Flow (`src/auth.ts`)
Resolution order: `GITHUB_TOKEN` env var → token file → `gh auth token` CLI → interactive prompt. When falling through to the prompt, a `@clack/prompts` `note()` box is shown with the GitHub PAT creation URL and required permissions (Contents: Read-only).

### Caching (`src/cache.ts`)
Cache files live at `<configDir>/cache/<owner>__<repo>__<branch>.json`. Filenames are sanitised to remove characters illegal on Windows NTFS. The cache is invalidated whenever the remote branch SHA changes.

### BFS Resolver (`src/resolver.ts`)
`SkillResolver.resolveMultiple(names)` uses a visited `Set` for cycle safety and deduplication. Skills listed under `skills:` in a `SKILL.md` frontmatter are queued as transitive dependencies.

### Repo Config Format (`src/config.ts` + `src/fetcher.ts`)
The `repo` field must be `owner/repo` format. Full GitHub URLs (`https://github.com/owner/repo`) are also accepted — `GitHubFetcher.listSkillNames()` normalises them by stripping the `github.com/` prefix and `.git` suffix. Default config ships with `owner/repo` format.

### Banner (`src/banner.ts`)
Renders `assets/ninja.png` via `terminal-image`. If the image is missing, returns empty output, or throws, `printTextBanner()` is called instead — it prints a UTF-8 box art fallback so something always appears regardless of terminal graphics support.

### Interactive Picker (`src/interactive.ts`)
Uses `autocompleteMultiselect` from `@clack/prompts` 1.2.0. Flow: fetch all skill names → fetch all `SKILL.md` descriptions in parallel (`Promise.allSettled`) → show filterable multiselect with `maxItems: 25` and per-option `hint: "owner/repo · description[:100]"`. Type to filter inline; space to select.

## Conventions

- All source imports use `.ts` extensions (e.g. `import { foo } from "./foo.ts"`) — required by `moduleResolution: Bundler`
- Tests use `bun:test` — mock with `spyOn` and always call `mockRestore()` in `afterEach` when spying on globals like `Bun.file` or `Bun.write`
- Do not add `node:fs` direct reads/writes — use `Bun.file()` / `Bun.write()` instead
- Do not hardcode platform-specific path separators or home directory paths

## What to Watch Out For

- `Bun.spawnSync` throws (does not return non-zero) when the binary is not found — always wrap in try/catch
- `spyOn(Bun, "file")` replaces the global `Bun.file`; if not restored it breaks Bun's internal WriteStream usage in subsequent tests
- `terminal-image` v3 API: `terminalImage.buffer(Buffer, options)` — if it returns empty output on unsupported terminals, the ASCII fallback in `banner.ts` handles it
- `@clack/prompts` must be **1.2.0+** — `autocompleteMultiselect` does not exist in 0.9.x
- Repo strings in `.skillup.yml` must be `owner/repo` format (full URLs are normalised automatically but `owner/repo` is canonical)
