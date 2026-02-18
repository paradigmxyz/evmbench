import { useEffect, useMemo, useState } from "react"
import { codeToHtml, type ShikiTransformer } from "shiki"
import {
  buildAnnotationStarts,
  buildFocusedLines,
  buildLineSeverityMap,
  detectTabSize,
  getIndent,
  type HastNode,
  stripLeadingWhitespace,
} from "@/lib/code-viewer"
import { getLanguageFromPath, SHIKI_THEMES } from "@/lib/shiki"
import type { CodeAnnotation } from "@/types"

interface UseCodeHtmlParams {
  code: string
  path: string
  annotations: CodeAnnotation[]
  focusedAnnotationId?: string | null
}

export function useCodeHtml({
  code,
  path,
  annotations,
  focusedAnnotationId,
}: UseCodeHtmlParams) {
  const [html, setHtml] = useState("")
  const [tabSize, setTabSize] = useState(4)

  const lineSeverityMap = useMemo(
    () => buildLineSeverityMap(annotations),
    [annotations],
  )
  const focusedLines = useMemo(
    () => buildFocusedLines(annotations, focusedAnnotationId),
    [annotations, focusedAnnotationId],
  )
  const annotationStarts = useMemo(
    () => buildAnnotationStarts(annotations),
    [annotations],
  )

  const lineCount = useMemo(() => code.split("\n").length, [code])

  useEffect(() => {
    let cancelled = false
    const detected = detectTabSize(code)
    setTabSize(detected)
    const lines = code.split("\n")
    const indents = lines.map((line) => getIndent(line, detected))

    const lineTransformer: ShikiTransformer = {
      name: "line-numbers",
      line(node, lineNum) {
        const indent = indents[lineNum - 1] || 0
        node.properties["data-line"] = lineNum

        const severity = lineSeverityMap.get(lineNum)
        if (severity) {
          node.properties["data-severity"] = severity
        }

        if (focusedLines.has(lineNum)) {
          node.properties["data-focused"] = ""
        }

        const strippedChildren = stripLeadingWhitespace(
          node.children as unknown as HastNode[],
        ) as typeof node.children

        const starts = annotationStarts.get(lineNum) || []
        const hasContent = strippedChildren.length > 0
        const badgeElements = starts.map((start) => ({
          type: "element" as const,
          tagName: "span",
          properties: {
            class: hasContent
              ? "annotation-badge has-sibling"
              : "annotation-badge",
            "data-severity": start.severity,
            "data-annotation-id": start.id,
          },
          children: [{ type: "text" as const, value: start.id }],
        }))

        node.children = [
          {
            type: "element",
            tagName: "span",
            properties: { class: "line-number" },
            children: [{ type: "text", value: String(lineNum) }],
          },
          {
            type: "element",
            tagName: "span",
            properties: {
              class: "line-content",
              style: `padding-left:${indent}ch`,
            },
            children: [
              ...(strippedChildren.length > 0 ? strippedChildren : []),
              ...badgeElements,
            ],
          },
        ]
      },
    }

    codeToHtml(code, {
      lang: getLanguageFromPath(path),
      themes: SHIKI_THEMES,
      defaultColor: false,
      transformers: [lineTransformer],
    })
      .then((result) => !cancelled && setHtml(result))
      .catch(() => !cancelled && setHtml(""))

    return () => {
      cancelled = true
    }
  }, [code, path, lineSeverityMap, focusedLines, annotationStarts])

  return { html, tabSize, lineCount }
}
