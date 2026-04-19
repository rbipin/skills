import { homedir } from "node:os";
import { join } from "node:path";

/**
 * Returns the platform-appropriate config directory for skillup:
 *   Windows : %APPDATA%\skillup  (C:\Users\<user>\AppData\Roaming\skillup)
 *   macOS   : ~/.config/skillup
 *   Linux   : ~/.config/skillup
 */
export function getConfigDir(): string {
  if (process.platform === "win32") {
    const appData = process.env["APPDATA"];
    return appData ? join(appData, "skillup") : join(homedir(), "AppData", "Roaming", "skillup");
  }
  return join(homedir(), ".config", "skillup");
}

export function getCacheDir(): string {
  return join(getConfigDir(), "cache");
}

export function getTokenFile(): string {
  return join(getConfigDir(), "token");
}
