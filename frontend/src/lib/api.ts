// Runtime detection for reverse proxy setups (e.g., /evmbench)
export const PATH_PREFIX =
  typeof window !== "undefined" &&
  window.location.pathname.startsWith("/evmbench")
    ? "/evmbench"
    : ""

export const API_BASE = PATH_PREFIX
  ? `${PATH_PREFIX}/api`
  : (process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:1337")
