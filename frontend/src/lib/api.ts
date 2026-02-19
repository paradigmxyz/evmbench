export const API_BASE = (() => {
  // Runtime detection for reverse proxy setups (e.g., /svmbench)
  if (
    typeof window !== "undefined" &&
    window.location.pathname.startsWith("/svmbench")
  ) {
    return "/svmbench/api"
  }
  return process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:1337"
})()
