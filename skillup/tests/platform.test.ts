import { describe, it, expect, afterEach } from "bun:test";
import { homedir } from "node:os";
import { join } from "node:path";

// Store original values so we can restore them
const originalPlatform = process.platform;
const originalAppData = process.env["APPDATA"];

function setPlatform(platform: string) {
  Object.defineProperty(process, "platform", { value: platform, configurable: true });
}

afterEach(() => {
  Object.defineProperty(process, "platform", { value: originalPlatform, configurable: true });
  if (originalAppData === undefined) {
    delete process.env["APPDATA"];
  } else {
    process.env["APPDATA"] = originalAppData;
  }
});

describe("platform — getConfigDir", () => {
  it("returns ~/.config/skillup on linux", async () => {
    setPlatform("linux");
    const { getConfigDir } = await import("../src/platform.ts");
    expect(getConfigDir()).toBe(join(homedir(), ".config", "skillup"));
  });

  it("returns ~/.config/skillup on darwin", async () => {
    setPlatform("darwin");
    const { getConfigDir } = await import("../src/platform.ts");
    expect(getConfigDir()).toBe(join(homedir(), ".config", "skillup"));
  });

  it("uses APPDATA on win32 when env var is set", async () => {
    setPlatform("win32");
    process.env["APPDATA"] = "C:\\Users\\test\\AppData\\Roaming";
    const { getConfigDir } = await import("../src/platform.ts");
    expect(getConfigDir()).toBe(join("C:\\Users\\test\\AppData\\Roaming", "skillup"));
  });

  it("falls back to homedir on win32 when APPDATA is missing", async () => {
    setPlatform("win32");
    delete process.env["APPDATA"];
    const { getConfigDir } = await import("../src/platform.ts");
    expect(getConfigDir()).toBe(join(homedir(), "AppData", "Roaming", "skillup"));
  });
});

describe("platform — getCacheDir / getTokenFile", () => {
  it("getCacheDir is nested under getConfigDir", async () => {
    setPlatform("linux");
    const { getConfigDir, getCacheDir } = await import("../src/platform.ts");
    expect(getCacheDir()).toBe(join(getConfigDir(), "cache"));
  });

  it("getTokenFile is nested under getConfigDir", async () => {
    setPlatform("linux");
    const { getConfigDir, getTokenFile } = await import("../src/platform.ts");
    expect(getTokenFile()).toBe(join(getConfigDir(), "token"));
  });
});
