"use client"

import {
  Empty,
  EmptyContent,
  EmptyDescription,
  EmptyHeader,
  EmptyTitle,
} from "@/components/ui/empty"
import { FileTreeNode } from "./file-tree-node"
import type { FileTreeProps } from "./types"

export function FileTree({
  nodes,
  selectedFile,
  onFileSelect,
  focusedPath,
  onFocusChange,
  expandedPaths,
  onToggleExpand,
  severityByPath,
}: FileTreeProps) {
  if (nodes.length === 0) {
    return (
      <Empty className="border-none px-2 py-8">
        <EmptyHeader>
          <EmptyTitle>No files loaded</EmptyTitle>
        </EmptyHeader>
        <EmptyContent>
          <EmptyDescription>
            Upload a folder to populate the explorer.
          </EmptyDescription>
        </EmptyContent>
      </Empty>
    )
  }

  return (
    <div className="text-sm">
      {nodes.map((node) => (
        <FileTreeNode
          key={node.path}
          node={node}
          selectedFile={selectedFile}
          onFileSelect={onFileSelect}
          focusedPath={focusedPath}
          onFocusChange={onFocusChange}
          expandedPaths={expandedPaths}
          onToggleExpand={onToggleExpand}
          severityByPath={severityByPath}
        />
      ))}
    </div>
  )
}
