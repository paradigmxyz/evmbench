"use client"

import { useCallback, useMemo, useRef } from "react"
import { useCodeHtml } from "@/hooks/use-code-html"
import { useScrollIntoView } from "@/hooks/use-scroll-into-view"
import { cn } from "@/lib/utils"
import type { CodeAnnotation } from "@/types"

interface CodeViewerProps {
  code: string
  path: string
  annotations?: CodeAnnotation[]
  focusedAnnotationId?: string | null
  scrollToLine?: number | null
  wordWrap?: boolean
  onAnnotationClick?: (annotationId: string) => void
}

export function CodeViewer({
  code,
  path,
  annotations = [],
  focusedAnnotationId,
  scrollToLine,
  wordWrap = false,
  onAnnotationClick,
}: CodeViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const { html, tabSize, lineCount } = useCodeHtml({
    code,
    path,
    annotations,
    focusedAnnotationId,
  })

  const hasFocus = focusedAnnotationId != null
  const scrollSelector =
    scrollToLine == null ? null : `[data-line="${scrollToLine}"]`
  useScrollIntoView(
    containerRef,
    scrollSelector,
    { behavior: "smooth", block: "start" },
    [html],
    0.2,
  )

  const gutterWidth = useMemo(
    () => `${String(lineCount).length}ch`,
    [lineCount],
  )

  const handleAnnotationActivate = useCallback(
    (target: EventTarget | null) => {
      if (!onAnnotationClick || !(target instanceof HTMLElement)) return
      const badge = target.closest(".annotation-badge")
      if (!badge) return
      const annotationId = badge.getAttribute("data-annotation-id")
      if (annotationId) {
        onAnnotationClick(annotationId)
      }
    },
    [onAnnotationClick],
  )

  const handleClick = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      handleAnnotationActivate(event.target)
    },
    [handleAnnotationActivate],
  )

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLDivElement>) => {
      if (event.key !== "Enter" && event.key !== " ") return
      handleAnnotationActivate(event.target)
    },
    [handleAnnotationActivate],
  )

  if (!html) {
    return (
      <pre className="p-4 font-mono text-sm text-muted-foreground whitespace-pre-wrap">
        {code}
      </pre>
    )
  }

  return (
    <section
      ref={containerRef}
      data-has-focus={hasFocus ? "" : undefined}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      aria-label="Code viewer"
      style={
        {
          "--gutter": `calc(${gutterWidth} + 1.5rem)`,
          tabSize,
        } as React.CSSProperties
      }
      className={cn(
        "code-viewer py-4 pl-4 text-sm",
        "[&_pre]:bg-transparent! [&_pre]:pr-4",
        "[&_code]:flex [&_code]:flex-col [&_code]:font-mono",
        "[&_.line]:grid [&_.line]:grid-cols-[var(--gutter)_1fr] [&_.line]:-mr-4 [&_.line]:pr-4",
        "[&_.line-number]:text-right [&_.line-number]:pr-4 [&_.line-number]:text-muted-foreground/50! [&_.line-number]:select-none",
        "[&_.line-number]:sticky [&_.line-number]:left-0 [&_.line-number]:z-10 [&_.line-number]:-ml-4 [&_.line-number]:pl-4",
        "[&_.line-number]:bg-linear-to-r [&_.line-number]:from-background [&_.line-number]:from-80% [&_.line-number]:to-transparent",
        "**:data-[severity=critical]:bg-severity-critical",
        "**:data-[severity=high]:bg-severity-high",
        "**:data-[severity=medium]:bg-severity-medium",
        "**:data-[severity=low]:bg-severity-low",
        "**:data-[severity=info]:bg-severity-info",
        "[&_[data-severity=critical]_.line-number]:border-l-4 [&_[data-severity=critical]_.line-number]:border-l-severity-critical-foreground",
        "[&_[data-severity=high]_.line-number]:border-l-4 [&_[data-severity=high]_.line-number]:border-l-severity-high-foreground",
        "[&_[data-severity=medium]_.line-number]:border-l-4 [&_[data-severity=medium]_.line-number]:border-l-severity-medium-foreground",
        "[&_[data-severity=low]_.line-number]:border-l-4 [&_[data-severity=low]_.line-number]:border-l-severity-low-foreground",
        "[&_[data-severity=info]_.line-number]:border-l-4 [&_[data-severity=info]_.line-number]:border-l-severity-info-foreground",
        "[&_[data-severity=critical]_.line-number]:from-severity-critical",
        "[&_[data-severity=high]_.line-number]:from-severity-high",
        "[&_[data-severity=medium]_.line-number]:from-severity-medium",
        "[&_[data-severity=low]_.line-number]:from-severity-low",
        "[&_[data-severity=info]_.line-number]:from-severity-info",
        "[&_.annotation-badge]:inline-block [&_.annotation-badge]:px-1.5 [&_.annotation-badge]:py-0.5 [&_.annotation-badge]:font-mono!",
        "[&_.annotation-badge]:rounded [&_.annotation-badge]:text-[10px] [&_.annotation-badge]:tabular-nums [&_.annotation-badge]:leading-none [&_.annotation-badge]:border",
        "[&_.annotation-badge]:align-middle [&_.annotation-badge]:-translate-y-px [&_.annotation-badge]:cursor-pointer [&_.annotation-badge]:hover:opacity-80",
        "[&_.annotation-badge.has-sibling]:ml-2",
        "[&_.annotation-badge[data-severity=critical]]:bg-severity-critical [&_.annotation-badge[data-severity=critical]]:text-severity-critical-foreground [&_.annotation-badge[data-severity=critical]]:border-severity-critical-foreground/25",
        "[&_.annotation-badge[data-severity=high]]:bg-severity-high [&_.annotation-badge[data-severity=high]]:text-severity-high-foreground [&_.annotation-badge[data-severity=high]]:border-severity-high-foreground/25",
        "[&_.annotation-badge[data-severity=medium]]:bg-severity-medium [&_.annotation-badge[data-severity=medium]]:text-severity-medium-foreground [&_.annotation-badge[data-severity=medium]]:border-severity-medium-foreground/25",
        "[&_.annotation-badge[data-severity=low]]:bg-severity-low [&_.annotation-badge[data-severity=low]]:text-severity-low-foreground [&_.annotation-badge[data-severity=low]]:border-severity-low-foreground/25",
        "[&_.annotation-badge[data-severity=info]]:bg-severity-info [&_.annotation-badge[data-severity=info]]:text-severity-info-foreground [&_.annotation-badge[data-severity=info]]:border-severity-info-foreground/25",
        "[&[data-has-focus]_.line:not([data-focused])]:opacity-50",
        "[&_.line]:transition-opacity",
        wordWrap
          ? "[&_.line-content]:whitespace-pre-wrap [&_.line-content]:wrap-anywhere"
          : "[&_pre]:w-max [&_pre]:min-w-full",
      )}
      // biome-ignore lint/security/noDangerouslySetInnerHtml: shiki output is trusted
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}
