import { join } from "node:path";
import { mkdir } from "node:fs/promises";
import type { ResolvedSkill } from "./resolver.ts";

export class SkillWriter {
  async write(resolvedSkills: ResolvedSkill[], outputDir: string): Promise<void> {
    // outputDir is relative to cwd; path.join handles both Windows and Unix separators
    const base = join(process.cwd(), outputDir);

    for (const skill of resolvedSkills) {
      const skillDir = join(base, skill.source.name);
      await mkdir(skillDir, { recursive: true });
      for (const file of skill.files) {
        await Bun.write(join(skillDir, file.name), file.content);
      }
    }
  }
}
