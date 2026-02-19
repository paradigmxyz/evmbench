"use client"

import {
  Copy01Icon,
  InformationCircleIcon,
  Share08Icon,
} from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { toast } from "sonner"
import { PATH_PREFIX } from "@/lib/api"
import { AppHeader } from "@/components/app-header"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useMediaQuery } from "@/hooks/use-media-query"
import { isJobActive } from "@/lib/job-status"
import type { JobResponse } from "@/lib/jobs"
import { formatDateTime } from "@/lib/time"
import { JobStatusBadge, JobStatusDot } from "./job-status-badge"

interface ResultsHeaderProps {
  jobId: string | null
  job: JobResponse | null
  isLoading: boolean
  error: string | null
  onTogglePublic?: () => void
  isUpdatingPublic?: boolean
  shareError?: string | null
  isAuthEnabled?: boolean
}

function JobDetailsContent({
  jobId,
  job,
  statusError,
}: {
  jobId: string
  job: JobResponse | null
  statusError: string | null
}) {
  return (
    <div className="min-w-0 space-y-3">
      <div className="min-w-0 space-y-0.5">
        <div className="text-sm text-foreground">Job details</div>
        <div className="min-w-0 truncate font-mono text-xs text-muted-foreground">
          {jobId}
        </div>
      </div>
      <div className="grid grid-cols-[80px_1fr] gap-y-1.5 text-xs">
        <span className="text-muted-foreground">Status</span>
        <JobStatusBadge status={job?.status} pulse={isJobActive(job?.status)} />
        {job?.queue_position != null && (
          <>
            <span className="text-muted-foreground">Queue</span>
            <span>{job.queue_position}</span>
          </>
        )}
        <span className="text-muted-foreground">Model</span>
        <span>{job?.model ?? "—"}</span>
        <span className="text-muted-foreground">File</span>
        <span className="truncate">{job?.file_name ?? "—"}</span>
        {job?.created_at && (
          <>
            <span className="text-muted-foreground">Created</span>
            <span className="tabular-nums">
              {formatDateTime(job.created_at)}
            </span>
          </>
        )}
        {job?.finished_at && (
          <>
            <span className="text-muted-foreground">Finished</span>
            <span className="tabular-nums">
              {formatDateTime(job.finished_at)}
            </span>
          </>
        )}
      </div>
      {statusError && (
        <div className="text-destructive text-xs">{statusError}</div>
      )}
    </div>
  )
}

function SharingContent({
  job,
  sharePath,
  isSharePublic,
  isAuthEnabled,
  isUpdatingPublic,
  shareError,
  onTogglePublic,
  onCopyLink,
}: {
  job: JobResponse
  sharePath: string
  isSharePublic: boolean
  isAuthEnabled: boolean
  isUpdatingPublic: boolean
  shareError: string | null
  onTogglePublic: () => void
  onCopyLink: () => void
}) {
  return (
    <div className="space-y-3 text-sm">
      <div className="space-y-0.5">
        <div className="text-sm text-foreground">Sharing</div>
        <p className="text-sm text-muted-foreground">
          Control who can access this run and copy the link.
        </p>
      </div>
      <div className="grid grid-cols-[80px_1fr] items-center gap-y-1.5">
        <span className="text-xs self-center text-muted-foreground">
          Visibility
        </span>
        <div className="flex items-center gap-2 self-center">
          <Select
            value={
              !isAuthEnabled ? "public" : job.public ? "public" : "private"
            }
            onValueChange={(value) => {
              if (!isAuthEnabled) return
              const nextPublic = value === "public"
              if (nextPublic !== job.public) {
                onTogglePublic()
              }
            }}
            disabled={!isAuthEnabled || isUpdatingPublic}
          >
            <SelectTrigger className="h-6 w-[120px] text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="public">Public</SelectItem>
              <SelectItem value="private">Private</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <span className="text-xs self-center text-muted-foreground">Link</span>
        {isSharePublic ? (
          <div className="flex min-w-0 items-center gap-2 self-center">
            <span className="flex-1 truncate font-mono text-xs text-muted-foreground">
              {sharePath}
            </span>
            <button
              type="button"
              onClick={onCopyLink}
              className="ml-auto rounded p-1 text-muted-foreground hover:bg-muted"
              title="Copy link"
            >
              <HugeiconsIcon
                icon={Copy01Icon}
                strokeWidth={2}
                className="size-3.5"
              />
            </button>
          </div>
        ) : (
          <span className="text-sm font-serif text-muted-foreground">
            Make the job public to share this link.
          </span>
        )}
      </div>
      {shareError && (
        <div className="text-destructive text-xs">{shareError}</div>
      )}
    </div>
  )
}

export function ResultsHeader({
  jobId,
  job,
  isLoading,
  error,
  onTogglePublic,
  isUpdatingPublic = false,
  shareError,
  isAuthEnabled = true,
}: ResultsHeaderProps) {
  const isMobile = useMediaQuery("(max-width: 768px)")
  const statusError = error || job?.error || null
  const sharePath = jobId ? `${PATH_PREFIX}/results?job_id=${jobId}` : ""
  const isSharePublic = !isAuthEnabled || Boolean(job?.public)

  const handleCopyLink = () => {
    if (!sharePath) return
    const shareUrl =
      typeof window === "undefined"
        ? sharePath
        : `${window.location.origin}${sharePath}`
    void navigator.clipboard.writeText(shareUrl).then(
      () => toast("Link copied to clipboard!"),
      () => toast("Failed to copy link."),
    )
  }

  const runNameButton = (
    <button
      type="button"
      className="flex translate-y-px items-center gap-1 rounded-md p-1 text-xs hover:bg-muted/50 sm:gap-2 sm:px-2"
    >
      <JobStatusDot status={job?.status} pulse={isJobActive(job?.status)} />
      <span className="max-w-28 truncate text-muted-foreground">
        {job?.file_name?.replace(/\.zip$/, "") ?? "Loading…"}
      </span>
      {isLoading && (
        <span className="animate-spin text-muted-foreground/50">↻</span>
      )}
    </button>
  )

  if (isMobile) {
    return (
      <AppHeader
        right={
          jobId ? (
            <Dialog>
              <DialogTrigger asChild>
                <Button variant="ghost" size="icon-sm" className="relative">
                  <HugeiconsIcon
                    icon={InformationCircleIcon}
                    strokeWidth={2}
                    className="size-4"
                  />
                  <JobStatusDot
                    status={job?.status}
                    pulse={isJobActive(job?.status)}
                    className="absolute -top-0.5 -right-0.5 size-2"
                  />
                  <span className="sr-only">Run details</span>
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader className="sr-only">
                  <DialogTitle className="sr-only">Run details</DialogTitle>
                </DialogHeader>
                <JobDetailsContent
                  jobId={jobId}
                  job={job}
                  statusError={statusError}
                />
                {job && onTogglePublic && (
                  <>
                    <div className="h-px bg-border" />
                    <SharingContent
                      job={job}
                      sharePath={sharePath}
                      isSharePublic={isSharePublic}
                      isAuthEnabled={isAuthEnabled}
                      isUpdatingPublic={isUpdatingPublic}
                      shareError={shareError ?? null}
                      onTogglePublic={onTogglePublic}
                      onCopyLink={handleCopyLink}
                    />
                  </>
                )}
              </DialogContent>
            </Dialog>
          ) : null
        }
      />
    )
  }

  return (
    <AppHeader
      right={
        jobId ? (
          <div className="flex items-center gap-2">
            <Popover>
              <PopoverTrigger asChild>{runNameButton}</PopoverTrigger>
              <PopoverContent align="end" className="w-80">
                <JobDetailsContent
                  jobId={jobId}
                  job={job}
                  statusError={statusError}
                />
              </PopoverContent>
            </Popover>
            {job && onTogglePublic && (
              <Popover>
                <PopoverTrigger asChild>
                  <button
                    type="button"
                    className="rounded-md p-1 text-muted-foreground hover:bg-muted/50 hover:text-foreground"
                    aria-label="Share"
                  >
                    <HugeiconsIcon
                      icon={Share08Icon}
                      strokeWidth={2}
                      className="size-4"
                    />
                  </button>
                </PopoverTrigger>
                <PopoverContent align="end" className="w-80">
                  <SharingContent
                    job={job}
                    sharePath={sharePath}
                    isSharePublic={isSharePublic}
                    isAuthEnabled={isAuthEnabled}
                    isUpdatingPublic={isUpdatingPublic}
                    shareError={shareError ?? null}
                    onTogglePublic={onTogglePublic}
                    onCopyLink={handleCopyLink}
                  />
                </PopoverContent>
              </Popover>
            )}
          </div>
        ) : null
      }
    />
  )
}
