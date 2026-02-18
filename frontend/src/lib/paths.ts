export function normalizeFilePath(path: string): string {
  return path.replace(/\\/g, "/").replace(/^\.\//, "").replace(/^\//, "")
}

export function truncateFilePath(path: string, maxSegments = 2): string {
  const normalized = normalizeFilePath(path)
  const parts = normalized.split("/")

  if (parts.length <= maxSegments) {
    return normalized
  }

  return `…/${parts.slice(-maxSegments).join("/")}`
}

export function matchPathFlexibly(
  sourcePath: string,
  targetPaths: Set<string>,
): string | null {
  const normalized = normalizeFilePath(sourcePath)

  if (targetPaths.has(normalized)) return normalized

  const parts = normalized.split("/")
  for (let i = 1; i < parts.length; i++) {
    const stripped = parts.slice(i).join("/")
    if (targetPaths.has(stripped)) return stripped
  }

  return null
}
