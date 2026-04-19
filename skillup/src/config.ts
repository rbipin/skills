import { join } from "node:path";
import yaml from "js-yaml";

export interface RepoConfig {
  repo: string;
  branch: string;
}

export interface Config {
  repos: RepoConfig[];
  skillDirs: string[];
  outputDir: string;
}

const DEFAULTS: Config = {
  repos: [{ repo: "github/awesome-copilot", branch: "main" }],
  skillDirs: ["skills", ".github/skills", ".claude/skills", ".agents/skills"],
  outputDir: ".agents/skills",
};

const CONFIG_NAMES = [".skillup.json", ".skillup.yaml", ".skillup.yml"];

export class ConfigLoader {
  static async load(): Promise<Config> {
    for (const name of CONFIG_NAMES) {
      const filePath = join(process.cwd(), name);
      const file = Bun.file(filePath);
      if (await file.exists()) {
        const text = await file.text();
        let parsed: Partial<Config>;
        if (name.endsWith(".json")) {
          parsed = JSON.parse(text) as Partial<Config>;
        } else {
          parsed = yaml.load(text) as Partial<Config>;
        }
        return { ...DEFAULTS, ...parsed };
      }
    }
    return { ...DEFAULTS };
  }
}
