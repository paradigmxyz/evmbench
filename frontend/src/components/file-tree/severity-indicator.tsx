import { type SeverityCounts, totalSeverityCount } from "@/lib/severity"
import { cn } from "@/lib/utils"
import { SEVERITIES, SEVERITY_CONFIG } from "@/types"

interface SeverityIndicatorProps {
  counts: SeverityCounts
}

export function FolderSeverityIndicator({ counts }: SeverityIndicatorProps) {
  const total = totalSeverityCount(counts)
  if (total === 0) return null

  return (
    <span className="ml-auto flex shrink-0 items-center gap-1">
      {SEVERITIES.map((severity) => {
        if (counts[severity] === 0) return null
        const { bgForeground } = SEVERITY_CONFIG[severity]
        return (
          <span
            key={severity}
            className={cn("size-2 rounded-full opacity-50", bgForeground)}
          />
        )
      })}
    </span>
  )
}

export function FileSeverityIndicator({ counts }: SeverityIndicatorProps) {
  const total = totalSeverityCount(counts)
  if (total === 0) return null

  return (
    <span className="ml-auto flex shrink-0 items-center gap-1 text-xs font-medium">
      {SEVERITIES.map((severity) => {
        const count = counts[severity]
        if (count === 0) return null
        const { text, label } = SEVERITY_CONFIG[severity]
        return (
          <span key={severity} className={cn("tabular-nums", text)}>
            {count}
            {label}
          </span>
        )
      })}
    </span>
  )
}
