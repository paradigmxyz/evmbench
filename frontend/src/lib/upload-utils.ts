type FileWithPath = File & { webkitRelativePath?: string }

export function inferPackageName(files: File[]): string | null {
  const first = (files[0] ?? null) as FileWithPath | null
  if (!first) return null
  if (first.webkitRelativePath) {
    return first.webkitRelativePath.split("/")[0] ?? first.name
  }
  return first.name
}
