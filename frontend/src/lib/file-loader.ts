import {
  createIgnore,
  createIgnoreFromGitignore,
  DEFAULT_IGNORE_PATTERNS,
} from "./gitignore"

export interface FileData {
  path: string
  content: string
  size: number
}

type FileWithPath = File & { webkitRelativePath?: string }

function getFilePath(file: FileWithPath): string {
  return file.webkitRelativePath || file.name
}

function getRootFolder(path: string): string | null {
  const parts = path.split("/")
  return parts.length > 1 ? parts[0] : null
}

async function buildIgnore(
  files: File[],
): Promise<ReturnType<typeof createIgnore>> {
  let ig = createIgnore(DEFAULT_IGNORE_PATTERNS)
  for (const file of files) {
    if (file.name === ".gitignore") {
      try {
        const content = await file.text()
        ig = createIgnoreFromGitignore(content, true)
      } catch {}
      break
    }
  }
  return ig
}

export async function readFilesFromInput(
  files: File[],
): Promise<{ rootFolder: string | null; fileData: FileData[] }> {
  const fileData: FileData[] = []
  const ig = await buildIgnore(files)
  const firstPath = files[0] ? getFilePath(files[0] as FileWithPath) : ""
  const rootFolder = firstPath ? getRootFolder(firstPath) : null

  for (const file of files) {
    let relativePath = getFilePath(file as FileWithPath)
    if (rootFolder && relativePath.startsWith(`${rootFolder}/`)) {
      relativePath = relativePath.slice(rootFolder.length + 1)
    }
    if (ig.ignores(relativePath)) continue
    try {
      const content = await file.text()
      if (content.includes("\0")) continue
      fileData.push({ path: relativePath, content, size: file.size })
    } catch {}
  }

  return { rootFolder, fileData }
}
