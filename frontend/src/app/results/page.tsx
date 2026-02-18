import { Suspense } from "react"
import ResultsClient from "./results-client"

export default function ResultsPage() {
  return (
    <Suspense fallback={<div className="h-screen w-screen" />}>
      <ResultsClient />
    </Suspense>
  )
}
