import { Octokit } from "@octokit/rest";
import type { Config } from "./config.ts";
import { CacheStore } from "./cache.ts";

export interface SkillSource {
  owner: string;
  repo: string;
  branch: string;
  /** Repo-relative path to the skill folder, e.g. "skills/dotnet-developer" */
  path: string;
  name: string;
}

export interface SkillFile {
  name: string;
  content: string;
}

type TreeItem = { type?: string; path?: string };

export class GitHubFetcher {
  private octokit: Octokit;
  private cache: CacheStore;
  private config: Config;
  private shaCache = new Map<string, string>();
  private treeCache = new Map<string, Promise<Record<string, TreeItem>>>();

  constructor(token: string | undefined, config: Config) {
    this.octokit = new Octokit({ auth: token, headers: { "X-GitHub-Api-Version": "2022-11-28" } });
    this.cache = new CacheStore();
    this.config = config;
  }

  private repoKey(owner: string, repo: string, branch: string): string {
    return `${owner}/${repo}@${branch}`;
  }

  private async getSha(owner: string, repo: string, branch: string): Promise<string> {
    const key = this.repoKey(owner, repo, branch);
    const cached = this.shaCache.get(key);
    if (cached) return cached;
    const { data } = await this.octokit.repos.getBranch({ owner, repo, branch });
    const sha = data.commit.sha;
    this.shaCache.set(key, sha);
    return sha;
  }

  private getTree(owner: string, repo: string, branch: string): Promise<Record<string, TreeItem>> {
    const key = this.repoKey(owner, repo, branch);
    let promise = this.treeCache.get(key);
    if (!promise) {
      promise = this._fetchTree(owner, repo, branch);
      this.treeCache.set(key, promise);
    }
    return promise;
  }

  private async _fetchTree(
    owner: string,
    repo: string,
    branch: string,
  ): Promise<Record<string, TreeItem>> {
    const sha = await this.getSha(owner, repo, branch);
    const diskCache = await this.cache.get(owner, repo, branch, sha);
    if (diskCache) return diskCache as Record<string, TreeItem>;

    const { data } = await this.octokit.git.getTree({
      owner,
      repo,
      tree_sha: sha,
      recursive: "1",
    });

    const tree: Record<string, TreeItem> = {};
    for (const item of data.tree) {
      if (item.path) tree[item.path] = item as TreeItem;
    }

    await this.cache.set(owner, repo, branch, sha, tree as Record<string, unknown>);
    return tree;
  }

  async listSkillNames(): Promise<SkillSource[]> {
    const sources: SkillSource[] = [];

    for (const repoConfig of this.config.repos) {
      const repoStr = repoConfig.repo.includes("github.com/")
        ? repoConfig.repo.split("github.com/")[1]!.replace(/\.git$/, "").split("?")[0]!
        : repoConfig.repo;
      const [owner, repo] = repoStr.split("/") as [string, string];
      const { branch } = repoConfig;
      const tree = await this.getTree(owner, repo, branch);

      for (const skillDir of this.config.skillDirs) {
        const dirDepth = skillDir.split("/").length;
        for (const treePath of Object.keys(tree)) {
          if (!treePath.startsWith(`${skillDir}/`) || !treePath.endsWith("/SKILL.md")) continue;
          const parts = treePath.split("/");
          const skillName = parts[dirDepth];
          if (skillName && !sources.some((s) => s.name === skillName)) {
            sources.push({
              owner,
              repo,
              branch,
              path: `${skillDir}/${skillName}`,
              name: skillName,
            });
          }
        }
      }
    }

    return sources;
  }

  async findSkillSources(name: string): Promise<SkillSource[]> {
    const all = await this.listSkillNames();
    return all.filter((s) => s.name === name);
  }

  async fetchSkillMd(source: SkillSource): Promise<string> {
    return this._fetchFileContent(source.owner, source.repo, source.branch, `${source.path}/SKILL.md`);
  }

  async fetchSkillFiles(source: SkillSource): Promise<SkillFile[]> {
    const tree = await this.getTree(source.owner, source.repo, source.branch);
    const prefix = `${source.path}/`;
    const files: SkillFile[] = [];

    for (const [treePath, item] of Object.entries(tree)) {
      if (!treePath.startsWith(prefix)) continue;
      if (item.type !== "blob") continue;
      const fileName = treePath.slice(prefix.length);
      if (fileName.includes("/")) continue; // only direct children

      const content = await this._fetchFileContent(
        source.owner,
        source.repo,
        source.branch,
        treePath,
      );
      files.push({ name: fileName, content });
    }

    return files;
  }

  private async _fetchFileContent(
    owner: string,
    repo: string,
    ref: string,
    path: string,
  ): Promise<string> {
    const { data } = await this.octokit.repos.getContent({ owner, repo, ref, path });
    if ("content" in data && typeof data.content === "string") {
      return Buffer.from(data.content, "base64").toString("utf-8");
    }
    throw new Error(`Could not fetch file: ${path}`);
  }
}
