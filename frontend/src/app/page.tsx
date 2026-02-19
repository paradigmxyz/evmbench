"use client"

import { ArrowUpRight01Icon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { useRouter } from "next/navigation"
import { useCallback, useMemo, useState } from "react"
import { AppFooter } from "@/components/app-footer"
import { AppHeader } from "@/components/app-header"
import { FileUploader } from "@/components/file-uploader"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useAuth } from "@/hooks/use-auth"
import { useLocalStorage } from "@/hooks/use-local-storage"
import { useSessionStorage } from "@/hooks/use-session-storage"
import { API_BASE } from "@/lib/api"
import { startJob } from "@/lib/jobs"
import { addRecentJob, type RecentJob } from "@/lib/recent-jobs"
import { inferPackageName } from "@/lib/upload-utils"
import { createZipFromFiles } from "@/lib/zip"
import { useUploadStore } from "@/store/upload-store"

const OPENAI_MODELS = [
  { value: "codex-gpt-5.2", label: "codex-gpt-5.2" },
  { value: "codex-gpt-5.1-codex-max", label: "codex-gpt-5.1-codex-max" },
]

const OPENROUTER_MODELS = [
  { value: "openai/gpt-5.2-codex", label: "openai/gpt-5.2-codex" },
  { value: "openai/gpt-5.1-codex-max", label: "openai/gpt-5.1-codex-max" },
  { value: "openai/gpt-5.2", label: "openai/gpt-5.2" },
  { value: "anthropic/claude-opus-4-5", label: "anthropic/claude-opus-4-5" },
  { value: "anthropic/claude-sonnet-4-5", label: "anthropic/claude-sonnet-4-5" },
  { value: "google/gemini-2.5-pro", label: "google/gemini-2.5-pro" },
  { value: "google/gemini-2.5-flash", label: "google/gemini-2.5-flash" },
  { value: "deepseek/deepseek-r1", label: "deepseek/deepseek-r1" },
  { value: "deepseek/deepseek-chat", label: "deepseek/deepseek-chat" },
]

export default function Page() {
  const router = useRouter()
  const { files, packageName, setUpload, clearUpload } = useUploadStore()
  const [apiKey, setApiKey] = useSessionStorage("svmbench.apiKey", "")
  const [provider, setProvider] = useState<"openai" | "openrouter">("openai")
  const [model, setModel] = useState("codex-gpt-5.2")
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [recentJobs, setRecentJobs] = useLocalStorage<RecentJob[]>(
    "svmbench.recentJobs.v1",
    [],
  )
  const {
    isAuthorized,
    isLoading: isAuthLoading,
    isConfigLoading,
    keyPredefined,
  } = useAuth()

  const fileCount = files?.length ?? 0
  const selectedLabel = useMemo(() => {
    if (packageName) return packageName
    if (files) return inferPackageName(files)
    return null
  }, [files, packageName])

  const models = provider === "openrouter" ? OPENROUTER_MODELS : OPENAI_MODELS

  const canSubmit =
    !!files && fileCount > 0 && !isSubmitting && !isAuthLoading && isAuthorized

  const handleFilesSelected = useCallback(
    (selected: File[]) => {
      setUpload(selected, inferPackageName(selected))
    },
    [setUpload],
  )

  const handleKeyChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      setApiKey(event.target.value)
    },
    [setApiKey],
  )

  const handleProviderChange = useCallback(
    (value: "openai" | "openrouter") => {
      setProvider(value)
      // Reset model to first available for new provider
      if (value === "openrouter") {
        setModel(OPENROUTER_MODELS[0].value)
      } else {
        setModel(OPENAI_MODELS[0].value)
      }
    },
    [],
  )

  const handleSubmit = async () => {
    if (!files || fileCount === 0) return
    if (!isAuthorized) {
      setSubmitError("Authorize with GitHub to start analysis.")
      return
    }
    const trimmedKey = apiKey.trim()

    setIsSubmitting(true)
    setSubmitError(null)

    try {
      const name = selectedLabel ?? "files"
      const zipFile = await createZipFromFiles(files, name)
      const response = await startJob(zipFile, model, trimmedKey, provider)
      const next = addRecentJob({
        job_id: response.job_id,
        label: name,
        created_at_ms: Date.now(),
      })
      setRecentJobs(next)
      router.push(`/results?job_id=${response.job_id}`)
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : "Upload failed")
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-screen w-screen flex-col">
      <AppHeader showLogo={false} showBorder={false} />
      <section className="flex flex-1 items-center justify-center px-6 py-12">
        <div className="w-full max-w-4xl">
          <div className="mx-auto grid max-w-sm gap-10 lg:max-w-none lg:grid-cols-5">
            <div className="space-y-6 lg:col-span-3">
              <div>
                <div className="-ms-2 mb-3 flex items-center gap-2">
                  <video
                    autoPlay
                    loop
                    muted
                    playsInline
                    className="size-16 rounded-lg"
                  >
                    <source src="/dance.webm" type="video/webm" />
                  </video>
                </div>
                <h1 className="text-5xl leading-[1.1] font-serif text-foreground mb-1.5">
                  svmbench
                </h1>
                <h2 className="text-2xl leading-[1.1] font-serif text-foreground mb-3">
                  evaluating ai performance on high-severity solana program findings
                </h2>
                <div className="space-y-2 text-base text-foreground/80">
                  <p className="leading-tight">
                    svmbench is an open benchmark that evaluates whether ai
                    agents can detect, patch, and exploit high-severity
                    vulnerabilities in solana programs.
                  </p>
                  <p className="leading-tight">
                    this interface focuses on detection and only reports
                    high-severity findings. upload a program folder, provide an
                    api key, and start a run.
                  </p>
                  <div className="flex flex-col items-start gap-0.5">
                    <a
                      href="https://github.com/neko/svmbench"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-0.5 font-serif leading-tight underline-offset-4 hover:text-foreground hover:underline"
                    >
                      repo
                      <HugeiconsIcon
                        icon={ArrowUpRight01Icon}
                        strokeWidth={2}
                        className="size-3.5"
                      />
                    </a>
                  </div>
                </div>
              </div>
            </div>

            <div className="space-y-6 lg:col-span-2">
              <FileUploader
                onFilesSelected={handleFilesSelected}
                files={files}
                selectedLabel={selectedLabel}
                fileCount={fileCount}
                disabled={isSubmitting}
                onClear={clearUpload}
              />

              <div className="grid gap-3 text-xs text-muted-foreground">
                <div className="grid gap-1">
                  <Label
                    htmlFor="provider-select"
                    className="text-xs text-foreground"
                  >
                    Provider
                  </Label>
                  <Select value={provider} onValueChange={handleProviderChange}>
                    <SelectTrigger id="provider-select" className="w-full">
                      <SelectValue placeholder="Select provider" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="openai">OpenAI</SelectItem>
                      <SelectItem value="openrouter">OpenRouter</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                {!isConfigLoading && !keyPredefined && (
                  <div className="grid gap-1">
                    <Label
                      htmlFor="api-key"
                      className="text-xs text-foreground"
                    >
                      {provider === "openrouter" ? "OpenRouter API Key" : "OpenAI API Key"}
                    </Label>
                    <Input
                      id="api-key"
                      type="password"
                      placeholder={provider === "openrouter" ? "sk-or-&hellip;" : "sk-&hellip;"}
                      value={apiKey}
                      onChange={handleKeyChange}
                    />
                  </div>
                )}
                <div className="grid gap-1">
                  <Label
                    htmlFor="model-select"
                    className="text-xs text-foreground"
                  >
                    Model
                  </Label>
                  <Select value={model} onValueChange={setModel}>
                    <SelectTrigger id="model-select" className="w-full">
                      <SelectValue placeholder="Select model" />
                    </SelectTrigger>
                    <SelectContent>
                      {models.map((m) => (
                        <SelectItem key={m.value} value={m.value}>
                          {m.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                {!isAuthLoading && !isAuthorized && (
                  <span className="text-base font-serif text-muted-foreground">
                    <a
                      href={`${API_BASE}/v1/auth/`}
                      className="text-foreground underline underline-offset-2 hover:text-primary"
                    >
                      Authorize
                    </a>{" "}
                    to start analysis.
                  </span>
                )}
                <Button
                  onClick={handleSubmit}
                  disabled={!canSubmit}
                  className="w-full uppercase"
                >
                  {isSubmitting ? "Uploading…" : "Start analysis"}
                </Button>
                {submitError && (
                  <div className="text-xs text-destructive">{submitError}</div>
                )}

                {recentJobs.length > 0 && (
                  <div className="pt-1">
                    <div className="flex items-baseline justify-between gap-3">
                      <span className="text-xs text-muted-foreground">
                        Recent runs
                      </span>
                      <button
                        type="button"
                        onClick={() => setRecentJobs([])}
                        className="text-xs text-muted-foreground hover:text-foreground"
                      >
                        Clear
                      </button>
                    </div>
                    <div className="mt-2 space-y-1">
                      {recentJobs.slice(0, 6).map((job) => (
                        <button
                          key={job.job_id}
                          type="button"
                          onClick={() =>
                            router.push(`/results?job_id=${job.job_id}`)
                          }
                          className="flex w-full items-center justify-between gap-3 rounded-md px-2 py-1.5 text-left text-xs hover:bg-muted/40"
                          title={job.job_id}
                        >
                          <span className="min-w-0 flex-1 truncate text-foreground">
                            {job.label}
                          </span>
                          <span className="shrink-0 font-mono text-muted-foreground">
                            {job.job_id.slice(0, 8)}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </section>
      <AppFooter showBorder={false} />
    </main>
  )
}
