import { describe, it, expect } from "bun:test";
import { SkillParser } from "../src/parser.ts";

const FULL_SKILL_MD = `---
name: dotnet-developer
description: Helps with .NET development tasks
skills:
  - dotnet-code-review
  - dotnet-version-checker
---

# Skill content here
`;

const MINIMAL_SKILL_MD = `---
name: my-skill
---
`;

const NO_FRONTMATTER = `# Just a plain markdown file\n`;

const EMPTY_SKILLS_LIST = `---
name: standalone
description: No dependencies
skills: []
---
`;

describe("SkillParser.parse", () => {
  it("extracts name, description, and skills from full frontmatter", () => {
    const meta = SkillParser.parse(FULL_SKILL_MD);
    expect(meta.name).toBe("dotnet-developer");
    expect(meta.description).toBe("Helps with .NET development tasks");
    expect(meta.skills).toEqual(["dotnet-code-review", "dotnet-version-checker"]);
  });

  it("defaults description to empty string when absent", () => {
    const meta = SkillParser.parse(MINIMAL_SKILL_MD);
    expect(meta.name).toBe("my-skill");
    expect(meta.description).toBe("");
  });

  it("defaults skills to empty array when absent", () => {
    const meta = SkillParser.parse(MINIMAL_SKILL_MD);
    expect(meta.skills).toEqual([]);
  });

  it("handles empty skills list", () => {
    const meta = SkillParser.parse(EMPTY_SKILLS_LIST);
    expect(meta.skills).toEqual([]);
  });

  it("returns empty defaults when there is no frontmatter", () => {
    const meta = SkillParser.parse(NO_FRONTMATTER);
    expect(meta.name).toBe("");
    expect(meta.description).toBe("");
    expect(meta.skills).toEqual([]);
  });
});
