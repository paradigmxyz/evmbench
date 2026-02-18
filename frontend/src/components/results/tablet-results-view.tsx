"use client"

import { Cancel01Icon, TextWrapIcon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { useState } from "react"
import { CodeViewer } from "@/components/code-viewer"
import type { FileNode } from "@/components/file-tree"
import {
  VulnerabilityDetailsPanel,
  VulnerabilityListPanel,
} from "@/components/panels"
import { Button } from "@/components/ui/button"
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
} from "@/components/ui/sheet"
import { useLocalStorage } from "@/hooks/use-local-storage"
import { truncateFilePath } from "@/lib/paths"
import type { CodeAnnotation, Vulnerability } from "@/types"

interface TabletResultsViewProps {
  vulnerabilities: Vulnerability[]
  selectedVulnerability: Vulnerability | null
  onSelectVulnerability: (vuln: Vulnerability) => void
  onNavigateToLocation: (file: string, lineStart: number) => void
  selectedNode: FileNode | null
  codeAnnotations: CodeAnnotation[]
  scrollToLine?: number | null
  scrollToVulnerabilityId?: string | null
}

export function TabletResultsView({
  vulnerabilities,
  selectedVulnerability,
  onSelectVulnerability,
  onNavigateToLocation,
  selectedNode,
  codeAnnotations,
  scrollToLine,
  scrollToVulnerabilityId,
}: TabletResultsViewProps) {
  const [codeSheetOpen, setCodeSheetOpen] = useState(false)
  const [codeSheetFile, setCodeSheetFile] = useState<string | null>(null)
  const [codeSheetLine, setCodeSheetLine] = useState<number | null>(null)
  const [wordWrap, setWordWrap] = useLocalStorage("evmbench.wordWrap", true)

  const handleNavigateToLocation = (file: string, lineStart: number) => {
    onNavigateToLocation(file, lineStart)
    setCodeSheetFile(file)
    setCodeSheetLine(lineStart)
    setCodeSheetOpen(true)
  }

  return (
    <>
      <ResizablePanelGroup orientation="horizontal" className="flex-1">
        <ResizablePanel defaultSize="35%" minSize="250px" maxSize="400px">
          <VulnerabilityListPanel
            showCollapseToggle={false}
            vulnerabilities={vulnerabilities}
            selectedVulnerability={selectedVulnerability}
            onSelectVulnerability={onSelectVulnerability}
            scrollToVulnerabilityId={scrollToVulnerabilityId}
          />
        </ResizablePanel>
        <ResizableHandle />
        <ResizablePanel defaultSize="65%">
          {selectedVulnerability ? (
            <VulnerabilityDetailsPanel
              vulnerability={selectedVulnerability}
              currentFile={selectedNode?.path ?? null}
              currentLine={scrollToLine ?? null}
              onClose={() => onSelectVulnerability(selectedVulnerability)}
              onNavigateToLocation={handleNavigateToLocation}
              showViewCodeButton
            />
          ) : (
            <div className="flex h-full items-center justify-center p-8">
              <p className="text-sm text-muted-foreground">
                Select a vulnerability to view details
              </p>
            </div>
          )}
        </ResizablePanel>
      </ResizablePanelGroup>

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
            <div className="flex shrink-0 items-center justify-between gap-2 border-b px-3 py-2">
              <div className="flex min-w-0 flex-1 items-center gap-2">
                <p className="min-w-0 truncate font-mono text-sm">
                  {codeSheetFile ? truncateFilePath(codeSheetFile, 2) : "Code"}
                </p>
                {codeSheetLine && (
                  <p className="shrink-0 text-sm text-muted-foreground">
                    L{codeSheetLine}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  onClick={() => setWordWrap(!wordWrap)}
                  className={wordWrap ? "bg-muted" : ""}
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
            <div className="min-h-0 flex-1 overflow-auto">
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
                  <p className="text-sm text-muted-foreground">
                    No file selected
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
