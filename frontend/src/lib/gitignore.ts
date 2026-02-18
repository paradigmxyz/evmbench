import ignore, { type Ignore } from "ignore"

export const DEFAULT_IGNORE_PATTERNS = [
  "node_modules",
  ".git",
  ".next",
  "dist",
  "build",
  "out",
  "coverage",
  ".cache",
  "cache",
  "artifacts",
  ".nyc_output",
  "*.log",
  "*.lock",
  ".DS_Store",
  "Thumbs.db",
  ".env",
  ".env.*",
  "*.map",
]

export function createIgnore(patterns: string[]): Ignore {
  return ignore().add(patterns)
}

export function createIgnoreFromGitignore(
  content: string,
  includeDefaults = true,
): Ignore {
  const ig = ignore()
  if (includeDefaults) {
    ig.add(DEFAULT_IGNORE_PATTERNS)
  }
  ig.add(content)
  return ig
}
