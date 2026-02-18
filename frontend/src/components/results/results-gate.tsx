"use client"

import { FileUploader } from "@/components/file-uploader"
import { Button } from "@/components/ui/button"

interface ResultsGateProps {
  packageName: string | null
  validationError: string | null
  onFilesSelected: (files: File[]) => void
}

export function ResultsGate({
  packageName,
  validationError,
  onFilesSelected,
}: ResultsGateProps) {
  return (
    <section className="flex flex-1 items-center justify-center px-6 py-10">
      <div className="w-full max-w-xl space-y-6">
        <div className="space-y-1">
          <h1 className="text-base text-foreground">Validation required</h1>
          <p className="text-base text-muted-foreground">
            Upload the exact contract folder used for this run.
          </p>
        </div>
        <div className="space-y-3">
          <FileUploader
            onFilesSelected={onFilesSelected}
            selectedLabel={packageName ?? "Choose folder"}
            fileCount={null}
          />
          {validationError && (
            <p className="text-xs text-destructive">{validationError}</p>
          )}
        </div>
        <Button asChild variant="outline">
          <a href="/">Back to upload</a>
        </Button>
      </div>
    </section>
  )
}
