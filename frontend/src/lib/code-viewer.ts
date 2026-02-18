import type { CodeAnnotation, Severity } from "@/types"

export type HastNode = { type: string; value?: string; children?: HastNode[] }

const SEVERITY_PRIORITY: Record<Severity, number> = {
  critical: 5,
  high: 4,
  medium: 3,
  low: 2,
  info: 1,
}

export function detectTabSize(code: string): number {
  let minSpaceIndent = Number.POSITIVE_INFINITY
  for (const line of code.split("\n")) {
    if (!line.trim()) continue
    const match = line.match(/^( +)\S/)
    if (match) minSpaceIndent = Math.min(minSpaceIndent, match[1].length)
  }
  return minSpaceIndent === Number.POSITIVE_INFINITY
    ? 4
    : Math.min(minSpaceIndent, 8)
}

export function getIndent(line: string, tabSize: number): number {
  let width = 0
  for (const char of line) {
    if (char === " ") width += 1
    else if (char === "\t") width += tabSize
    else break
  }
  return width
}

export function stripLeadingWhitespace(children: HastNode[]): HastNode[] {
  let stripped = false
  const result: HastNode[] = []

  for (const child of children) {
    if (stripped) {
      result.push(child)
      continue
    }

    if (child.type === "text" && typeof child.value === "string") {
      const trimmed = child.value.replace(/^[\t ]+/, "")
      if (trimmed) {
        result.push({ ...child, value: trimmed })
        stripped = true
      } else if (child.value.length === 0) {
        result.push(child)
      }
    } else if (child.type === "element" && child.children) {
      const strippedChildren = stripLeadingWhitespace(child.children)
      if (strippedChildren.length > 0) {
        result.push({ ...child, children: strippedChildren })
        stripped = true
      }
    } else {
      result.push(child)
      stripped = true
    }
  }

  return result
}

export function buildLineSeverityMap(
  annotations: CodeAnnotation[],
): Map<number, Severity> {
  const map = new Map<number, Severity>()
  for (const ann of annotations) {
    for (let line = ann.lineStart; line <= ann.lineEnd; line++) {
      const existing = map.get(line)
      if (
        !existing ||
        SEVERITY_PRIORITY[ann.severity] > SEVERITY_PRIORITY[existing]
      ) {
        map.set(line, ann.severity)
      }
    }
  }
  return map
}

export function buildFocusedLines(
  annotations: CodeAnnotation[],
  focusedId: string | null | undefined,
): Set<number> {
  const focused = new Set<number>()
  if (!focusedId) return focused
  for (const ann of annotations) {
    if (ann.id === focusedId) {
      for (let line = ann.lineStart; line <= ann.lineEnd; line++) {
        focused.add(line)
      }
    }
  }
  return focused
}

export interface AnnotationStart {
  id: string
  severity: Severity
}

export function buildAnnotationStarts(
  annotations: CodeAnnotation[],
): Map<number, AnnotationStart[]> {
  const map = new Map<number, AnnotationStart[]>()
  for (const ann of annotations) {
    const existing = map.get(ann.lineStart) || []
    existing.push({ id: ann.id, severity: ann.severity })
    map.set(ann.lineStart, existing)
  }
  return map
}
