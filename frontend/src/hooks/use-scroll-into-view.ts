import { useEffect, useLayoutEffect, useState } from "react"

const MAX_CONTAINER_ATTEMPTS = 10
const MAX_ELEMENT_ATTEMPTS = 20
const RETRY_DELAY_MS = 50

export function useScrollIntoView<T extends Element>(
  containerRef: React.RefObject<T | null>,
  selector: string | null,
  options: ScrollIntoViewOptions = { behavior: "smooth", block: "center" },
  deps: readonly unknown[] = [],
  offsetRatio?: number,
) {
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (selector === null) {
      setAttempt(0)
      return
    }
    setAttempt(0)
  }, [selector])

  useLayoutEffect(() => {
    if (!selector) {
      if (attempt !== 0) {
        setAttempt(0)
      }
      return
    }

    const container = containerRef.current
    if (!container) {
      if (attempt < MAX_CONTAINER_ATTEMPTS) {
        requestAnimationFrame(() => setAttempt((prev) => prev + 1))
      }
      return
    }

    requestAnimationFrame(() => {
      const el = container.querySelector(selector)
      if (!(el instanceof HTMLElement)) {
        if (attempt < MAX_ELEMENT_ATTEMPTS) {
          setTimeout(() => setAttempt((prev) => prev + 1), RETRY_DELAY_MS)
        }
        return
      }

      if (offsetRatio !== undefined) {
        const scrollParent = findScrollParent(container)
        if (scrollParent) {
          const elRect = el.getBoundingClientRect()
          const parentRect = scrollParent.getBoundingClientRect()
          const offsetFromParentTop = elRect.top - parentRect.top
          const targetScroll =
            scrollParent.scrollTop +
            offsetFromParentTop -
            parentRect.height * offsetRatio

          scrollParent.scrollTo({
            top: Math.max(0, targetScroll),
            behavior: options.behavior ?? "smooth",
          })
        } else {
          el.scrollIntoView(options)
        }
      } else {
        el.scrollIntoView(options)
      }
    })
  }, [selector, containerRef, options, attempt, offsetRatio, ...deps])
}

function findScrollParent(element: Element): Element | null {
  let current: Element | null = element
  while (current) {
    const style = getComputedStyle(current)
    const overflowY = style.overflowY
    if (
      (overflowY === "auto" || overflowY === "scroll") &&
      current.scrollHeight > current.clientHeight
    ) {
      return current
    }
    current = current.parentElement
  }
  return null
}
