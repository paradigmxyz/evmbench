"use client"

import {
  ArrowExpand02Icon,
  ArrowShrink02Icon,
  Folder01Icon,
} from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { useRef, useState } from "react"
import { type FileNode, FileTree } from "@/components/file-tree"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { useScrollIntoView } from "@/hooks/use-scroll-into-view"
import type { SeverityCounts } from "@/lib/severity"
import { cn } from "@/lib/utils"
import { PanelHeader } from "./panel-header"

interface FileTreePanelProps {
  folderName: string | null
  isAllExpanded: boolean
  onToggleExpandAll: () => void
  fileTree: FileNode[]
  selectedFile: string | null
  onFileSelect: (file: string | null) => void
  focusedPath: string | null
  onFocusChange: (path: string | null) => void
  expandedPaths: Set<string>
  onToggleExpand: (path: string) => void
  isCollapsed: boolean
  onToggleCollapse: () => void
  scrollToPath?: string | null
  severityByPath?: Map<string, SeverityCounts>
  emptyState?: React.ReactNode
}

export function FileTreePanel({
  folderName,
  isAllExpanded,
  onToggleExpandAll,
  fileTree,
  selectedFile,
  onFileSelect,
  focusedPath,
  onFocusChange,
  expandedPaths,
  onToggleExpand,
  isCollapsed,
  onToggleCollapse,
  scrollToPath,
  severityByPath,
  emptyState,
}: FileTreePanelProps) {
  const containerRef = useRef<HTMLDivElement>(null)

  const scrollTarget = scrollToPath
    ? `[data-path="${CSS.escape(scrollToPath)}"]`
    : null
  useScrollIntoView(containerRef, scrollTarget)
  const [expandTooltipOpen, setExpandTooltipOpen] = useState(false)

  const headerActions =
    folderName && !isCollapsed ? (
      <Tooltip open={expandTooltipOpen} onOpenChange={setExpandTooltipOpen}>
        <TooltipTrigger
          render={(triggerProps) => (
            <button
              {...triggerProps}
              type="button"
              onPointerDown={(event) => event.preventDefault()}
              onClick={() => {
                onToggleExpandAll()
                setExpandTooltipOpen(true)
              }}
              className={cn(
                "rounded p-1 -my-0.5",
                isAllExpanded
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground",
              )}
              aria-label={isAllExpanded ? "Collapse all" : "Expand all"}
            >
              <HugeiconsIcon
                icon={isAllExpanded ? ArrowShrink02Icon : ArrowExpand02Icon}
                strokeWidth={2}
                className="size-3.5"
              />
            </button>
          )}
        />
        <TooltipContent side="bottom" sideOffset={6}>
          {isAllExpanded ? "Collapse all" : "Expand all"}
        </TooltipContent>
      </Tooltip>
    ) : null

  return (
    <div className="flex h-full min-w-0 flex-col overflow-hidden">
      <PanelHeader
        icon={Folder01Icon}
        title={folderName || "Explorer"}
        isCollapsed={isCollapsed}
        onToggleCollapse={onToggleCollapse}
        actions={headerActions}
      />
      {!isCollapsed && (
        <ScrollArea className="min-w-0 flex-1 max-h-48 md:max-h-none">
          <div ref={containerRef}>
            {fileTree.length > 0 ? (
              <div className="ml-4 mr-2">
                <FileTree
                  nodes={fileTree}
                  selectedFile={selectedFile}
                  onFileSelect={onFileSelect}
                  focusedPath={focusedPath}
                  onFocusChange={onFocusChange}
                  expandedPaths={expandedPaths}
                  onToggleExpand={onToggleExpand}
                  severityByPath={severityByPath}
                />
              </div>
            ) : (
              <div className="flex h-full flex-col items-center justify-center p-6 text-center">
                {emptyState ?? (
                  <div className="space-y-3">
                    <HugeiconsIcon
                      icon={Folder01Icon}
                      strokeWidth={1.5}
                      className="mx-auto size-8 text-muted-foreground/50"
                    />
                    <div className="space-y-1">
                      <p className="text-sm text-foreground">No files loaded</p>
                      <p className="text-base text-muted-foreground">
                        Upload a folder on the home page to populate the
                        explorer.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </ScrollArea>
      )}
    </div>
  )
}
