import { useEffect, useState } from "react"
import { type AuthUser, fetchMe } from "@/lib/auth"
import { type FrontendConfig, fetchFrontendConfig } from "@/lib/integration"

const FRONTEND_CONFIG_TTL_MS = 10000
const DEFAULT_FRONTEND_CONFIG: FrontendConfig = {
  // OSS-friendly default: if the backend config can't be fetched, don't gate usage on auth.
  auth_enabled: false,
  key_predefined: false,
}
let frontendConfigCache: { value: FrontendConfig; timestamp: number } | null =
  null
let frontendConfigInFlight: Promise<FrontendConfig> | null = null
let authUserCache: { value: AuthUser | null; timestamp: number } | null = null
let authUserInFlight: Promise<AuthUser | null> | null = null

async function getFrontendConfig(): Promise<FrontendConfig> {
  const now = Date.now()
  if (
    frontendConfigCache &&
    now - frontendConfigCache.timestamp < FRONTEND_CONFIG_TTL_MS
  ) {
    return frontendConfigCache.value
  }
  if (frontendConfigInFlight) {
    return frontendConfigInFlight
  }

  frontendConfigInFlight = fetchFrontendConfig()
    .then((config) => {
      frontendConfigCache = { value: config, timestamp: Date.now() }
      return config
    })
    .catch(() => {
      return frontendConfigCache
        ? frontendConfigCache.value
        : DEFAULT_FRONTEND_CONFIG
    })
    .finally(() => {
      frontendConfigInFlight = null
    })

  return frontendConfigInFlight
}

async function getAuthUser(): Promise<AuthUser | null> {
  const now = Date.now()
  if (authUserCache && now - authUserCache.timestamp < FRONTEND_CONFIG_TTL_MS) {
    return authUserCache.value
  }
  if (authUserInFlight) {
    return authUserInFlight
  }

  authUserInFlight = fetchMe()
    .then((user) => {
      authUserCache = { value: user, timestamp: Date.now() }
      return user
    })
    .catch(() => {
      return authUserCache ? authUserCache.value : null
    })
    .finally(() => {
      authUserInFlight = null
    })

  return authUserInFlight
}

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(
    authUserCache ? authUserCache.value : null,
  )
  const [isLoading, setIsLoading] = useState(
    !(authUserCache || frontendConfigCache),
  )
  const [isConfigLoading, setIsConfigLoading] = useState(!frontendConfigCache)
  const [isAuthEnabled, setIsAuthEnabled] = useState(
    frontendConfigCache
      ? frontendConfigCache.value.auth_enabled
      : DEFAULT_FRONTEND_CONFIG.auth_enabled,
  )
  const [keyPredefined, setKeyPredefined] = useState(
    frontendConfigCache
      ? frontendConfigCache.value.key_predefined
      : DEFAULT_FRONTEND_CONFIG.key_predefined,
  )

  useEffect(() => {
    let isMounted = true

    const loadUser = async () => {
      try {
        const config = await getFrontendConfig()
        if (isMounted) {
          setIsAuthEnabled(config.auth_enabled)
          setKeyPredefined(config.key_predefined)
          setIsConfigLoading(false)
        }

        if (!config.auth_enabled) {
          if (isMounted) {
            authUserCache = null
            setUser(null)
            setIsLoading(false)
          }
          return
        }

        const result = await getAuthUser()
        if (isMounted) {
          setUser(result)
        }
      } catch {
        if (isMounted) {
          setUser(null)
          setIsConfigLoading(false)
        }
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    void loadUser()

    return () => {
      isMounted = false
    }
  }, [])

  return {
    user,
    isLoading,
    isConfigLoading,
    isAuthEnabled,
    keyPredefined,
    isAuthorized: !isAuthEnabled || Boolean(user),
  }
}
