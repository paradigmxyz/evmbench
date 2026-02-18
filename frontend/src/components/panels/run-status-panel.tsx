"use client"

import { useMemo } from "react"
import { JobStatusBadge } from "@/components/results"
import { useNow } from "@/hooks/use-now"
import { isJobActive } from "@/lib/job-status"
import type { JobResponse } from "@/lib/jobs"
import { formatDateTime, formatElapsed } from "@/lib/time"

interface RunStatusPanelProps {
  job: JobResponse | null
  isLoading?: boolean
}

export function RunStatusPanel({
  job,
  isLoading = false,
}: RunStatusPanelProps) {
  const now = useNow(1000)

  const startTimestamp = useMemo(() => {
    const value = job?.started_at ?? job?.created_at
    return value ? new Date(value).getTime() : null
  }, [job?.created_at, job?.started_at])

  const elapsedLabel = startTimestamp
    ? formatElapsed(now - startTimestamp)
    : "--:--"

  const statusLabel = job?.status ?? "queued"
  const isActive = isJobActive(job?.status)

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex flex-1 flex-col items-center justify-center p-8">
        <div className="w-full max-w-md space-y-3">
          <div className="space-y-1">
            <h3 className="text-base text-foreground">Running analysis</h3>
            <p className="text-base text-muted-foreground">
              We are analyzing the uploaded repository. Results will appear as
              soon as the run completes.
            </p>
          </div>

          <div className="grid grid-cols-[80px_1fr] gap-y-1.5 text-xs sm:grid-cols-[90px_1fr]">
            <span className="text-muted-foreground">Status</span>
            <div className="flex items-center gap-2 text-foreground">
              <JobStatusBadge
                status={job?.status}
                label={statusLabel}
                pulse={isActive}
              />
              {isLoading && (
                <span className="text-muted-foreground/50 animate-spin">↻</span>
              )}
            </div>
            {job?.queue_position != null && (
              <>
                <span className="text-muted-foreground">Queue position</span>
                <span className="text-foreground tabular-nums">
                  {job.queue_position}
                </span>
              </>
            )}
            <span className="text-muted-foreground">Elapsed</span>
            <span className="text-foreground tabular-nums">{elapsedLabel}</span>
            <span className="text-muted-foreground">Model</span>
            <span className="text-foreground">{job?.model ?? "—"}</span>
            <span className="text-muted-foreground">File</span>
            <span className="text-foreground truncate">
              {job?.file_name ?? "—"}
            </span>
            {job?.created_at && (
              <>
                <span className="text-muted-foreground">Created</span>
                <span className="text-foreground tabular-nums">
                  {formatDateTime(job.created_at)}
                </span>
              </>
            )}
            {job?.started_at && (
              <>
                <span className="text-muted-foreground">Started</span>
                <span className="text-foreground tabular-nums">
                  {formatDateTime(job.started_at)}
                </span>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
