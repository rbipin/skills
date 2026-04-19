import { text, confirm, note } from "@clack/prompts";
import { mkdir } from "node:fs/promises";
import { dirname } from "node:path";
import { getTokenFile } from "./platform.ts";

export class TokenResolver {
  static async resolve(): Promise<string | undefined> {
    // 1. Environment variable
    const envToken = process.env["GITHUB_TOKEN"];
    if (envToken) return envToken;

    // 2. Token file (platform-appropriate location)
    const tokenFile = getTokenFile();
    const file = Bun.file(tokenFile);
    if (await file.exists()) {
      const saved = (await file.text()).trim();
      if (saved) return saved;
    }

    // 3. gh CLI
    try {
      const result = Bun.spawnSync(["gh", "auth", "token"]);
      if (result.exitCode === 0) {
        const cliToken = result.stdout.toString().trim();
        if (cliToken) return cliToken;
      }
    } catch {
      // gh not installed or not in PATH — continue to interactive prompt
    }

    // 4. Interactive prompt — show token creation guidance first
    note(
      [
        "No GitHub token found. Create a Personal Access Token (PAT) at:",
        "",
        "  https://github.com/settings/personal-access-tokens/new",
        "",
        "Required permission (fine-grained token):",
        "  • Contents      → Read-only",
        "",
        "Or use a classic token (https://github.com/settings/tokens/new)",
        "with the \`repo\` scope (or \`public_repo\` for public repos only).",
      ].join("\n"),
      "GitHub Token Required",
    );

    const token = await text({
      message: "Enter your GitHub Personal Access Token (PAT):",
      placeholder: "ghp_...",
      validate: (v) => (!v ? "Token is required" : undefined),
    });

    if (typeof token === "symbol") return undefined; // cancelled

    const shouldSave = await confirm({
      message: `Save token to ${tokenFile}?`,
      initialValue: false,
    });

    if (shouldSave === true) {
      await mkdir(dirname(tokenFile), { recursive: true });
      await Bun.write(tokenFile, token);
    }

    return token;
  }
}
