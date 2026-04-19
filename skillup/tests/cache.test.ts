import { describe, it, expect, beforeEach, afterEach, spyOn, mock } from "bun:test";

// Prevent real mkdir from running (it uses Bun.write internally)
mock.module("node:fs/promises", () => ({ mkdir: async () => {} }));

const SHA_A = "abc123";
const SHA_B = "def456";
const OWNER = "my-org";
const REPO = "my-repo";
const BRANCH = "main";

function makeFakeFile(exists: boolean, content?: unknown) {
  return {
    exists: async () => exists,
    json: async () => content,
  } as unknown as ReturnType<typeof Bun.file>;
}

describe("CacheStore", () => {
  let fileSpy: ReturnType<typeof spyOn>;
  let writeSpy: ReturnType<typeof spyOn>;

  beforeEach(() => {
    fileSpy = spyOn(Bun, "file");
    writeSpy = spyOn(Bun, "write").mockResolvedValue(0 as never);
  });

  afterEach(() => {
    fileSpy.mockRestore();
    writeSpy.mockRestore();
  });

  it("returns null when cache file does not exist", async () => {
    fileSpy.mockReturnValue(makeFakeFile(false));
    const { CacheStore } = await import("../src/cache.ts");
    const store = new CacheStore();
    expect(await store.get(OWNER, REPO, BRANCH, SHA_A)).toBeNull();
  });

  it("returns null when cached SHA does not match", async () => {
    fileSpy.mockReturnValue(makeFakeFile(true, { sha: SHA_B, data: { key: "value" } }));
    const { CacheStore } = await import("../src/cache.ts");
    const store = new CacheStore();
    expect(await store.get(OWNER, REPO, BRANCH, SHA_A)).toBeNull();
  });

  it("returns cached data when SHA matches", async () => {
    const data = { skills: ["foo", "bar"] };
    fileSpy.mockReturnValue(makeFakeFile(true, { sha: SHA_A, data }));
    const { CacheStore } = await import("../src/cache.ts");
    const store = new CacheStore();
    expect(await store.get(OWNER, REPO, BRANCH, SHA_A)).toEqual(data);
  });

  it("returns null and does not throw when json() fails", async () => {
    fileSpy.mockReturnValue({
      exists: async () => true,
      json: async () => { throw new Error("bad json"); },
    } as unknown as ReturnType<typeof Bun.file>);
    const { CacheStore } = await import("../src/cache.ts");
    const store = new CacheStore();
    expect(await store.get(OWNER, REPO, BRANCH, SHA_A)).toBeNull();
  });

  it("writes a serialised entry on set()", async () => {
    fileSpy.mockReturnValue(makeFakeFile(false));
    const { CacheStore } = await import("../src/cache.ts");
    const store = new CacheStore();
    const data = { tree: { "skills/foo/SKILL.md": { type: "blob" } } };
    await store.set(OWNER, REPO, BRANCH, SHA_A, data);

    // Find the Bun.write call that wrote the JSON cache file
    const jsonCall = writeSpy.mock.calls.find(([p]) => (p as string).endsWith(".json"));
    expect(jsonCall).toBeDefined();
    const parsed = JSON.parse(jsonCall![1] as string);
    expect(parsed.sha).toBe(SHA_A);
    expect(parsed.data).toEqual(data);
  });

  it("cache filename sanitises characters illegal on Windows", async () => {
    fileSpy.mockReturnValue(makeFakeFile(false));
    const { CacheStore } = await import("../src/cache.ts");
    const store = new CacheStore();
    await store.set("org", "repo", "feature/my-branch", SHA_A, {});

    const jsonCall = writeSpy.mock.calls.find(([p]) => (p as string).endsWith(".json"));
    expect(jsonCall).toBeDefined();
    // The filename portion (after last separator) must not contain illegal chars
    const filename = (jsonCall![0] as string).split(/[\\/]/).pop()!;
    expect(filename).not.toMatch(/[/\\:*?"<>|]/);
  });
});
