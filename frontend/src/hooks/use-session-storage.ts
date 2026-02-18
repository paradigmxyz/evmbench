import { useCallback, useState } from "react"

export function useSessionStorage(key: string, fallbackValue: string) {
  const [value, setValue] = useState(() => {
    if (typeof window === "undefined") return fallbackValue
    return window.sessionStorage.getItem(key) ?? fallbackValue
  })

  const setStoredValue = useCallback(
    (nextValue: string) => {
      setValue(nextValue)
      if (typeof window !== "undefined") {
        window.sessionStorage.setItem(key, nextValue)
      }
    },
    [key],
  )

  return [value, setStoredValue] as const
}
