import { describe, it, expect } from "bun:test";
import { SkillResolver } from "../src/resolver.ts";
import type { GitHubFetcher, SkillSource, SkillFile } from "../src/fetcher.ts";

// Each test provides exactly one source per skill, so pickSource never calls
// @clack/prompts select() — no module mock needed.

function makeSource(name: string): SkillSource {
  return { owner: "org", repo: "repo", branch: "main", path: `skills/${name}`, name };
}

function makeFiles(name: string, deps: string[] = []): SkillFile[] {
  const lines = deps.length
    ? `---\nname: ${name}\nskills:\n${deps.map((d) => `  - ${d}`).join("\n")}\n---\n`
    : `---\nname: ${name}\n---\n`;
  return [{ name: "SKILL.md", content: lines }];
}

function makeFetcher(
  skillMap: Record<string, { source: SkillSource; files: SkillFile[] }>,
): GitHubFetcher {
  return {
    findSkillSources: async (name: string) => {
      const entry = skillMap[name];
      return entry ? [entry.source] : [];
    },
    fetchSkillFiles: async (source: SkillSource) => {
      return skillMap[source.name]?.files ?? [];
    },
  } as unknown as GitHubFetcher;
}

describe("SkillResolver.resolve", () => {
  it("resolves a single skill with no dependencies", async () => {
    const fetcher = makeFetcher({
      "my-skill": { source: makeSource("my-skill"), files: makeFiles("my-skill") },
    });
    const results = await new SkillResolver(fetcher).resolve("my-skill");
    expect(results).toHaveLength(1);
    expect(results[0]!.source.name).toBe("my-skill");
  });

  it("resolves transitive dependencies (BFS)", async () => {
    const fetcher = makeFetcher({
      "root":  { source: makeSource("root"),  files: makeFiles("root",  ["dep-a"]) },
      "dep-a": { source: makeSource("dep-a"), files: makeFiles("dep-a", ["dep-b"]) },
      "dep-b": { source: makeSource("dep-b"), files: makeFiles("dep-b") },
    });
    const results = await new SkillResolver(fetcher).resolve("root");
    const names = results.map((r) => r.source.name);
    expect(names).toContain("root");
    expect(names).toContain("dep-a");
    expect(names).toContain("dep-b");
    expect(results).toHaveLength(3);
  });

  it("deduplicates shared dependencies", async () => {
    const fetcher = makeFetcher({
      "root":   { source: makeSource("root"),   files: makeFiles("root",   ["a", "b"]) },
      "a":      { source: makeSource("a"),      files: makeFiles("a",      ["shared"]) },
      "b":      { source: makeSource("b"),      files: makeFiles("b",      ["shared"]) },
      "shared": { source: makeSource("shared"), files: makeFiles("shared") },
    });
    const results = await new SkillResolver(fetcher).resolve("root");
    expect(results.filter((r) => r.source.name === "shared")).toHaveLength(1);
  });

  it("is cycle-safe (does not loop infinitely)", async () => {
    const fetcher = makeFetcher({
      "a": { source: makeSource("a"), files: makeFiles("a", ["b"]) },
      "b": { source: makeSource("b"), files: makeFiles("b", ["a"]) },
    });
    const results = await new SkillResolver(fetcher).resolve("a");
    expect(results).toHaveLength(2);
  });

  it("throws when a skill is not found", async () => {
    const fetcher = makeFetcher({});
    await expect(new SkillResolver(fetcher).resolve("missing")).rejects.toThrow(
      "Skill not found: missing",
    );
  });

  it("resolves multiple root skills via resolveMultiple", async () => {
    const fetcher = makeFetcher({
      "x": { source: makeSource("x"), files: makeFiles("x") },
      "y": { source: makeSource("y"), files: makeFiles("y") },
    });
    const results = await new SkillResolver(fetcher).resolveMultiple(["x", "y"]);
    expect(results.map((r) => r.source.name)).toEqual(expect.arrayContaining(["x", "y"]));
  });
});
