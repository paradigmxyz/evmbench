import type { JobStatus } from "@/lib/jobs"

type JobStatusStyles = {
  dotClass: string
  textClass: string
}

const STATUS_STYLES: Record<JobStatus, JobStatusStyles> = {
  queued: { dotClass: "bg-status-pending", textClass: "text-status-pending" },
  running: { dotClass: "bg-status-running", textClass: "text-status-running" },
  succeeded: {
    dotClass: "bg-status-success",
    textClass: "text-status-success",
  },
  failed: { dotClass: "bg-status-error", textClass: "text-status-error" },
}

const FALLBACK_STYLES: JobStatusStyles = {
  dotClass: "bg-muted-foreground/50",
  textClass: "text-muted-foreground",
}

export function getJobStatusStyles(status?: JobStatus | null): JobStatusStyles {
  if (!status) return FALLBACK_STYLES
  return STATUS_STYLES[status]
}

export function isJobActive(status?: JobStatus | null): boolean {
  return status === "queued" || status === "running"
}

export function isJobComplete(status?: JobStatus | null): boolean {
  return status === "succeeded" || status === "failed"
}
