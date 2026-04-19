export class ErrorHandler {
  static handle(err: unknown): never {
    if (err instanceof Error) {
      const msg = err.message;
      if (msg.includes("Not Found") || msg.includes("404")) {
        console.error("Skill not found. Check the skill name and repository configuration.");
      } else if (msg.includes("403") || msg.includes("Forbidden")) {
        console.error("Access denied. Check your GitHub token has the required permissions.");
      } else if (msg.includes("ENOTFOUND") || msg.includes("fetch failed") || msg.includes("network")) {
        console.error("Network error. Check your internet connection.");
      } else {
        console.error(`Error: ${msg}`);
      }
    } else {
      console.error("An unexpected error occurred.");
    }
    process.exit(1);
  }
}
