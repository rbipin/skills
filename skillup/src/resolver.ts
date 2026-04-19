import { select } from "@clack/prompts";
import type { GitHubFetcher, SkillSource, SkillFile } from "./fetcher.ts";
import { SkillParser } from "./parser.ts";
import type { SkillMeta } from "./parser.ts";

export interface ResolvedSkill {
  source: SkillSource;
  files: SkillFile[];
  meta: SkillMeta;
}

export class SkillResolver {
  constructor(private fetcher: GitHubFetcher) {}

  private async pickSource(name: string, sources: SkillSource[]): Promise<SkillSource> {
    if (sources.length === 1) return sources[0]!;
    const choice = await select({
      message: `Multiple sources found for "${name}". Pick one:`,
      options: sources.map((s) => ({
        value: s,
        label: `${s.owner}/${s.repo} (${s.branch}) — ${s.path}`,
      })),
    });
    if (typeof choice === "symbol") process.exit(0);
    return choice as SkillSource;
  }

  async resolve(name: string): Promise<ResolvedSkill[]> {
    return this.resolveMultiple([name]);
  }

  async resolveMultiple(names: string[]): Promise<ResolvedSkill[]> {
    const visited = new Set<string>();
    const queue = [...names];
    const results: ResolvedSkill[] = [];

    while (queue.length > 0) {
      const name = queue.shift()!;
      if (visited.has(name)) continue;
      visited.add(name);

      const sources = await this.fetcher.findSkillSources(name);
      if (sources.length === 0) throw new Error(`Skill not found: ${name}`);

      const source = await this.pickSource(name, sources);
      const files = await this.fetcher.fetchSkillFiles(source);

      const skillMdFile = files.find((f) => f.name === "SKILL.md");
      if (!skillMdFile) throw new Error(`SKILL.md not found for skill: ${name}`);

      const meta = SkillParser.parse(skillMdFile.content);
      results.push({ source, files, meta });

      // Queue transitive dependencies (BFS, cycle-safe via visited set)
      for (const dep of meta.skills) {
        if (!visited.has(dep)) queue.push(dep);
      }
    }

    return results;
  }
}
