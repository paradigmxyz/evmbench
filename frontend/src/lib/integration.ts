import { API_BASE } from "@/lib/api"

export interface FrontendConfig {
  auth_enabled: boolean
  key_predefined: boolean
}

export async function fetchFrontendConfig(
  signal?: AbortSignal,
): Promise<FrontendConfig> {
  const response = await fetch(`${API_BASE}/v1/integration/frontend`, {
    signal,
    cache: "no-store",
    credentials: "omit",
  })

  if (!response.ok) {
    throw new Error(`Failed to load frontend config (${response.status})`)
  }

  return response.json()
}
