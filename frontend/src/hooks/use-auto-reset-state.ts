import { useEffect, useState } from "react"

export function useAutoResetState<T>(
  initialValue: T,
  resetMs: number,
): [T, (value: T) => void] {
  const [value, setValue] = useState<T>(initialValue)

  useEffect(() => {
    if (Object.is(value, initialValue)) return
    const timer = window.setTimeout(() => {
      setValue(initialValue)
    }, resetMs)
    return () => window.clearTimeout(timer)
  }, [value, initialValue, resetMs])

  return [value, setValue]
}
