import { API_BASE } from "@/lib/api"

export interface AuthUser {
  username: string
  avatar_url: string | null
}

export async function fetchMe(signal?: AbortSignal): Promise<AuthUser | null> {
  const response = await fetch(`${API_BASE}/v1/auth/me`, {
    signal,
    cache: "no-store",
    credentials: "include",
  })

  if (response.status === 401) {
    return null
  }

  if (!response.ok) {
    throw new Error(`Failed to load session (${response.status})`)
  }

  return response.json()
}
