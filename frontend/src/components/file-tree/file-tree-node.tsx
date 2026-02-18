"use client"

import {
  ArrowRight01Icon,
  File01Icon,
  Folder01Icon,
} from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { useCallback, useMemo, useRef } from "react"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { emptySeverityCounts } from "@/lib/severity"
import { cn } from "@/lib/utils"
import {
  FileSeverityIndicator,
  FolderSeverityIndicator,
} from "./severity-indicator"
import type { FileTreeNodeProps } from "./types"
import { getFileCountUnderNode } from "./utils"

export function FileTreeNode({
  node,
  selectedFile,
  onFileSelect,
  focusedPath,
  onFocusChange,
  expandedPaths,
  onToggleExpand,
  severityByPath,
  level = 0,
}: FileTreeNodeProps) {
  const isFocused = node.path === focusedPath
  const severityCounts = severityByPath?.get(node.path) || emptySeverityCounts()

  if (node.type === "folder" && node.children) {
    return (
      <FolderNode
        node={node}
        level={level}
        isFocused={isFocused}
        isOpen={expandedPaths.has(node.path)}
        severityCounts={severityCounts}
        onToggleExpand={onToggleExpand}
        onFocusChange={onFocusChange}
        severityByPath={severityByPath}
      >
        {node.children.map((child) => (
          <FileTreeNode
            key={child.path}
            node={child}
            selectedFile={selectedFile}
            onFileSelect={onFileSelect}
            focusedPath={focusedPath}
            onFocusChange={onFocusChange}
            expandedPaths={expandedPaths}
            onToggleExpand={onToggleExpand}
            severityByPath={severityByPath}
            level={level + 1}
          />
        ))}
      </FolderNode>
    )
  }

  return (
    <FileNode
      node={node}
      isFocused={isFocused}
      severityCounts={severityCounts}
      onFileSelect={onFileSelect}
      onFocusChange={onFocusChange}
    />
  )
}

interface FolderNodeProps {
  node: FileTreeNodeProps["node"]
  level: number
  isFocused: boolean
  isOpen: boolean
  severityCounts: ReturnType<typeof emptySeverityCounts>
  onToggleExpand: FileTreeNodeProps["onToggleExpand"]
  onFocusChange: FileTreeNodeProps["onFocusChange"]
  severityByPath: FileTreeNodeProps["severityByPath"]
  children: React.ReactNode
}

function FolderNode({
  node,
  level,
  isFocused,
  isOpen,
  severityCounts,
  onToggleExpand,
  onFocusChange,
  children,
}: FolderNodeProps) {
  const folderRef = useRef<HTMLDivElement>(null)
  const fileCount = useMemo(() => getFileCountUnderNode(node), [node])

  const handleOpenChange = useCallback(
    (open: boolean) => {
      onFocusChange?.(node.path)

      if (!open && folderRef.current) {
        const viewport = folderRef.current.closest(
          '[data-slot="scroll-area-viewport"]',
        ) as HTMLElement | null

        if (viewport) {
          const folderRect = folderRef.current.getBoundingClientRect()
          const viewportRect = viewport.getBoundingClientRect()
          const offsetBefore = folderRect.top - viewportRect.top

          onToggleExpand(node.path)

          requestAnimationFrame(() => {
            if (folderRef.current) {
              const newRect = folderRef.current.getBoundingClientRect()
              const offsetAfter = newRect.top - viewportRect.top
              viewport.scrollTop += offsetAfter - offsetBefore
            }
          })
          return
        }
      }

      onToggleExpand(node.path)
    },
    [node.path, onToggleExpand, onFocusChange],
  )

  return (
    <Collapsible open={isOpen} onOpenChange={handleOpenChange}>
      <div
        ref={folderRef}
        className="sticky bg-background"
        style={{ top: `${level * 24}px`, zIndex: 50 - level }}
      >
        <CollapsibleTrigger
          className={cn(
            "flex w-full items-center gap-1 py-0.5 px-2 rounded-sm text-left min-w-0",
            "hover:bg-muted/50",
            isFocused && "bg-muted/50 inset-ring-1 inset-ring-border",
          )}
        >
          <HugeiconsIcon
            icon={ArrowRight01Icon}
            strokeWidth={2}
            className={cn(
              "size-3.5 text-muted-foreground transition-transform shrink-0",
              isOpen && "rotate-90",
            )}
          />
          <HugeiconsIcon
            icon={Folder01Icon}
            strokeWidth={2}
            className="size-3.5 text-muted-foreground shrink-0"
          />
          <span className="truncate">
            {node.name}
            <span className="text-muted-foreground/60 text-xs tabular-nums">
              {" "}
              ({fileCount})
            </span>
          </span>
          <FolderSeverityIndicator counts={severityCounts} />
        </CollapsibleTrigger>
      </div>
      <CollapsibleContent>
        <div className="ml-2.5 border-l border-border/50 pl-1">{children}</div>
      </CollapsibleContent>
    </Collapsible>
  )
}

interface FileNodeProps {
  node: FileTreeNodeProps["node"]
  isFocused: boolean
  severityCounts: ReturnType<typeof emptySeverityCounts>
  onFileSelect: FileTreeNodeProps["onFileSelect"]
  onFocusChange: FileTreeNodeProps["onFocusChange"]
}

function FileNode({
  node,
  isFocused,
  severityCounts,
  onFileSelect,
  onFocusChange,
}: FileNodeProps) {
  const handleClick = useCallback(() => {
    onFocusChange?.(node.path)
    onFileSelect?.(node.path)
  }, [node.path, onFileSelect, onFocusChange])

  return (
    <button
      type="button"
      data-path={node.path}
      onClick={handleClick}
      className={cn(
        "flex w-full items-center gap-1 py-0.5 pl-6.5 pr-2 rounded-sm text-left min-w-0",
        "hover:bg-muted/50",
        isFocused && "bg-muted/50 inset-ring-1 inset-ring-border",
      )}
    >
      <HugeiconsIcon
        icon={File01Icon}
        strokeWidth={2}
        className="size-3.5 shrink-0 text-muted-foreground"
      />
      <span className="truncate">{node.name}</span>
      <FileSeverityIndicator counts={severityCounts} />
    </button>
  )
}
