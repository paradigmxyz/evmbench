"use client"

import { getJobStatusStyles } from "@/lib/job-status"
import type { JobStatus } from "@/lib/jobs"
import { cn } from "@/lib/utils"

interface JobStatusDotProps {
  status?: JobStatus | null
  pulse?: boolean
  className?: string
}

export function JobStatusDot({
  status,
  pulse = false,
  className,
}: JobStatusDotProps) {
  const styles = getJobStatusStyles(status)
  const shouldPulse = Boolean(pulse)

  return (
    <span
      className={cn(
        "size-1.5 rounded-full",
        styles.dotClass,
        shouldPulse && "animate-pulse",
        className,
      )}
    />
  )
}

interface JobStatusBadgeProps {
  status?: JobStatus | null
  label?: string
  className?: string
  pulse?: boolean
}

export function JobStatusBadge({
  status,
  label,
  className,
  pulse,
}: JobStatusBadgeProps) {
  const styles = getJobStatusStyles(status)
  const statusLabel = label ?? status ?? "—"

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide [font-variant:small-caps]",
        styles.textClass,
        className,
      )}
    >
      <JobStatusDot status={status} pulse={pulse} />
      {statusLabel}
    </span>
  )
}
