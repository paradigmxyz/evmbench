import models from "@/data/models.json"

const reasoningLabels: Record<string, string> = {
  low: "Low",
  medium: "Medium",
  high: "High",
  xhigh: "Extra high",
  max: "Max",
}

export function getReasoningEfforts(model: string): string[] {
  return models.find(({ id }) => id === model)?.reasoningEfforts ?? []
}

export function reasoningLabel(effort?: string | null): string {
  return effort ? (reasoningLabels[effort] ?? effort) : "Model default"
}
