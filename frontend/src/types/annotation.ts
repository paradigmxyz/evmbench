import type { Severity } from "./severity"

export interface CodeAnnotation {
  id: string
  lineStart: number
  lineEnd: number
  severity: Severity
}
