"use client"

import {
  AlertDiamondIcon,
  ArrowDown01Icon,
  Cancel01Icon,
  File01Icon,
  SourceCodeIcon,
  TestTube01Icon,
  TextWrapIcon,
  Wrench01Icon,
} from "@hugeicons/core-free-icons"
import { HugeiconsIcon, type IconSvgElement } from "@hugeicons/react"
import { useLayoutEffect, useRef, useState } from "react"
import { CodeViewer } from "@/components/code-viewer"
import type { FileNode } from "@/components/file-tree"
import { InlineMarkdown, Markdown } from "@/components/markdown"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
} from "@/components/ui/sheet"
import { useLocalStorage } from "@/hooks/use-local-storage"
import { truncateFilePath } from "@/lib/paths"
import { cn } from "@/lib/utils"
import { sortVulnerabilitiesBySeverity } from "@/lib/vulnerabilities"
import type { CodeAnnotation } from "@/types"
import { SEVERITY_CONFIG, type Vulnerability } from "@/types"

interface MobileResultsViewProps {
  vulnerabilities: Vulnerability[]
  onSelectVulnerability: (vuln: Vulnerability) => void
  onNavigateToLocation: (file: string, lineStart: number) => void
  selectedNode: FileNode | null
  codeAnnotations: CodeAnnotation[]
  scrollToLine?: number | null
}

function SectionHeader({
  icon,
  children,
}: {
  icon: IconSvgElement
  children: React.ReactNode
}) {
  return (
    <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
      <HugeiconsIcon icon={icon} strokeWidth={2} className="size-3.5" />
      <span>{children}</span>
    </div>
  )
}

function SectionCard({
  icon,
  title,
  children,
}: {
  icon: IconSvgElement
  title: string
  children: React.ReactNode
}) {
  return (
    <section className="border-t border-border/50">
      <div className="flex items-center bg-secondary/30 justify-between border-b border-border/50 px-3 py-1.5">
        <SectionHeader icon={icon}>{title}</SectionHeader>
      </div>
      <div className="px-3 py-3">{children}</div>
    </section>
  )
}

function VulnerabilityCard({
  vulnerability,
  isExpanded,
  onToggle,
  onViewCode,
}: {
  vulnerability: Vulnerability
  isExpanded: boolean
  onToggle: () => void
  onViewCode: (file: string, lineStart: number) => void
}) {
  return (
    <div className="border-b border-border/50">
      <button
        type="button"
        onClick={onToggle}
        className={cn(
          "flex w-full items-start gap-3 px-4 py-2 text-left hover:bg-muted/30",
          isExpanded && "bg-muted/50 hover:bg-muted/60",
        )}
      >
        <HugeiconsIcon
          icon={ArrowDown01Icon}
          strokeWidth={2}
          className={cn(
            "mt-0.5 size-4 shrink-0 text-muted-foreground",
            isExpanded && "rotate-180",
          )}
        />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="shrink-0 tabular-nums text-xs text-muted-foreground">
              {vulnerability.id}
            </span>
            <span
              className={cn(
                "shrink-0 rounded px-1.5 text-xs capitalize",
                SEVERITY_CONFIG[vulnerability.severity].bg,
                SEVERITY_CONFIG[vulnerability.severity].text,
              )}
            >
              {vulnerability.severity}
            </span>
          </div>
          <h3 className="text-foreground">
            <InlineMarkdown>{vulnerability.title}</InlineMarkdown>
          </h3>
        </div>
      </button>

      {isExpanded && (
        <div className="border-t border-border/30 bg-muted/25">
          <div className="px-4 py-3">
            <Markdown className="text-base text-muted-foreground">
              {vulnerability.summary}
            </Markdown>
          </div>

          <SectionCard icon={File01Icon} title="Affected Locations">
            <div className="space-y-2">
              {vulnerability.description.map((loc, i) => (
                <div
                  key={`${loc.file}-${loc.line_start}-${i}`}
                  className="rounded-md border border-border/50 bg-muted/25 p-2"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <HugeiconsIcon
                      icon={File01Icon}
                      strokeWidth={2}
                      className="size-3.5 shrink-0 text-muted-foreground"
                    />
                    <span className="text-xs truncate flex-1" title={loc.file}>
                      {truncateFilePath(loc.file, 2)}
                    </span>
                    <span className="text-xs tabular-nums text-muted-foreground">
                      L{loc.line_start}
                      {loc.line_end !== loc.line_start && `-${loc.line_end}`}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mb-2">
                    <InlineMarkdown>{loc.desc}</InlineMarkdown>
                  </p>
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full"
                    onClick={(e) => {
                      e.stopPropagation()
                      onViewCode(loc.file, loc.line_start)
                    }}
                  >
                    <HugeiconsIcon
                      icon={SourceCodeIcon}
                      strokeWidth={2}
                      className="size-3.5 mr-1.5"
                    />
                    <span className="text-xs">View code</span>
                  </Button>
                </div>
              ))}
            </div>
          </SectionCard>

          <SectionCard icon={AlertDiamondIcon} title="Impact">
            <Markdown className="text-base">{vulnerability.impact}</Markdown>
          </SectionCard>

          <SectionCard icon={TestTube01Icon} title="Proof of Concept">
            <Markdown className="text-base">
              {vulnerability.proof_of_concept}
            </Markdown>
          </SectionCard>

          <SectionCard icon={Wrench01Icon} title="Remediation">
            <Markdown className="text-base">
              {vulnerability.remediation}
            </Markdown>
          </SectionCard>
        </div>
      )}
    </div>
  )
}

export function MobileResultsView({
  vulnerabilities,
  onSelectVulnerability,
  onNavigateToLocation,
  selectedNode,
  codeAnnotations,
  scrollToLine,
}: MobileResultsViewProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const [codeSheetOpen, setCodeSheetOpen] = useState(false)
  const [codeSheetFile, setCodeSheetFile] = useState<string | null>(null)
  const [codeSheetLine, setCodeSheetLine] = useState<number | null>(null)
  const [wordWrap, setWordWrap] = useLocalStorage("evmbench.wordWrap", true)

  const codeViewportRef = useRef<HTMLDivElement>(null)
  const pendingScrollTop = useRef<number | null>(null)
  const pendingAnchorLine = useRef<number | null>(null)
  const pendingAnchorOffset = useRef<number | null>(null)

  const findAnchorElement = () => {
    const viewport = codeViewportRef.current
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
    if (!codeViewportRef.current) return
    requestAnimationFrame(() => {
      const viewport = codeViewportRef.current
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

  const handleWordWrapToggle = () => {
    const viewport = codeViewportRef.current
    const anchor = findAnchorElement()
    if (viewport && anchor instanceof HTMLElement) {
      const viewportRect = viewport.getBoundingClientRect()
      const anchorRect = anchor.getBoundingClientRect()
      pendingAnchorOffset.current = anchorRect.top - viewportRect.top
      pendingAnchorLine.current = Number(anchor.getAttribute("data-line"))
      pendingScrollTop.current = null
    } else {
      pendingScrollTop.current = viewport?.scrollTop ?? null
      pendingAnchorLine.current = null
      pendingAnchorOffset.current = null
    }
    setWordWrap(!wordWrap)
  }

  const sortedVulnerabilities = sortVulnerabilitiesBySeverity(vulnerabilities)

  const handleToggle = (vuln: Vulnerability) => {
    if (expandedId === vuln.id) {
      setExpandedId(null)
    } else {
      setExpandedId(vuln.id)
      onSelectVulnerability(vuln)
    }
  }

  const handleViewCode = (file: string, lineStart: number) => {
    onNavigateToLocation(file, lineStart)
    setCodeSheetFile(file)
    setCodeSheetLine(lineStart)
    setCodeSheetOpen(true)
  }

  return (
    <>
      <ScrollArea className="flex-1">
        <div>
          {sortedVulnerabilities.length === 0 ? (
            <div className="flex items-center justify-center p-8">
              <p className="text-base text-muted-foreground">
                No vulnerabilities reported.
              </p>
            </div>
          ) : (
            sortedVulnerabilities.map((vuln) => (
              <VulnerabilityCard
                key={vuln.id}
                vulnerability={vuln}
                isExpanded={expandedId === vuln.id}
                onToggle={() => handleToggle(vuln)}
                onViewCode={handleViewCode}
              />
            ))
          )}
        </div>
      </ScrollArea>

      <Sheet open={codeSheetOpen} onOpenChange={setCodeSheetOpen}>
        <SheetContent
          side="bottom"
          className="h-[80vh] max-h-[80vh] overflow-hidden p-0"
          showCloseButton={false}
        >
          <SheetTitle className="sr-only">Code Viewer</SheetTitle>
          <SheetDescription className="sr-only">
            View the source code for the affected location
          </SheetDescription>
          <div className="flex h-full max-h-full flex-col overflow-hidden">
            <div className="flex shrink-0 items-center justify-between gap-2 border-b px-3 py-1">
              <div className="flex min-w-0 flex-1 items-center gap-2">
                <p className="min-w-0 truncate font-mono text-sm">
                  {codeSheetFile ? truncateFilePath(codeSheetFile, 2) : "Code"}
                </p>
                {codeSheetLine && (
                  <p className="shrink-0 font-mono text-xs text-muted-foreground">
                    L{codeSheetLine}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={handleWordWrapToggle}
                  className={cn(wordWrap && "bg-muted")}
                  aria-label={
                    wordWrap ? "Disable word wrap" : "Enable word wrap"
                  }
                >
                  <HugeiconsIcon
                    icon={TextWrapIcon}
                    strokeWidth={2}
                    className="size-4"
                  />
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => setCodeSheetOpen(false)}
                  aria-label="Close"
                >
                  <HugeiconsIcon
                    icon={Cancel01Icon}
                    strokeWidth={2}
                    className="size-4"
                  />
                </Button>
              </div>
            </div>
            <div ref={codeViewportRef} className="min-h-0 flex-1 overflow-auto">
              {selectedNode ? (
                <CodeViewer
                  code={selectedNode.content || ""}
                  path={selectedNode.path}
                  annotations={codeAnnotations}
                  scrollToLine={scrollToLine ?? codeSheetLine ?? undefined}
                  wordWrap={wordWrap}
                />
              ) : (
                <div className="flex h-full items-center justify-center p-8">
                  <p className="text-base text-muted-foreground">
                    Upload a folder to view code
                  </p>
                </div>
              )}
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}
