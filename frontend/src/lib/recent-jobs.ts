export interface RecentJob {
  job_id: string
  label: string
  created_at_ms: number
}

const STORAGE_KEY = "evmbench.recentJobs.v1"
const MAX_RECENT = 20

function safeParseRecentJobs(raw: string | null): RecentJob[] {
  if (!raw) return []
  try {
    const value: unknown = JSON.parse(raw)
    if (!Array.isArray(value)) return []
    const jobs: RecentJob[] = []
    for (const item of value) {
      if (!item || typeof item !== "object") continue
      const obj = item as Record<string, unknown>
      const job_id = obj.job_id
      const label = obj.label
      const created_at_ms = obj.created_at_ms
      if (typeof job_id !== "string" || !job_id) continue
      if (typeof label !== "string" || !label) continue
      if (typeof created_at_ms !== "number" || !Number.isFinite(created_at_ms))
        continue
      jobs.push({ job_id, label, created_at_ms })
    }
    return jobs
  } catch {
    return []
  }
}

export function getRecentJobs(): RecentJob[] {
  if (typeof window === "undefined") return []
  return safeParseRecentJobs(window.localStorage.getItem(STORAGE_KEY))
}

export function setRecentJobs(jobs: RecentJob[]) {
  if (typeof window === "undefined") return
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(jobs))
}

export function addRecentJob(job: RecentJob) {
  const existing = getRecentJobs()
  const next = [job, ...existing.filter((j) => j.job_id !== job.job_id)].slice(
    0,
    MAX_RECENT,
  )
  setRecentJobs(next)
  return next
}
