import { API_BASE } from "@/lib/api"

export interface FrontendModelOption {
  key: string
  label: string
}

export const DEFAULT_MODEL_OPTIONS: FrontendModelOption[] = [
  { key: "codex-gpt-5.5", label: "codex-gpt-5.5" },
  { key: "codex-gpt-5.4", label: "codex-gpt-5.4" },
  { key: "codex-gpt-5.4-mini", label: "codex-gpt-5.4-mini" },
  { key: "codex-gpt-5.2", label: "codex-gpt-5.2 (legacy)" },
  {
    key: "codex-gpt-5.1-codex-max",
    label: "codex-gpt-5.1-codex-max (legacy)",
  },
]

export const DEFAULT_MODEL_KEY =
  DEFAULT_MODEL_OPTIONS[0]?.key ?? "codex-gpt-5.5"

export interface FrontendConfig {
  auth_enabled: boolean
  key_predefined: boolean
  default_model: string
  models: FrontendModelOption[]
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
