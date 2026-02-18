export type Severity = "critical" | "high" | "medium" | "low" | "info"

export const SEVERITIES = ["critical", "high", "medium", "low", "info"] as const

export const SEVERITY_RANK = Object.fromEntries(
  SEVERITIES.map((severity, index) => [severity, index]),
) as Record<Severity, number>

export interface SeverityConfig {
  bg: string
  bgForeground: string
  text: string
  border: string
  label: string
}

export const SEVERITY_CONFIG: Record<Severity, SeverityConfig> = {
  critical: {
    bg: "bg-severity-critical",
    bgForeground: "bg-severity-critical-foreground",
    text: "text-severity-critical-foreground",
    border: "border-severity-critical-foreground",
    label: "C",
  },
  high: {
    bg: "bg-severity-high",
    bgForeground: "bg-severity-high-foreground",
    text: "text-severity-high-foreground",
    border: "border-severity-high-foreground",
    label: "H",
  },
  medium: {
    bg: "bg-severity-medium",
    bgForeground: "bg-severity-medium-foreground",
    text: "text-severity-medium-foreground",
    border: "border-severity-medium-foreground",
    label: "M",
  },
  low: {
    bg: "bg-severity-low",
    bgForeground: "bg-severity-low-foreground",
    text: "text-severity-low-foreground",
    border: "border-severity-low-foreground",
    label: "L",
  },
  info: {
    bg: "bg-severity-info",
    bgForeground: "bg-severity-info-foreground",
    text: "text-severity-info-foreground",
    border: "border-severity-info-foreground",
    label: "I",
  },
}
