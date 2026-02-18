"use client"

import {
  Cancel01Icon,
  Copy01Icon,
  File01Icon,
  TextWrapIcon,
} from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { Fragment, useLayoutEffect, useRef, useState } from "react"
import { toast } from "sonner"
import { CodeViewer } from "@/components/code-viewer"
import type { FileNode } from "@/components/file-tree"
import {
  Breadcrumb,
  BreadcrumbEllipsis,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { useLocalStorage } from "@/hooks/use-local-storage"
import { cn } from "@/lib/utils"
import type { CodeAnnotation } from "@/types"

interface CodeViewerPanelProps {
  selectedNode: FileNode | null
  onClose: () => void
  annotations?: CodeAnnotation[]
  focusedAnnotationId?: string | null
  scrollToLine?: number | null
  onAnnotationClick?: (annotationId: string) => void
}

export function CodeViewerPanel({
  selectedNode,
  onClose,
  annotations = [],
  focusedAnnotationId,
  scrollToLine,
  onAnnotationClick,
}: CodeViewerPanelProps) {
  const [wordWrap, setWordWrap] = useLocalStorage("evmbench.wordWrap", true)
  const [wordWrapTooltipOpen, setWordWrapTooltipOpen] = useState(false)
  const [copyTooltipOpen, setCopyTooltipOpen] = useState(false)
  const viewportRef = useRef<HTMLDivElement>(null)
  const pendingScrollTop = useRef<number | null>(null)
  const pendingAnchorLine = useRef<number | null>(null)
  const pendingAnchorOffset = useRef<number | null>(null)

  const parts = selectedNode?.path.split("/") || []
  const dirs = parts.slice(0, -1)
  const filename = parts.at(-1)

  const maxVisibleDirs = 2
  const shouldCollapse = dirs.length > maxVisibleDirs
  const visibleDirs = shouldCollapse
    ? [
        { label: dirs[0], key: dirs[0] },
        { label: dirs.at(-1) ?? "", key: dirs.join("/") },
      ]
    : dirs.map((dir, index) => ({
        label: dir,
        key: dirs.slice(0, index + 1).join("/"),
      }))

  const findAnchorElement = () => {
    const viewport = viewportRef.current
    if (!viewport) return null

    const viewportRect = viewport.getBoundingClientRect()
    const targetY = viewportRect.top + viewportRect.height * 0.3
    const lines = viewport.querySelectorAll("[data-line]")

    let closestLine: Element | null = null
    let closestDistance = Number.POSITIVE_INFINITY

    for (const line of lines) {
      const lineRect = line.getBoundingClientRect()
      const lineMiddle = lineRect.top + lineRect.height / 2
      const distance = Math.abs(lineMiddle - targetY)
      if (distance < closestDistance) {
        closestDistance = distance
        closestLine = line
      }
    }

    return closestLine
  }

  useLayoutEffect(() => {
    void wordWrap
    if (!viewportRef.current) return
    requestAnimationFrame(() => {
      const viewport = viewportRef.current
      if (!viewport) return

      if (
        pendingAnchorLine.current !== null &&
        pendingAnchorOffset.current !== null
      ) {
        const anchor = viewport.querySelector(
          `[data-line="${pendingAnchorLine.current}"]`,
        )
        if (anchor) {
          const viewportRect = viewport.getBoundingClientRect()
          const anchorRect = anchor.getBoundingClientRect()
          const nextOffset = anchorRect.top - viewportRect.top
          viewport.scrollTop += nextOffset - pendingAnchorOffset.current
        } else if (pendingScrollTop.current !== null) {
          viewport.scrollTop = pendingScrollTop.current
        }
      } else if (pendingScrollTop.current !== null) {
        viewport.scrollTop = pendingScrollTop.current
      }

      pendingScrollTop.current = null
      pendingAnchorLine.current = null
      pendingAnchorOffset.current = null
    })
  }, [wordWrap])

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {selectedNode && (
        <div className="h-8 flex items-center justify-between gap-2 border-b border-border/50 py-1.5 pl-2 pr-2 sm:pl-4 sm:pr-3">
          <Breadcrumb className="min-w-0 flex-1">
            <BreadcrumbList className="flex-nowrap overflow-hidden">
              {visibleDirs.map((dir, i) => (
                <Fragment key={dir.key}>
                  {i > 0 && <BreadcrumbSeparator />}
                  {shouldCollapse && i === 1 && (
                    <>
                      <BreadcrumbItem>
                        <BreadcrumbEllipsis />
                      </BreadcrumbItem>
                      <BreadcrumbSeparator />
                    </>
                  )}
                  <BreadcrumbItem>
                    <span className="text-muted-foreground">{dir.label}</span>
                  </BreadcrumbItem>
                </Fragment>
              ))}
              {visibleDirs.length > 0 && <BreadcrumbSeparator />}
              <BreadcrumbItem>
                <HugeiconsIcon
                  icon={File01Icon}
                  strokeWidth={2}
                  className="size-3.5 text-muted-foreground"
                />
                <BreadcrumbPage>{filename}</BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>
          <div className="flex items-center">
            <Tooltip
              open={wordWrapTooltipOpen}
              onOpenChange={setWordWrapTooltipOpen}
            >
              <TooltipTrigger
                render={(triggerProps) => (
                  <button
                    {...triggerProps}
                    onPointerDown={(event) => event.preventDefault()}
                    onClick={() => {
                      const viewport = viewportRef.current
                      const anchor = findAnchorElement()
                      if (viewport && anchor instanceof HTMLElement) {
                        const viewportRect = viewport.getBoundingClientRect()
                        const anchorRect = anchor.getBoundingClientRect()
                        pendingAnchorOffset.current =
                          anchorRect.top - viewportRect.top
                        pendingAnchorLine.current = Number(
                          anchor.getAttribute("data-line"),
                        )
                        pendingScrollTop.current = null
                      } else {
                        pendingScrollTop.current = viewport?.scrollTop ?? null
                        pendingAnchorLine.current = null
                        pendingAnchorOffset.current = null
                      }
                      setWordWrap(!wordWrap)
                      setWordWrapTooltipOpen(true)
                    }}
                    className={cn(
                      "rounded p-1 hover:bg-muted",
                      wordWrap ? "bg-muted" : "text-muted-foreground",
                    )}
                    aria-label="Toggle word wrap"
                  >
                    <HugeiconsIcon
                      icon={TextWrapIcon}
                      strokeWidth={2}
                      className="size-3.5"
                    />
                  </button>
                )}
              />
              <TooltipContent side="bottom" sideOffset={6}>
                {wordWrap ? "Disable word wrap" : "Enable word wrap"}
              </TooltipContent>
            </Tooltip>
            <Tooltip open={copyTooltipOpen} onOpenChange={setCopyTooltipOpen}>
              <TooltipTrigger
                render={(triggerProps) => (
                  <button
                    {...triggerProps}
                    onPointerDown={(event) => event.preventDefault()}
                    onClick={() => {
                      navigator.clipboard
                        .writeText(selectedNode.content || "")
                        .then(
                          () => toast("Copied to clipboard!"),
                          () => toast("Failed to copy."),
                        )
                      setCopyTooltipOpen(true)
                    }}
                    className="rounded p-1 text-muted-foreground hover:bg-muted"
                    aria-label="Copy file contents"
                  >
                    <HugeiconsIcon
                      icon={Copy01Icon}
                      strokeWidth={2}
                      className="size-3.5"
                    />
                  </button>
                )}
              />
              <TooltipContent side="bottom" sideOffset={6}>
                Copy
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger
                render={(triggerProps) => (
                  <button
                    {...triggerProps}
                    onClick={(event) => {
                      triggerProps.onClick?.(event)
                      onClose()
                    }}
                    className="rounded p-1 text-muted-foreground hover:bg-muted"
                    aria-label="Close"
                  >
                    <HugeiconsIcon
                      icon={Cancel01Icon}
                      strokeWidth={2}
                      className="size-3.5"
                    />
                  </button>
                )}
              />
              <TooltipContent side="bottom" sideOffset={6}>
                Close
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
      )}
      <ScrollArea
        className="flex-1"
        orientation="both"
        fadeOffsets={{ left: -100 }}
        viewportRef={viewportRef}
      >
        {selectedNode ? (
          <CodeViewer
            code={selectedNode.content || ""}
            path={selectedNode.path}
            annotations={annotations}
            focusedAnnotationId={focusedAnnotationId}
            scrollToLine={scrollToLine}
            wordWrap={wordWrap}
            onAnnotationClick={onAnnotationClick}
          />
        ) : (
          <div className="flex h-full items-center justify-center p-8">
            <p className="text-base text-muted-foreground">
              Select a finding to view code
            </p>
          </div>
        )}
        <ScrollBar orientation="horizontal" />
      </ScrollArea>
    </div>
  )
}
