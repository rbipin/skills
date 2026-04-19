import matter from "gray-matter";

export interface SkillMeta {
  name: string;
  description: string;
  skills: string[];
}

export class SkillParser {
  static parse(content: string): SkillMeta {
    const { data } = matter(content);
    return {
      name: (data["name"] as string) ?? "",
      description: (data["description"] as string) ?? "",
      skills: (data["skills"] as string[]) ?? [],
    };
  }
}
