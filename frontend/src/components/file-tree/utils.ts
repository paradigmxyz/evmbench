import { normalizeFilePath } from "@/lib/paths"
import type { FileNode } from "./types"

export function buildFileTree(
  files: { path: string; content: string; size: number }[],
): FileNode[] {
  const root: FileNode[] = []

  for (const file of files) {
    const normalizedPath = normalizeFilePath(file.path)
    if (!normalizedPath) continue
    const parts = normalizedPath.split("/")
    let current = root

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i]
      const isFile = i === parts.length - 1
      const path = parts.slice(0, i + 1).join("/")

      let existing = current.find((n) => n.name === part)

      if (!existing) {
        existing = {
          name: part,
          path,
          type: isFile ? "file" : "folder",
          children: isFile ? undefined : [],
          content: isFile ? file.content : undefined,
          size: isFile ? file.size : undefined,
        }
        current.push(existing)
      }

      if (!isFile && existing.children) {
        current = existing.children
      }
    }
  }

  return sortNodes(root)
}

function sortNodes(nodes: FileNode[]): FileNode[] {
  return nodes
    .sort((a, b) => {
      if (a.type !== b.type) return a.type === "folder" ? -1 : 1
      return a.name.localeCompare(b.name)
    })
    .map((node) => ({
      ...node,
      children: node.children ? sortNodes(node.children) : undefined,
    }))
}

export function getAllFilePaths(nodes: FileNode[]): string[] {
  const paths: string[] = []

  function traverse(node: FileNode): void {
    if (node.type === "file") {
      paths.push(node.path)
    }
    node.children?.forEach(traverse)
  }

  nodes.forEach(traverse)
  return paths
}

export function getFileCountUnderNode(node: FileNode): number {
  if (node.type === "file") return 1

  let count = 0
  function traverse(n: FileNode): void {
    if (n.type === "file") {
      count++
    }
    n.children?.forEach(traverse)
  }
  traverse(node)
  return count
}

export function getAllFolderPaths(nodes: FileNode[]): string[] {
  const paths: string[] = []

  function traverse(node: FileNode): void {
    if (node.type === "folder") {
      paths.push(node.path)
    }
    node.children?.forEach(traverse)
  }

  nodes.forEach(traverse)
  return paths
}

export function getTopLevelFolderPaths(nodes: FileNode[]): string[] {
  return nodes.filter((node) => node.type === "folder").map((node) => node.path)
}

export function buildFileMap(nodes: FileNode[]): Map<string, FileNode> {
  const map = new Map<string, FileNode>()

  function traverse(node: FileNode): void {
    if (node.type === "file") {
      map.set(normalizeFilePath(node.path), node)
    }
    node.children?.forEach(traverse)
  }

  nodes.forEach(traverse)
  return map
}
