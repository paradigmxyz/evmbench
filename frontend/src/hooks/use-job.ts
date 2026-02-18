import { useCallback, useEffect, useMemo, useState } from "react"
import { isJobActive, isJobComplete } from "@/lib/job-status"
import type { JobResponse } from "@/lib/jobs"
import { fetchJob } from "@/lib/jobs"

interface UseJobOptions {
  pollIntervalMs?: number
}

export function useJob(jobId: string | null, options: UseJobOptions = {}) {
  const pollIntervalMs = options.pollIntervalMs ?? 4000
  const [job, setJob] = useState<JobResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const loadJob = useCallback(async () => {
    if (!jobId) return
    setIsLoading(true)
    try {
      const data = await fetchJob(jobId)
      setJob(data)
      setError(null)
    } catch (err) {
      setJob(null)
      setError(err instanceof Error ? err.message : "Failed to load job")
    } finally {
      setIsLoading(false)
    }
  }, [jobId])

  useEffect(() => {
    if (!jobId) {
      setJob(null)
      setError(null)
      setIsLoading(false)
      return
    }
    void loadJob()
  }, [jobId, loadJob])

  useEffect(() => {
    if (!jobId || !isJobActive(job?.status)) return
    const interval = window.setInterval(() => {
      void loadJob()
    }, pollIntervalMs)
    return () => window.clearInterval(interval)
  }, [jobId, job?.status, loadJob, pollIntervalMs])

  const isActive = useMemo(() => isJobActive(job?.status), [job?.status])
  const isComplete = useMemo(() => isJobComplete(job?.status), [job?.status])
  const shouldShowRunStatus = Boolean(jobId) && (isActive || isLoading || !job)

  return {
    job,
    error,
    isLoading,
    reload: loadJob,
    setJob,
    isActive,
    isComplete,
    shouldShowRunStatus,
  }
}
