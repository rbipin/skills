import { autocompleteMultiselect, spinner, intro, outro, isCancel } from "@clack/prompts";
import { Listr } from "listr2";
import type { GitHubFetcher, SkillSource } from "./fetcher.ts";
import { SkillResolver } from "./resolver.ts";
import { SkillWriter } from "./writer.ts";
import type { Config } from "./config.ts";
import { SkillParser } from "./parser.ts";

interface SkillOption {
  name: string;
  owner: string;
  repo: string;
  description: string;
}

async function loadDescriptions(
  fetcher: GitHubFetcher,
  sources: SkillSource[],
): Promise<SkillOption[]> {
  const results = await Promise.allSettled(
    sources.map((src) =>
      fetcher.fetchSkillMd(src).then((md) => SkillParser.parse(md).description),
    ),
  );
  return sources.map((src, i) => ({
    name: src.name,
    owner: src.owner,
    repo: src.repo,
    description: results[i]?.status === "fulfilled" ? (results[i].value ?? "") : "",
  }));
}

export class InteractiveCLI {
  constructor(
    private fetcher: GitHubFetcher,
    private config: Config,
  ) {}

  async run(): Promise<void> {
    intro("skillup — install agent skills");

    const s = spinner();
    s.start("Fetching available skills...");
    const sources = await this.fetcher.listSkillNames();
    s.stop(`Found ${sources.length} skill(s)`);

    if (sources.length === 0) {
      outro("No skills found in configured repositories.");
      return;
    }

    const s2 = spinner();
    s2.start("Loading descriptions...");
    const options = await loadDescriptions(this.fetcher, sources);
    s2.stop("Ready");

    const C = "\x1b[0m"; // reset (breaks out of clack's dim wrapper)
    const PURPLE = "\x1b[95m"; // bright magenta / purple
    const CYAN = "\x1b[96m"; // bright cyan

    const selected = await autocompleteMultiselect({
      message: "Select skills to install (type to filter):",
      options: options.map((o) => ({
        value: o.name,
        label: `${CYAN}${o.name}${C}`,
        hint: `${C}${PURPLE}${o.owner}/${o.repo}${C} · ${CYAN}${o.description.slice(0, 100)}${C}`,
      })),
      maxItems: 25,
    });

    if (isCancel(selected)) {
      outro("Cancelled.");
      process.exit(0);
    }

    await this._installSkills(selected as string[]);
    outro("Done!");
  }

  async install(name: string): Promise<void> {
    intro(`skillup — installing "${name}"`);
    await this._installSkills([name]);
    outro("Done!");
  }

  private async _installSkills(names: string[]): Promise<void> {
    const resolver = new SkillResolver(this.fetcher);
    const writer = new SkillWriter();

    const tasks = new Listr(
      names.map((name) => ({
        title: `Resolving "${name}"`,
        task: async (_, task) => {
          const resolved = await resolver.resolve(name);
          task.title = `Installed "${name}" (${resolved.length} skill(s) total)`;
          await writer.write(resolved, this.config.outputDir);
        },
      })),
      { concurrent: false },
    );

    await tasks.run();
  }
}
