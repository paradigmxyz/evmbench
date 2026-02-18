"use client"

import { Moon02Icon, Sun02Icon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { useTheme } from "next-themes"
import { useEffect, useState } from "react"
import { cn } from "@/lib/utils"

export function ModeToggle() {
  const { setTheme, resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return <div className="flex h-6 w-12 items-center" />
  }

  const isLight = resolvedTheme === "light"

  return (
    <div className="relative flex items-center rounded-full bg-muted p-0.5">
      <div
        className={cn(
          "absolute size-6 rounded-full bg-background shadow-sm",
          isLight ? "translate-x-0" : "translate-x-6",
        )}
      />
      <button
        type="button"
        onClick={() => setTheme("light")}
        className={cn(
          "relative z-10 flex size-6 items-center justify-center rounded-full",
          isLight ? "text-foreground" : "text-muted-foreground",
        )}
        aria-label="Light mode"
      >
        <HugeiconsIcon icon={Sun02Icon} strokeWidth={2} className="size-3.5" />
      </button>
      <button
        type="button"
        onClick={() => setTheme("dark")}
        className={cn(
          "relative z-10 flex size-6 items-center justify-center rounded-full",
          !isLight ? "text-foreground" : "text-muted-foreground",
        )}
        aria-label="Dark mode"
      >
        <HugeiconsIcon icon={Moon02Icon} strokeWidth={2} className="size-3.5" />
      </button>
    </div>
  )
}
