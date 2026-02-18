import { type CodeAnnotation, SEVERITY_RANK, type Vulnerability } from "@/types"
import { matchPathFlexibly, normalizeFilePath } from "./paths"

export function findVulnerabilityById(
  vulnerabilities: Vulnerability[],
  id: string,
): Vulnerability | undefined {
  return vulnerabilities.find((vuln) => vuln.id === id)
}

export function buildCodeAnnotationsForFile(
  filePath: string | null,
  vulnerabilities: Vulnerability[],
): CodeAnnotation[] {
  if (!filePath) return []
  const normalizedSelectedFile = normalizeFilePath(filePath)
  const filePathSet = new Set([normalizedSelectedFile])
  const annotations: CodeAnnotation[] = []

  for (const vuln of vulnerabilities) {
    for (const loc of vuln.description) {
      const matched = matchPathFlexibly(loc.file, filePathSet)
      if (matched) {
        annotations.push({
          id: vuln.id,
          lineStart: loc.line_start,
          lineEnd: loc.line_end,
          severity: vuln.severity,
        })
      }
    }
  }

  return annotations
}

export function sortVulnerabilitiesBySeverity(
  vulnerabilities: Vulnerability[],
): Vulnerability[] {
  return [...vulnerabilities].sort(
    (a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity],
  )
}
