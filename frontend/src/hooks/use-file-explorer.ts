import type { RefObject } from "react"
import { useCallback, useMemo, useState } from "react"
import {
  buildFileMap,
  buildFileTree,
  type FileNode,
  getAllFolderPaths,
  getTopLevelFolderPaths,
} from "@/components/file-tree"
import { useAutoResetState } from "@/hooks/use-auto-reset-state"
import { type FileData, readFilesFromInput } from "@/lib/file-loader"
import { matchPathFlexibly, normalizeFilePath } from "@/lib/paths"

interface UseFileExplorerOptions {
  onResetSelection?: () => void
  onFileSelect?: (path: string | null) => void
  onResetSelectionRef?: RefObject<(() => void) | null>
  onFileSelectRef?: RefObject<((path: string | null) => void) | null>
  controlledSelectedFile?: string | null
  setControlledSelectedFile?: (file: string | null) => void
}

export function useFileExplorer({
  onResetSelection,
  onFileSelect,
  onResetSelectionRef,
  onFileSelectRef,
  controlledSelectedFile,
  setControlledSelectedFile,
}: UseFileExplorerOptions = {}) {
  const [fileTree, setFileTree] = useState<FileNode[]>([])
  const [internalSelectedFile, setInternalSelectedFile] = useState<
    string | null
  >(null)
  const [focusedPath, setFocusedPath] = useState<string | null>(null)

  const isControlled = controlledSelectedFile !== undefined
  const selectedFile = isControlled
    ? controlledSelectedFile
    : internalSelectedFile
  const setSelectedFile = isControlled
    ? (setControlledSelectedFile ?? (() => {}))
    : setInternalSelectedFile
  const [folderName, setFolderName] = useState<string | null>(null)
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set())
  const [scrollToPath, setScrollToPath] = useAutoResetState<string | null>(
    null,
    0,
  )

  const allFolderPaths = useMemo(() => getAllFolderPaths(fileTree), [fileTree])
  const isAllExpanded =
    allFolderPaths.length > 0 &&
    allFolderPaths.every((p) => expandedPaths.has(p))
  const fileMap = useMemo(() => buildFileMap(fileTree), [fileTree])
  const fileMapKeySet = useMemo(() => new Set(fileMap.keys()), [fileMap])

  const loadFileData = useCallback(
    (rootFolder: string | null, fileData: FileData[]) => {
      const tree = buildFileTree(fileData)
      setFileTree(tree)
      setFolderName(rootFolder)
      setFocusedPath(null)
      setExpandedPaths(new Set(getTopLevelFolderPaths(tree)))
    },
    [],
  )

  const handleFiles = useCallback(
    async (files: File[] | null) => {
      if (!files || files.length === 0) return
      const { rootFolder, fileData } = await readFilesFromInput(files)
      loadFileData(rootFolder, fileData)
    },
    [loadFileData],
  )

  const handleToggleExpand = useCallback((path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev)
      if (next.has(path)) {
        next.delete(path)
      } else {
        next.add(path)
      }
      return next
    })
  }, [])

  const handleToggleExpandAll = useCallback(() => {
    if (isAllExpanded) {
      setExpandedPaths(new Set())
    } else {
      setExpandedPaths(new Set(allFolderPaths))
    }
  }, [isAllExpanded, allFolderPaths])

  const handleClearFolder = useCallback(() => {
    setFileTree([])
    setFolderName(null)
    setSelectedFile(null)
    setFocusedPath(null)
    setExpandedPaths(new Set())
    onResetSelection?.()
    onResetSelectionRef?.current?.()
  }, [onResetSelection, onResetSelectionRef, setSelectedFile])

  const navigateToFile = useCallback(
    (filePath: string) => {
      const matchedPath = matchPathFlexibly(filePath, fileMapKeySet)
      const fileNode = matchedPath ? fileMap.get(matchedPath) : undefined

      if (fileNode) {
        setSelectedFile(fileNode.path)
        setFocusedPath(fileNode.path)

        const pathParts = fileNode.path.split("/")
        const foldersToExpand: string[] = []
        for (let i = 1; i < pathParts.length; i++) {
          foldersToExpand.push(pathParts.slice(0, i).join("/"))
        }
        setExpandedPaths((prev) => {
          const next = new Set(prev)
          for (const path of foldersToExpand) {
            next.add(path)
          }
          return next
        })

        setScrollToPath(fileNode.path)
      }
    },
    [fileMap, fileMapKeySet, setScrollToPath, setSelectedFile],
  )

  const handleFileSelect = useCallback(
    (path: string | null) => {
      setSelectedFile(path)
      onFileSelect?.(path)
      onFileSelectRef?.current?.(path)
    },
    [onFileSelect, onFileSelectRef, setSelectedFile],
  )

  const selectedNode = useMemo(() => {
    if (!selectedFile) return null
    return fileMap.get(normalizeFilePath(selectedFile)) ?? null
  }, [fileMap, selectedFile])

  return {
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
    handleClearFolder,
    navigateToFile,
    handleFileSelect,
  }
}
