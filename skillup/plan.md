# Plan: Implement skillup in Bun

## Status: Implemented

All source files have been created and the project builds and tests successfully.

---

## Bun API Substitutions

| Old (Node / tool-chain) | New (Bun) |
|---|---|
| `tsx` (dev runner) | removed — `bun src/index.ts` runs TS natively |
| `esbuild` + build script (`.mjs`) | `Bun.build()` in `scripts/build.ts` |
| `node:fs` reads / writes | `Bun.file()`, `Bun.write()` |
| `node:child_process` execSync | `Bun.spawnSync()` |
| `@types/node` only | add `@types/bun` |
| `"moduleResolution": "NodeNext"` | `"moduleResolution": "Bundler"` — no `.js` import hacks |
| Node ≥24 engine requirement | `"bun": ">=1.0.0"` |

### Dependencies removed

- `tsx` (devDep)
- `esbuild` (devDep)

### Dependencies added

- `@types/bun` (devDep)

### Dependencies kept

- `@clack/prompts` **1.2.0** — interactive UI (upgraded from 0.9.0 for `autocompleteMultiselect`)
- `listr2` — task list UI for install progress
- `@octokit/rest` — GitHub API (fetch-based, Bun-compatible)
- `commander` — CLI arg parsing
- `gray-matter` — YAML frontmatter
- `js-yaml` — YAML config files
- `terminal-image` — banner image rendering

---

## Files Created

### Toolchain

| File | Purpose |
|---|---|
| `package.json` | Scripts, engines, dependencies for Bun |
| `tsconfig.json` | `module: ESNext`, `moduleResolution: Bundler` |
| `scripts/build.ts` | `Bun.build()` replacing the old esbuild script |

### Source (`src/`)

| File | Class / Export | Role |
|---|---|---|
| `src/platform.ts` | `getConfigDir()` `getCacheDir()` `getTokenFile()` | **Cross-platform config paths.** Windows → `%APPDATA%\skillup`, macOS/Linux → `~/.config/skillup` |
| `src/errors.ts` | `ErrorHandler` | `handle(err)` — friendly messages for skill-not-found, 403, network errors |
| `src/banner.ts` | `printBanner()` | Reads `assets/ninja.png` via `Bun.file()`, renders with `terminal-image`. Falls back to ASCII text banner if image missing or terminal unsupported |
| `src/config.ts` | `ConfigLoader` | `load()` — reads `.skillup.{json,yaml,yml}` via `Bun.file()`, merges with DEFAULTS |
| `src/cache.ts` | `CacheStore` | Disk cache at platform config dir `cache/`. Uses `Bun.file()` + `Bun.write()`. Invalidates on HEAD SHA change |
| `src/auth.ts` | `TokenResolver` | `resolve()` — env → file → `gh auth token` → interactive prompt + optional save. Shows GitHub token creation link when prompting |
| `src/parser.ts` | `SkillParser` | `parse(content)` — wraps `gray-matter` → `SkillMeta { name, description, skills[] }` |
| `src/fetcher.ts` | `GitHubFetcher` | Octokit wrapper + in-memory Promise caches + `CacheStore`. Methods: `listSkillNames`, `fetchSkillFiles`, `fetchSkillMd`, `findSkillSources` |
| `src/resolver.ts` | `SkillResolver` | BFS transitive resolver. `resolve()` + `resolveMultiple()`. Dedup by name, cycle-safe |
| `src/writer.ts` | `SkillWriter` | `write(resolvedSkills, outputDir)` — `Bun.write()` per file, `mkdir` from `node:fs/promises` |
| `src/interactive.ts` | `InteractiveCLI` | `run()` (autocomplete multiselect picker) + `install(name)` (direct). Uses `@clack/prompts` `autocompleteMultiselect` + `listr2`. Shows 25 items at a time; type to filter inline |
| `src/index.ts` | — | Entry point. `commander` CLI wiring: no args → interactive, `<name>` → direct install, `--list` → list |

### Tests (`tests/`)

| File | Tests | What's covered |
|---|---|---|
| `tests/platform.test.ts` | 5 | `getConfigDir` per platform, `APPDATA` fallback, `getCacheDir`, `getTokenFile` |
| `tests/parser.test.ts` | 5 | Full frontmatter, missing fields default to `""` / `[]`, no frontmatter |
| `tests/errors.test.ts` | 8 | 404, 403, network, unknown, non-Error values, `process.exit(1)` |
| `tests/cache.test.ts` | 6 | Cache miss, SHA mismatch, SHA hit, corrupt JSON, write content, Windows-safe filenames |
| `tests/config.test.ts` | 3 | Defaults, JSON config merge, YAML config merge |
| `tests/resolver.test.ts` | 6 | Single skill, BFS deps, deduplication, cycle detection, not-found error, `resolveMultiple` |
| `tests/writer.test.ts` | 3 | File paths, file content, multiple skills |

Run tests: `bun test tests/`

---

## Cross-Platform Design

All config/cache/token paths are resolved via `src/platform.ts`:

| Platform | Config directory |
|---|---|
| Windows | `%APPDATA%\skillup` (falls back to `~\AppData\Roaming\skillup`) |
| macOS | `~/.config/skillup` |
| Linux | `~/.config/skillup` |

Additional cross-platform practices:
- `path.join()` used for all path construction (handles `\` vs `/`)
- `node:os` `homedir()` for home directory resolution
- `node:fs/promises` `mkdir({ recursive: true })` for directory creation
- Cache filenames sanitise characters illegal on Windows NTFS (`/ \ : * ? " < > |`)
- `Bun.spawnSync(["gh", "auth", "token"])` wrapped in try/catch for when `gh` is not installed

---

## Key Design Notes

### tsconfig

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "strict": true,
    "noUncheckedIndexedAccess": true,
    "noImplicitOverride": true
  }
}
```

Imports use `.ts` extensions (e.g. `import { foo } from "./foo.ts"`) — no `.js` workaround needed with Bundler resolution.

### File I/O pattern (Bun)

```ts
// Read
const text = await Bun.file(path).text();
const json = await Bun.file(path).json();
const exists = await Bun.file(path).exists();
// Write
await Bun.write(path, content);
// mkdir still uses node:fs/promises
import { mkdir } from "node:fs/promises";
```

### Child process (Bun)

```ts
try {
  const result = Bun.spawnSync(["gh", "auth", "token"]);
  if (result.exitCode === 0) return result.stdout.toString().trim();
} catch {
  // gh not installed or not in PATH
}
```

### Build script

```ts
const result = await Bun.build({
  entrypoints: ["./src/index.ts"],
  outdir: "./dist",
  target: "node",    // Node-compatible for npx/bunx distribution
  minify: true,
});
```

### Config defaults

```ts
const DEFAULTS: Config = {
  repos: [{ repo: "meijer-stme/stme-common-ai-foundation", branch: "main" }],
  skillDirs: ["skills", ".github/skills", ".claude/skills", ".agents/skills"],
  outputDir: ".agents/skills",
};
```

### Token resolution order

1. `GITHUB_TOKEN` env var
2. Platform config dir `token` file (`Bun.file().text()`)
3. `gh auth token` CLI (`Bun.spawnSync`) — wrapped in try/catch
4. Interactive PAT prompt (shows GitHub token creation link + required permissions) → optional save (`Bun.write`)

### Cache strategy

- File: `<configDir>/cache/<owner>__<repo>__<branch>.json` (illegal chars sanitised)
- Stored: `{ sha: string, data: Record<string, unknown> }`
- Invalidated when GitHub refs API returns a different SHA

### BFS resolver

```
queue = rootNames
visited = Set<string>
while queue not empty:
  name = queue.shift()
  if visited.has(name) continue
  visited.add(name)
  source = findSkillSources(name) → pickSource if multiple
  files  = fetchSkillFiles(source)
  meta   = SkillParser.parse(SKILL.md from files)
  queue.push(...meta.skills)  ← transitive deps
```

### Writer

- Output: `{cwd}/{outputDir}/{skillName}/`
- `mkdir({ recursive: true })` then `Bun.write(filePath, content)` for each file

### InteractiveCLI cancellation

```ts
if (isCancel(selected)) process.exit(0);  // @clack/prompts cancelled
if (typeof result === "symbol") process.exit(0);  // select/text cancelled
```

### Repo config format

The `repo` field in `.skillup.{json,yaml,yml}` (and the built-in DEFAULTS) must use `owner/repo` format, not a full GitHub URL. `GitHubFetcher` normalises URLs automatically — if the value contains `github.com/` it strips the prefix and `.git` suffix — so both formats work, but `owner/repo` is canonical.

### Banner

`printBanner()` attempts to render `assets/ninja.png` via `terminal-image`. If the image is missing, the rendered output is empty, or rendering throws, it falls back to a UTF-8 box art text banner. The fallback ensures something always appears even on terminals that do not support sixel/kitty graphics.

### Interactive skill picker (`autocompleteMultiselect`)

`@clack/prompts` 1.2.0 added `autocompleteMultiselect` which combines type-ahead filtering with multiselect in a single UI. The `run()` flow:

1. Spinner — fetch all skill names (one cached tree API call per repo)
2. Spinner — fetch `SKILL.md` for every skill in parallel (`Promise.allSettled`) to populate descriptions
3. `autocompleteMultiselect` — type to filter by name, space to select, `maxItems: 25` controls viewport
4. Each option `hint` shows `owner/repo · description[:100]`
5. `Listr` task list installs selected skills via BFS resolver
