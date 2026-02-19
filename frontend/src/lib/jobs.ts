import { API_BASE } from "@/lib/api"
import { normalizeFilePath } from "@/lib/paths"
import type { Severity, Vulnerability } from "@/types"

export type JobStatus = "queued" | "running" | "succeeded" | "failed"

export interface StartJobResponse {
  job_id: string
  status: JobStatus
}

export interface JobResponse {
  job_id: string
  status: JobStatus
  result: JobReport | null
  error: string | null
  model: string
  file_name: string
  public: boolean
  queue_position: number | null
  created_at: string
  started_at: string | null
  finished_at: string | null
}

export interface JobReport {
  vulnerabilities: JobVulnerability[]
}

export interface JobHistoryItem {
  job_id: string
  status: JobStatus
  file_name: string
  public?: boolean
  created_at: string
  finished_at: string | null
}

export interface JobVulnerability {
  id?: string
  title: string
  severity: string
  summary: string
  description: {
    file: string
    line_start: number
    line_end: number
    desc: string
  }[]
  impact: string
  proof_of_concept: string
  remediation: string
}

export async function fetchJob(
  jobId: string,
  signal?: AbortSignal,
): Promise<JobResponse> {
  const response = await fetch(`${API_BASE}/v1/jobs/${jobId}`, {
    signal,
    cache: "no-store",
    credentials: "include",
  })

  if (!response.ok) {
    const message = await readApiError(response)
    throw new Error(message ?? `Failed to fetch job (${response.status})`)
  }

  return response.json()
}

export async function setJobPublic(
  jobId: string,
  isPublic: boolean,
): Promise<JobResponse> {
  const response = await fetch(`${API_BASE}/v1/jobs/${jobId}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ public: isPublic }),
    credentials: "include",
  })

  if (!response.ok) {
    const message = await readApiError(response)
    throw new Error(message ?? `Failed to update job (${response.status})`)
  }

  return response.json()
}

export async function startJob(
  file: File,
  model: string,
  apiKey: string,
  provider: string = "openai",
): Promise<StartJobResponse> {
  const body = new FormData()
  body.append("file", file)
  body.append("model", model)
  body.append("openai_key", apiKey)
  body.append("provider", provider)

  const response = await fetch(`${API_BASE}/v1/jobs/start`, {
    method: "POST",
    body,
    credentials: "include",
  })

  if (!response.ok) {
    const message = await readApiError(response)
    throw new Error(message ?? `Failed to start job (${response.status})`)
  }

  return response.json()
}

export async function fetchJobHistory(
  signal?: AbortSignal,
): Promise<JobHistoryItem[]> {
  const response = await fetch(`${API_BASE}/v1/jobs/history`, {
    signal,
    cache: "no-store",
    credentials: "include",
  })

  if (!response.ok) {
    const message = await readApiError(response)
    throw new Error(
      message ?? `Failed to fetch job history (${response.status})`,
    )
  }

  return response.json()
}

async function readApiError(response: Response): Promise<string | null> {
  try {
    const data = await response.clone().json()
    if (data && typeof data === "object" && "detail" in data) {
      const detail = (data as { detail?: unknown }).detail
      if (typeof detail === "string") {
        return detail
      }
    }
  } catch {
    // ignore
  }

  try {
    const text = await response.text()
    return text.trim() ? text : null
  } catch {
    return null
  }
}

export function mapJobVulnerabilities(
  report: JobReport | null,
): Vulnerability[] {
  if (!report?.vulnerabilities?.length) return []

  return report.vulnerabilities.map((vuln, index) => ({
    id: vuln.id ?? formatVulnerabilityId(index),
    title: vuln.title,
    severity: normalizeSeverity(vuln.severity),
    summary: vuln.summary,
    description: vuln.description.map((item) => ({
      ...item,
      file: stripAuditPrefix(item.file),
    })),
    impact: vuln.impact,
    proof_of_concept: vuln.proof_of_concept,
    remediation: vuln.remediation,
  }))
}

function normalizeSeverity(input: string): Severity {
  const normalized = input.trim().toLowerCase()
  if (
    normalized === "critical" ||
    normalized === "high" ||
    normalized === "medium" ||
    normalized === "low" ||
    normalized === "info"
  ) {
    return normalized
  }
  if (normalized.startsWith("crit")) return "critical"
  if (normalized.startsWith("med")) return "medium"
  if (normalized.startsWith("hi")) return "high"
  if (normalized.startsWith("lo")) return "low"
  return "info"
}

function formatVulnerabilityId(index: number): string {
  return `V-${String(index + 1).padStart(3, "0")}`
}

function stripAuditPrefix(path: string): string {
  const normalized = normalizeFilePath(path)
  return normalized.startsWith("audit/")
    ? normalized.slice("audit/".length)
    : normalized
}
