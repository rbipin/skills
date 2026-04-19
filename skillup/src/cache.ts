import { join } from "node:path";
import { mkdir } from "node:fs/promises";
import { getCacheDir } from "./platform.ts";

interface CacheEntry {
  sha: string;
  data: Record<string, unknown>;
}

export class CacheStore {
  private cacheDir: string;

  constructor() {
    this.cacheDir = getCacheDir();
  }

  private cacheFile(owner: string, repo: string, branch: string): string {
    // Replace slashes in case owner/repo contain them (they shouldn't, but be safe)
    const safeName = `${owner}__${repo}__${branch}`.replace(/[/\\:*?"<>|]/g, "_");
    return join(this.cacheDir, `${safeName}.json`);
  }

  async get(
    owner: string,
    repo: string,
    branch: string,
    currentSha: string,
  ): Promise<Record<string, unknown> | null> {
    const file = Bun.file(this.cacheFile(owner, repo, branch));
    if (!(await file.exists())) return null;
    try {
      const entry = (await file.json()) as CacheEntry;
      if (entry.sha !== currentSha) return null;
      return entry.data;
    } catch {
      return null;
    }
  }

  async set(
    owner: string,
    repo: string,
    branch: string,
    sha: string,
    data: Record<string, unknown>,
  ): Promise<void> {
    await mkdir(this.cacheDir, { recursive: true });
    const entry: CacheEntry = { sha, data };
    await Bun.write(this.cacheFile(owner, repo, branch), JSON.stringify(entry));
  }
}
