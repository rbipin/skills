import { describe, it, expect, spyOn } from "bun:test";

function makeFakeFile(exists: boolean, content: string) {
  return {
    exists: async () => exists,
    text: async () => content,
  } as unknown as ReturnType<typeof Bun.file>;
}

describe("ConfigLoader.load", () => {
  it("returns defaults when no config file exists", async () => {
    spyOn(Bun, "file").mockReturnValue(makeFakeFile(false, ""));
    const { ConfigLoader } = await import("../src/config.ts");
    const config = await ConfigLoader.load();
    expect(config.repos).toEqual([{ repo: "meijer-stme/stme-common-ai-foundation", branch: "main" }]);
    expect(config.skillDirs).toContain("skills");
    expect(config.outputDir).toBe(".agents/skills");
  });

  it("merges JSON config over defaults", async () => {
    const custom = JSON.stringify({ outputDir: "custom/output" });
    let callCount = 0;
    spyOn(Bun, "file").mockImplementation((path: unknown) => {
      // First call is for .skillup.json — make it exist
      if (callCount++ === 0) return makeFakeFile(true, custom);
      return makeFakeFile(false, "");
    });
    const { ConfigLoader } = await import("../src/config.ts");
    const config = await ConfigLoader.load();
    expect(config.outputDir).toBe("custom/output");
    // Defaults still present for un-overridden keys
    expect(config.skillDirs).toContain("skills");
  });

  it("merges YAML config over defaults", async () => {
    const yaml = "outputDir: yaml-output\n";
    let callCount = 0;
    spyOn(Bun, "file").mockImplementation(() => {
      // Skip .skillup.json (callCount 0), return yaml on second call
      if (callCount++ === 0) return makeFakeFile(false, "");
      return makeFakeFile(true, yaml);
    });
    const { ConfigLoader } = await import("../src/config.ts");
    const config = await ConfigLoader.load();
    expect(config.outputDir).toBe("yaml-output");
  });
});
