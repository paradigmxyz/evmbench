import { create } from "zustand"

interface UploadState {
  files: File[] | null
  packageName: string | null
  setUpload: (files: File[] | null, packageName: string | null) => void
  clearUpload: () => void
}

export const useUploadStore = create<UploadState>((set) => ({
  files: null,
  packageName: null,
  setUpload: (files, packageName) => set({ files, packageName }),
  clearUpload: () => set({ files: null, packageName: null }),
}))
