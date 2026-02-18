import type { NextConfig } from "next"

const nextConfig: NextConfig = {
  reactCompiler: true,
  output: "export",
  images: {
    unoptimized: true,
  },
  // Avoid Next.js incorrectly inferring workspace root (e.g. from unrelated lockfiles).
  turbopack: {
    root: import.meta.dirname,
  },
}

export default nextConfig
