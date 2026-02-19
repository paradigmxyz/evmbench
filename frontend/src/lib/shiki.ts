import { bundledLanguages } from "shiki"

const LANGUAGE_OVERRIDES: Record<string, string> = {
  h: "c",
  hpp: "cpp",
  rs: "rust",
  dockerfile: "docker",
  makefile: "make",
}

export function resolveShikiLanguage(lang: string): string {
  const normalized = lang.toLowerCase()
  const override = LANGUAGE_OVERRIDES[normalized]
  if (override && override in bundledLanguages) return override
  if (lang in bundledLanguages) return lang
  if (normalized in bundledLanguages) return normalized
  return "text"
}

export function getLanguageFromPath(path: string): string {
  const name = path.split("/").pop() || ""
  const nameLower = name.toLowerCase()
  const nameOverride = LANGUAGE_OVERRIDES[nameLower]
  if (nameOverride) return resolveShikiLanguage(nameOverride)
  const ext = nameLower.split(".").pop() || ""
  const extOverride = LANGUAGE_OVERRIDES[ext] || ext
  return resolveShikiLanguage(extOverride)
}

export const SHIKI_THEMES = {
  light: "github-light-default",
  dark: "github-dark-default",
} as const
