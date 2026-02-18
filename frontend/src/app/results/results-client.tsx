"use client"

import { useSearchParams } from "next/navigation"
import { parseAsInteger, parseAsString, useQueryStates } from "nuqs"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { usePanelRef } from "react-resizable-panels"
import { AppFooter } from "@/components/app-footer"
import { getAllFilePaths } from "@/components/file-tree"
import {
  buildFileSeverityMap,
  buildSeverityMap,
} from "@/components/file-tree/severity-utils"
import { FileUploader } from "@/components/file-uploader"
import {
  CodeViewerPanel,
  FileTreePanel,
  RunStatusPanel,
  VulnerabilityDetailsPanel,
  VulnerabilityListPanel,
} from "@/components/panels"
import {
  MobileResultsView,
  ResultsGate,
  ResultsHeader,
  TabletResultsView,
} from "@/components/results"
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable"
import { useAuth } from "@/hooks/use-auth"
import { useFileExplorer } from "@/hooks/use-file-explorer"
import { useJob } from "@/hooks/use-job"
import { useMediaQuery } from "@/hooks/use-media-query"
import { useMounted } from "@/hooks/use-mounted"
import { useVulnerabilityNavigation } from "@/hooks/use-vulnerability-navigation"
import { readFilesFromInput } from "@/lib/file-loader"
import { validateFileData } from "@/lib/file-validation"
import { mapJobVulnerabilities, setJobPublic } from "@/lib/jobs"
import { normalizeFilePath } from "@/lib/paths"
import { addRecentJob } from "@/lib/recent-jobs"
import { inferPackageName } from "@/lib/upload-utils"
import { cn } from "@/lib/utils"
import { useUploadStore } from "@/store/upload-store"

export default function ResultsClient() {
  const isNarrowViewport = useMediaQuery("(max-width: 1024px)")
  const isMobileViewport = useMediaQuery("(max-width: 768px)")
  const searchParams = useSearchParams()

  const [urlState, setUrlState] = useQueryStates(
    {
      job_id: parseAsString,
      file: parseAsString,
      vuln: parseAsString,
      line: parseAsInteger,
    },
    {
      history: "replace",
      shallow: true,
    },
  )

  const jobId = urlState.job_id

  const { files, packageName, setUpload } = useUploadStore()
  const lastLoadedFiles = useRef<File[] | null>(null)
  const skipAutoLoadRef = useRef(false)

  const fileTreePanelRef = usePanelRef()
  const bugViewerPanelRef = usePanelRef()
  const [isFileTreeCollapsed, setIsFileTreeCollapsed] = useState(false)
  const [isBugViewerCollapsed, setIsBugViewerCollapsed] = useState(false)
  const isMounted = useMounted()
  const { isAuthEnabled } = useAuth()

  const clearSelectionRef = useRef<(() => void) | null>(null)

  const [validationError, setValidationError] = useState<string | null>(null)
  const [shareError, setShareError] = useState<string | null>(null)
  const [isUpdatingPublic, setIsUpdatingPublic] = useState(false)
  const {
    job,
    error: jobError,
    isLoading: isLoadingJob,
    isComplete: isRunComplete,
    shouldShowRunStatus,
    setJob,
  } = useJob(jobId)

  useEffect(() => {
    if (!jobId || !job) return
    // If a user lands here via a copied link, still remember it locally.
    addRecentJob({
      job_id: jobId,
      label: job.file_name?.replace(/\.zip$/, "") ?? "run",
      created_at_ms: Date.now(),
    })
  }, [jobId, job])

  const setUrlFile = useCallback(
    (file: string | null) => {
      setUrlState({ file })
    },
    [setUrlState],
  )

  const setUrlVuln = useCallback(
    (vuln: string | null) => {
      setUrlState({ vuln })
    },
    [setUrlState],
  )

  const setUrlLine = useCallback(
    (line: number | null) => {
      setUrlState({ line })
    },
    [setUrlState],
  )

  const {
    fileTree,
    selectedFile,
    focusedPath,
    folderName,
    expandedPaths,
    scrollToPath,
    isAllExpanded,
    selectedNode,
    setFocusedPath,
    handleFiles,
    loadFileData,
    handleToggleExpand,
    handleToggleExpandAll,
    navigateToFile,
    handleFileSelect,
  } = useFileExplorer({
    onResetSelectionRef: clearSelectionRef,
    onFileSelectRef: clearSelectionRef,
    controlledSelectedFile: urlState.file,
    setControlledSelectedFile: setUrlFile,
  })

  useEffect(() => {
    if (!files) {
      lastLoadedFiles.current = null
      return
    }
    if (files === lastLoadedFiles.current) return
    if (skipAutoLoadRef.current) {
      skipAutoLoadRef.current = false
      return
    }
    lastLoadedFiles.current = files
    void handleFiles(files)
  }, [files, handleFiles])

  const vulnerabilities = useMemo(
    () => mapJobVulnerabilities(job?.result ?? null),
    [job?.result],
  )

  const availableFilePaths = useMemo(
    () => new Set(getAllFilePaths(fileTree).map(normalizeFilePath)),
    [fileTree],
  )
  const fileSeverityMap = useMemo(
    () => buildFileSeverityMap(vulnerabilities, availableFilePaths),
    [vulnerabilities, availableFilePaths],
  )
  const severityByPath = useMemo(
    () => buildSeverityMap(fileTree, fileSeverityMap),
    [fileTree, fileSeverityMap],
  )

  useEffect(() => {
    if (urlState.job_id) return
    const legacyJobId = searchParams.get("jobId")
    if (legacyJobId) {
      setUrlState({ job_id: legacyJobId })
    }
  }, [searchParams, setUrlState, urlState.job_id])

  const hasRestoredFromUrl = useRef(false)
  const lastRestoredJobId = useRef<string | null | undefined>(undefined)
  useEffect(() => {
    if (lastRestoredJobId.current !== jobId) {
      hasRestoredFromUrl.current = false
      lastRestoredJobId.current = jobId
    }
    if (
      fileTree.length > 0 &&
      urlState.file &&
      availableFilePaths.has(normalizeFilePath(urlState.file)) &&
      !hasRestoredFromUrl.current
    ) {
      hasRestoredFromUrl.current = true
      navigateToFile(urlState.file)
    }
  }, [
    availableFilePaths,
    fileTree.length,
    urlState.file,
    navigateToFile,
    jobId,
  ])

  const handlePromptFiles = useCallback(
    async (selected: File[]) => {
      setValidationError(null)
      const { rootFolder, fileData } = await readFilesFromInput(selected)
      const validationMessage = validateFileData(fileData, vulnerabilities)
      if (validationMessage) {
        setValidationError(validationMessage)
        return
      }

      loadFileData(rootFolder, fileData)
      skipAutoLoadRef.current = true
      lastLoadedFiles.current = selected
      setUpload(selected, rootFolder ?? inferPackageName(selected))
    },
    [loadFileData, setUpload, vulnerabilities],
  )

  useEffect(() => {
    if (!urlState.file || fileTree.length === 0) return
    const normalizedFile = normalizeFilePath(urlState.file)
    if (!availableFilePaths.has(normalizedFile)) {
      setUrlState({ file: null, vuln: null, line: null })
    }
  }, [availableFilePaths, fileTree.length, setUrlState, urlState.file])

  const {
    selectedVulnerability,
    scrollToLine,
    scrollToVulnerabilityId,
    codeAnnotations,
    setSelectedVulnerability,
    handleSelectVulnerability,
    handleNavigateToLocation,
    handleAnnotationClick,
    clearSelection,
  } = useVulnerabilityNavigation({
    vulnerabilities,
    selectedFile,
    navigateToFile,
    controlledVulnId: urlState.vuln,
    setControlledVulnId: setUrlVuln,
    controlledLine: urlState.line,
    setControlledLine: setUrlLine,
  })

  useEffect(() => {
    clearSelectionRef.current = clearSelection
  }, [clearSelection])

  const prevJobIdRef = useRef<string | null | undefined>(undefined)
  useEffect(() => {
    if (prevJobIdRef.current !== undefined && prevJobIdRef.current !== jobId) {
      setUrlState({ file: null, vuln: null, line: null })
    }
    prevJobIdRef.current = jobId
  }, [jobId, setUrlState])

  useEffect(() => {
    if (jobId !== undefined) {
      setShareError(null)
    }
  }, [jobId])

  const resetBothPanels = useCallback(() => {
    fileTreePanelRef.current?.resize("50%")
    bugViewerPanelRef.current?.resize("50%")
    setIsFileTreeCollapsed(false)
    setIsBugViewerCollapsed(false)
  }, [fileTreePanelRef, bugViewerPanelRef])

  const handleToggleFileTreeCollapse = useCallback(() => {
    const panel = fileTreePanelRef.current
    const otherPanel = bugViewerPanelRef.current
    if (!panel) return

    if (panel.isCollapsed()) {
      panel.expand()
      setIsFileTreeCollapsed(false)
    } else {
      if (otherPanel?.isCollapsed()) {
        resetBothPanels()
      } else {
        panel.collapse()
        setIsFileTreeCollapsed(true)
      }
    }
  }, [fileTreePanelRef, bugViewerPanelRef, resetBothPanels])

  const handleToggleBugViewerCollapse = useCallback(() => {
    const panel = bugViewerPanelRef.current
    const otherPanel = fileTreePanelRef.current
    if (!panel) return

    if (panel.isCollapsed()) {
      panel.expand()
      setIsBugViewerCollapsed(false)
    } else {
      if (otherPanel?.isCollapsed()) {
        resetBothPanels()
      } else {
        panel.collapse()
        setIsBugViewerCollapsed(true)
      }
    }
  }, [bugViewerPanelRef, fileTreePanelRef, resetBothPanels])

  const handleTogglePublic = useCallback(async () => {
    if (!jobId || !job) return
    setShareError(null)
    setIsUpdatingPublic(true)
    try {
      const updated = await setJobPublic(jobId, !job.public)
      setJob(updated)
    } catch (error) {
      setShareError(
        error instanceof Error ? error.message : "Failed to update sharing",
      )
    } finally {
      setIsUpdatingPublic(false)
    }
  }, [jobId, job, setJob])

  const emptyState = useMemo(() => {
    if (isRunComplete && !files) {
      return null
    }
    if (!files) {
      return (
        <div className="w-full space-y-3">
          <div className="space-y-1 text-center">
            <p className="text-sm text-foreground">
              Select a folder to view code
            </p>
            <p className="text-base text-muted-foreground">
              We will verify it matches the reported findings before loading.
            </p>
          </div>
          <FileUploader
            onFilesSelected={handlePromptFiles}
            selectedLabel={packageName ?? "Choose folder"}
            fileCount={null}
          />
          {validationError && (
            <p className="text-xs text-destructive">{validationError}</p>
          )}
        </div>
      )
    }
    if (files && fileTree.length === 0) {
      return (
        <div className="space-y-1 text-center">
          <p className="text-sm text-foreground">
            Loading files from {packageName ?? "upload"}
          </p>
          <p className="text-base text-muted-foreground">
            Parsing folder contents for the explorer.
          </p>
        </div>
      )
    }
    return null
  }, [
    files,
    fileTree,
    packageName,
    handlePromptFiles,
    validationError,
    isRunComplete,
  ])

  const shouldGateResults = isRunComplete && !files
  const statusError = jobError || job?.error

  return (
    <main className="flex min-h-screen w-screen flex-col md:h-screen">
      <ResultsHeader
        jobId={jobId}
        job={job}
        isLoading={isLoadingJob}
        error={jobError}
        onTogglePublic={handleTogglePublic}
        isUpdatingPublic={isUpdatingPublic}
        shareError={shareError}
        isAuthEnabled={isAuthEnabled}
      />
      {statusError && (
        <div className="border-b border-border/60 bg-destructive/10 px-4 py-2 text-xs text-destructive">
          {statusError}
        </div>
      )}

      {shouldGateResults ? (
        <ResultsGate
          packageName={packageName}
          validationError={validationError}
          onFilesSelected={handlePromptFiles}
        />
      ) : shouldShowRunStatus ? (
        <section
          className={cn(
            "flex flex-1 items-center justify-center px-6 py-10",
            isMounted ? "opacity-100" : "opacity-0",
          )}
        >
          <div className="w-full max-w-2xl">
            <RunStatusPanel job={job} isLoading={isLoadingJob} />
          </div>
        </section>
      ) : isMobileViewport ? (
        <MobileResultsView
          vulnerabilities={vulnerabilities}
          onSelectVulnerability={handleSelectVulnerability}
          onNavigateToLocation={handleNavigateToLocation}
          selectedNode={selectedNode}
          codeAnnotations={codeAnnotations}
          scrollToLine={scrollToLine}
        />
      ) : isNarrowViewport ? (
        <TabletResultsView
          vulnerabilities={vulnerabilities}
          selectedVulnerability={selectedVulnerability}
          onSelectVulnerability={handleSelectVulnerability}
          onNavigateToLocation={handleNavigateToLocation}
          selectedNode={selectedNode}
          codeAnnotations={codeAnnotations}
          scrollToLine={scrollToLine}
          scrollToVulnerabilityId={scrollToVulnerabilityId}
        />
      ) : (
        <ResizablePanelGroup
          orientation="horizontal"
          className={cn("flex-1", isMounted ? "opacity-100" : "opacity-0")}
        >
          <ResizablePanel defaultSize="20%" minSize="300px" maxSize="420px">
            <ResizablePanelGroup
              orientation="vertical"
              className="h-full py-1.5"
            >
              <ResizablePanel
                panelRef={fileTreePanelRef}
                defaultSize="50%"
                minSize="25px"
                collapsible
                collapsedSize="25px"
                onResize={() => {
                  setIsFileTreeCollapsed(
                    fileTreePanelRef.current?.isCollapsed() ?? false,
                  )
                }}
              >
                <FileTreePanel
                  folderName={folderName ?? packageName}
                  isAllExpanded={isAllExpanded}
                  onToggleExpandAll={handleToggleExpandAll}
                  fileTree={fileTree}
                  selectedFile={selectedFile}
                  onFileSelect={handleFileSelect}
                  focusedPath={focusedPath}
                  onFocusChange={setFocusedPath}
                  expandedPaths={expandedPaths}
                  onToggleExpand={handleToggleExpand}
                  isCollapsed={isFileTreeCollapsed}
                  onToggleCollapse={handleToggleFileTreeCollapse}
                  scrollToPath={scrollToPath}
                  severityByPath={severityByPath}
                  emptyState={emptyState}
                />
              </ResizablePanel>
              <ResizableHandle />
              <ResizablePanel
                panelRef={bugViewerPanelRef}
                defaultSize="50%"
                minSize="26px"
                collapsible
                collapsedSize="26px"
                className="pt-1.5"
                onResize={() => {
                  setIsBugViewerCollapsed(
                    bugViewerPanelRef.current?.isCollapsed() ?? false,
                  )
                }}
              >
                <VulnerabilityListPanel
                  isCollapsed={isBugViewerCollapsed}
                  onToggleCollapse={handleToggleBugViewerCollapse}
                  vulnerabilities={vulnerabilities}
                  selectedVulnerability={selectedVulnerability}
                  onSelectVulnerability={handleSelectVulnerability}
                  scrollToVulnerabilityId={scrollToVulnerabilityId}
                />
              </ResizablePanel>
            </ResizablePanelGroup>
          </ResizablePanel>
          <ResizableHandle />
          <ResizablePanel defaultSize="80%">
            <ResizablePanelGroup
              orientation={isNarrowViewport ? "vertical" : "horizontal"}
              className="h-full"
            >
              <ResizablePanel
                defaultSize={selectedVulnerability ? "60%" : "100%"}
                minSize={isNarrowViewport ? "240px" : "420px"}
              >
                <CodeViewerPanel
                  selectedNode={selectedNode}
                  onClose={() => {
                    handleFileSelect(null)
                  }}
                  annotations={codeAnnotations}
                  focusedAnnotationId={selectedVulnerability?.id}
                  scrollToLine={scrollToLine}
                  onAnnotationClick={handleAnnotationClick}
                />
              </ResizablePanel>
              {selectedVulnerability && (
                <>
                  <ResizableHandle />
                  <ResizablePanel
                    defaultSize={isNarrowViewport ? "40%" : "40%"}
                    minSize={isNarrowViewport ? "200px" : "320px"}
                    maxSize={isNarrowViewport ? "60%" : "520px"}
                  >
                    <VulnerabilityDetailsPanel
                      vulnerability={selectedVulnerability}
                      currentFile={selectedFile}
                      currentLine={scrollToLine}
                      onClose={() => setSelectedVulnerability(null)}
                      onNavigateToLocation={handleNavigateToLocation}
                    />
                  </ResizablePanel>
                </>
              )}
            </ResizablePanelGroup>
          </ResizablePanel>
        </ResizablePanelGroup>
      )}
      <AppFooter />
    </main>
  )
}
