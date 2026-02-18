import { useCallback, useEffect, useRef, useState } from "react"

export function useLocalStorage<T>(
  key: string,
  fallbackValue: T,
): [T, (value: T) => void] {
  // Important: don't read localStorage during initial render.
  // Next.js will render this component on the server too, and if we render
  // different HTML on the client based on stored values we'll trigger a
  // hydration mismatch warning.
  const fallbackRef = useRef(fallbackValue)
  fallbackRef.current = fallbackValue

  const [value, setValue] = useState<T>(fallbackValue)

  useEffect(() => {
    const stored =
      typeof window === "undefined" ? null : window.localStorage.getItem(key)
    if (stored === null) {
      setValue(fallbackRef.current)
      return
    }
    try {
      setValue(JSON.parse(stored) as T)
    } catch {
      setValue(fallbackRef.current)
    }
  }, [key])

  const setStoredValue = useCallback(
    (nextValue: T) => {
      setValue(nextValue)
      if (typeof window !== "undefined") {
        window.localStorage.setItem(key, JSON.stringify(nextValue))
      }
    },
    [key],
  )

  return [value, setStoredValue]
}
