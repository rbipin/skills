import { Command } from "commander";
import { printBanner } from "./banner.ts";
import { ConfigLoader } from "./config.ts";
import { TokenResolver } from "./auth.ts";
import { GitHubFetcher } from "./fetcher.ts";
import { InteractiveCLI } from "./interactive.ts";
import { ErrorHandler } from "./errors.ts";

const program = new Command();

program
  .name("skillup")
  .description("Install agent skills from GitHub repositories")
  .version("1.0.0")
  .argument("[name]", "Skill name to install directly")
  .option("-l, --list", "List available skills")
  .action(async (name: string | undefined, options: { list?: boolean }) => {
    try {
      await printBanner();
      const config = await ConfigLoader.load();
      const token = await TokenResolver.resolve();
      const fetcher = new GitHubFetcher(token, config);
      const cli = new InteractiveCLI(fetcher, config);

      if (options.list) {
        const sources = await fetcher.listSkillNames();
        if (sources.length === 0) {
          console.log("No skills found.");
        } else {
          console.log("Available skills:");
          for (const s of sources) {
            console.log(`  - ${s.name}  (${s.owner}/${s.repo}@${s.branch})`);
          }
        }
      } else if (name) {
        await cli.install(name);
      } else {
        await cli.run();
      }
    } catch (err) {
      ErrorHandler.handle(err);
    }
  });

program.parse();
