import type { FileData } from "@/lib/file-loader"
import { matchPathFlexibly, normalizeFilePath } from "@/lib/paths"
import type { Vulnerability } from "@/types"

export function validateFileData(
  fileData: FileData[],
  vulnerabilities: Vulnerability[],
): string | null {
  if (vulnerabilities.length === 0) return null

  const lineCounts = new Map<string, number>()
  const pathSet = new Set<string>()
  for (const file of fileData) {
    const normalized = normalizeFilePath(file.path)
    const lines =
      file.content.length === 0 ? 1 : file.content.split(/\r\n|\r|\n/).length
    lineCounts.set(normalized, lines)
    pathSet.add(normalized)
  }

  const missingFiles: string[] = []
  const shortFiles: string[] = []

  for (const vuln of vulnerabilities) {
    for (const loc of vuln.description) {
      const matchedPath = matchPathFlexibly(loc.file, pathSet)
      const lineCount = matchedPath ? lineCounts.get(matchedPath) : null
      if (!lineCount) {
        missingFiles.push(loc.file)
      } else if (lineCount < loc.line_end) {
        shortFiles.push(`${loc.file} (need ${loc.line_end}, got ${lineCount})`)
      }
    }
  }

  if (missingFiles.length === 0 && shortFiles.length === 0) {
    return null
  }

  const missingSummary = missingFiles.length
    ? `Missing ${missingFiles.length} file(s): ${missingFiles
        .slice(0, 4)
        .join(", ")}${missingFiles.length > 4 ? "…" : ""}.`
    : ""
  const shortSummary = shortFiles.length
    ? `Insufficient lines in ${shortFiles.length} file(s): ${shortFiles
        .slice(0, 3)
        .join(", ")}${shortFiles.length > 3 ? "…" : ""}.`
    : ""

  return [missingSummary, shortSummary].filter(Boolean).join(" ")
}
