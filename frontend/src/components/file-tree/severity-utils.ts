import { matchPathFlexibly, normalizeFilePath } from "@/lib/paths"
import {
  emptySeverityCounts,
  mergeSeverityCounts,
  type SeverityCounts,
} from "@/lib/severity"
import type { Vulnerability } from "@/types"
import type { FileNode } from "./types"

export function buildFileSeverityMap(
  vulnerabilities: Vulnerability[],
  availableFilePaths?: Set<string>,
): Map<string, SeverityCounts> {
  const map = new Map<string, SeverityCounts>()

  for (const vuln of vulnerabilities) {
    const filesForVuln = new Set<string>()
    for (const loc of vuln.description) {
      const keyPath = availableFilePaths
        ? (matchPathFlexibly(loc.file, availableFilePaths) ??
          normalizeFilePath(loc.file))
        : normalizeFilePath(loc.file)
      filesForVuln.add(keyPath)
    }

    for (const keyPath of filesForVuln) {
      const existing = map.get(keyPath) || emptySeverityCounts()
      existing[vuln.severity] = (existing[vuln.severity] || 0) + 1
      map.set(keyPath, existing)
    }
  }

  return map
}

export function getFileSeverityCounts(
  path: string,
  fileSeverityMap: Map<string, SeverityCounts>,
): SeverityCounts {
  const normalizedPath = normalizeFilePath(path)
  return fileSeverityMap.get(normalizedPath) || emptySeverityCounts()
}

export function getFolderSeverityCounts(
  node: FileNode,
  fileSeverityMap: Map<string, SeverityCounts>,
): SeverityCounts {
  let total = emptySeverityCounts()

  function traverse(n: FileNode): void {
    if (n.type === "file") {
      total = mergeSeverityCounts(
        total,
        getFileSeverityCounts(n.path, fileSeverityMap),
      )
    }
    n.children?.forEach(traverse)
  }

  traverse(node)
  return total
}

export function getNodeSeverityCounts(
  node: FileNode,
  fileSeverityMap: Map<string, SeverityCounts>,
): SeverityCounts {
  return node.type === "folder"
    ? getFolderSeverityCounts(node, fileSeverityMap)
    : getFileSeverityCounts(node.path, fileSeverityMap)
}

export function buildSeverityMap(
  nodes: FileNode[],
  fileSeverityMap: Map<string, SeverityCounts>,
): Map<string, SeverityCounts> {
  const map = new Map<string, SeverityCounts>()

  function traverse(node: FileNode): SeverityCounts {
    if (node.type === "file") {
      const counts = getFileSeverityCounts(node.path, fileSeverityMap)
      map.set(node.path, counts)
      return counts
    }

    let total = emptySeverityCounts()
    node.children?.forEach((child) => {
      total = mergeSeverityCounts(total, traverse(child))
    })
    map.set(node.path, total)
    return total
  }

  nodes.forEach((node) => {
    traverse(node)
  })

  return map
}
