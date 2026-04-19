import { describe, it, expect, spyOn, mock } from "bun:test";
import { join } from "node:path";

// Mock node:fs/promises mkdir before importing writer
mock.module("node:fs/promises", () => ({ mkdir: async () => {} }));

import { SkillWriter } from "../src/writer.ts";
import type { ResolvedSkill } from "../src/resolver.ts";

function makeResolved(name: string, files: { name: string; content: string }[]): ResolvedSkill {
  return {
    source: { owner: "org", repo: "repo", branch: "main", path: `skills/${name}`, name },
    files,
    meta: { name, description: "", skills: [] },
  };
}

describe("SkillWriter.write", () => {
  it("writes each file under <outputDir>/<skillName>/", async () => {
    const writeSpy = spyOn(Bun, "write").mockResolvedValue(0 as never);
    const writer = new SkillWriter();

    const skills = [
      makeResolved("foo", [
        { name: "SKILL.md", content: "# foo" },
        { name: "extra.md", content: "extra" },
      ]),
    ];

    await writer.write(skills, ".agents/skills");

    const calls = writeSpy.mock.calls.map(([p]) => p as string);
    expect(calls).toContain(join(process.cwd(), ".agents/skills", "foo", "SKILL.md"));
    expect(calls).toContain(join(process.cwd(), ".agents/skills", "foo", "extra.md"));
  });

  it("writes the correct content for each file", async () => {
    const writeSpy = spyOn(Bun, "write").mockResolvedValue(0 as never);
    const writer = new SkillWriter();

    await writer.write(
      [makeResolved("bar", [{ name: "SKILL.md", content: "hello" }])],
      "output",
    );

    const call = writeSpy.mock.calls.find(([p]) =>
      (p as string).endsWith(join("bar", "SKILL.md")),
    );
    expect(call).toBeDefined();
    expect(call![1]).toBe("hello");
  });

  it("writes files for multiple skills", async () => {
    const writeSpy = spyOn(Bun, "write").mockResolvedValue(0 as never);
    const writer = new SkillWriter();

    await writer.write(
      [
        makeResolved("skill-a", [{ name: "SKILL.md", content: "a" }]),
        makeResolved("skill-b", [{ name: "SKILL.md", content: "b" }]),
      ],
      "out",
    );

    const paths = writeSpy.mock.calls.map(([p]) => p as string);
    expect(paths.some((p) => p.includes("skill-a"))).toBeTrue();
    expect(paths.some((p) => p.includes("skill-b"))).toBeTrue();
  });
});
