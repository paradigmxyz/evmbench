import JSZip from "jszip"

type FileWithPath = File & { webkitRelativePath?: string }

function getFilePath(file: FileWithPath): string {
  return file.webkitRelativePath || file.name
}

function getRootFolder(path: string): string | null {
  const parts = path.split("/")
  return parts.length > 1 ? parts[0] : null
}

function isZipFile(file: File): boolean {
  return (
    file.type === "application/zip" ||
    file.type === "application/x-zip-compressed" ||
    file.name.toLowerCase().endsWith(".zip")
  )
}

export async function createZipFromFiles(
  files: File[],
  name: string,
): Promise<File> {
  if (files.length === 1 && isZipFile(files[0])) {
    const file = files[0]
    if (file.name.toLowerCase().endsWith(".zip")) {
      return file
    }
    return new File([file], `${name}.zip`, { type: "application/zip" })
  }

  const zip = new JSZip()
  const firstPath = files[0] ? getFilePath(files[0] as FileWithPath) : ""
  const rootFolder = firstPath ? getRootFolder(firstPath) : null

  for (const file of Array.from(files)) {
    let path = getFilePath(file as FileWithPath)
    if (rootFolder && path.startsWith(`${rootFolder}/`)) {
      path = path.slice(rootFolder.length + 1)
    }
    if (!path) continue
    zip.file(path, file)
  }

  const blob = await zip.generateAsync({ type: "blob" })
  return new File([blob], `${name}.zip`, { type: "application/zip" })
}
