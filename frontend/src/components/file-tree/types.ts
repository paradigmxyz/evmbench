import type { SeverityCounts } from "@/lib/severity"

export interface FileNode {
  name: string
  path: string
  type: "file" | "folder"
  children?: FileNode[]
  content?: string
  size?: number
}

export interface FileTreeProps {
  nodes: FileNode[]
  selectedFile?: string | null
  onFileSelect?: (path: string) => void
  focusedPath?: string | null
  onFocusChange?: (path: string) => void
  expandedPaths: Set<string>
  onToggleExpand: (path: string) => void
  severityByPath?: Map<string, SeverityCounts>
}

export interface FileTreeNodeProps {
  node: FileNode
  selectedFile?: string | null
  onFileSelect?: (path: string) => void
  focusedPath?: string | null
  onFocusChange?: (path: string) => void
  expandedPaths: Set<string>
  onToggleExpand: (path: string) => void
  severityByPath?: Map<string, SeverityCounts>
  level?: number
}
