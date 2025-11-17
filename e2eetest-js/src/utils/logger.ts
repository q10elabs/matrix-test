/**
 * Logger utility providing formatted console output with timestamps and levels.
 */

type LogLevel = "DEBUG" | "INFO" | "WARN" | "ERROR";

interface LogOptions {
  level?: LogLevel;
}

function formatTimestamp(): string {
  const now = new Date();
  return now.toISOString().replace("T", " ").slice(0, 19);
}

export const logger = {
  debug(message: string, ...args: unknown[]): void {
    console.log(`${formatTimestamp()} [DEBUG] ${message}`, ...args);
  },

  info(message: string, ...args: unknown[]): void {
    console.log(`${formatTimestamp()} [INFO] ${message}`, ...args);
  },

  warn(message: string, ...args: unknown[]): void {
    console.warn(`${formatTimestamp()} [WARN] ${message}`, ...args);
  },

  error(message: string, ...args: unknown[]): void {
    console.error(`${formatTimestamp()} [ERROR] ${message}`, ...args);
  },

  section(title: string): void {
    const line = "=".repeat(60);
    console.log(line);
    console.log(title);
    console.log(line);
  },
};
