import type { Severity } from "@/types"

export interface SeverityCounts {
  critical: number
  high: number
  medium: number
  low: number
  info: number
}

export function emptySeverityCounts(): SeverityCounts {
  return { critical: 0, high: 0, medium: 0, low: 0, info: 0 }
}

export function totalSeverityCount(counts: SeverityCounts): number {
  return (
    counts.critical + counts.high + counts.medium + counts.low + counts.info
  )
}

export function mergeSeverityCounts(
  a: SeverityCounts,
  b: SeverityCounts,
): SeverityCounts {
  return {
    critical: a.critical + b.critical,
    high: a.high + b.high,
    medium: a.medium + b.medium,
    low: a.low + b.low,
    info: a.info + b.info,
  }
}

export function incrementSeverityCount(
  counts: SeverityCounts,
  severity: Severity,
): SeverityCounts {
  return { ...counts, [severity]: counts[severity] + 1 }
}
