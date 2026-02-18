"use client"

import Link from "next/link"
import { useEffect, useState } from "react"
import { AppFooter } from "@/components/app-footer"
import { AppHeader } from "@/components/app-header"
import { JobStatusBadge } from "@/components/results/job-status-badge"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/hooks/use-auth"
import { fetchJobHistory, type JobHistoryItem } from "@/lib/jobs"
import { formatDateTime } from "@/lib/time"

export default function HistoryPage() {
  const { isAuthorized, isLoading: isAuthLoading, isAuthEnabled } = useAuth()
  const [history, setHistory] = useState<JobHistoryItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isAuthLoading) return
    if (!isAuthEnabled || !isAuthorized) {
      setIsLoading(false)
      return
    }

    const controller = new AbortController()
    fetchJobHistory(controller.signal)
      .then(setHistory)
      .catch((err) => {
        if (err.name !== "AbortError") {
          setError(err.message)
        }
      })
      .finally(() => setIsLoading(false))

    return () => controller.abort()
  }, [isAuthLoading, isAuthorized, isAuthEnabled])

  return (
    <main className="flex min-h-screen w-screen flex-col">
      <AppHeader />
      <section className="flex flex-1 justify-center px-6 py-10">
        <div className="w-full max-w-3xl space-y-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-1">
              <h1 className="text-base text-foreground">Job history</h1>
              <p className="text-base text-muted-foreground">
                Review past analyses and jump back into results.
              </p>
            </div>
            <Button
              asChild
              variant="outline"
              size="sm"
              className="self-start sm:self-auto"
            >
              <Link href="/">Start a new run</Link>
            </Button>
          </div>

          {!isAuthEnabled && (
            <p className="text-base text-muted-foreground">
              Job history is not available when authentication is disabled.
            </p>
          )}

          {isAuthEnabled && !isAuthorized && !isAuthLoading && (
            <p className="text-base text-muted-foreground">
              Please authorize to view your job history.
            </p>
          )}

          {isLoading && (
            <p className="text-base text-muted-foreground">Loading...</p>
          )}

          {error && <p className="text-sm text-destructive">{error}</p>}

          {!isLoading && !error && isAuthorized && history.length === 0 && (
            <p className="text-base text-muted-foreground">
              No jobs found. Start an analysis to see your history.
            </p>
          )}

          {!isLoading && !error && history.length > 0 && (
            <div className="text-sm -mx-3">
              {/* Desktop: grid layout */}
              <div className="hidden grid-cols-[minmax(0,1fr)_160px_120px_110px] gap-x-6 gap-y-2 px-3 pb-2 text-xs text-muted-foreground md:grid">
                <span>File</span>
                <span>Created</span>
                <span>Status</span>
                <span>Visibility</span>
              </div>
              <div className="space-y-1">
                {history.map((job) => (
                  <Link
                    key={job.job_id}
                    href={`/results?job_id=${job.job_id}`}
                    className="flex flex-col gap-1 rounded-md px-3 py-2 hover:bg-muted/40 hover:text-foreground md:grid md:grid-cols-[minmax(0,1fr)_160px_120px_110px] md:items-center md:gap-x-6 md:gap-y-2 md:py-1"
                  >
                    <span className="truncate font-medium md:font-normal">
                      {job.file_name}
                    </span>
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 md:contents">
                      <span className="text-xs text-muted-foreground">
                        {formatDateTime(job.created_at)}
                      </span>
                      <JobStatusBadge status={job.status} />
                      <span className="text-xs text-muted-foreground">
                        {job.public == null
                          ? "—"
                          : job.public
                            ? "Public"
                            : "Private"}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>
      <AppFooter />
    </main>
  )
}
