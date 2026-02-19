"use client"

import { cn } from "@/lib/utils"

interface AppFooterProps {
  className?: string
  showBorder?: boolean
}

export function AppFooter({ className, showBorder = true }: AppFooterProps) {
  return (
    <footer
      className={cn(
        "flex shrink-0 flex-col items-center gap-x-2 p-3 text-xs text-muted-foreground sm:flex-row sm:justify-between sm:py-0",
        showBorder ? "sm:h-8 border-t" : "sm:h-10",
        className,
      )}
    >
      <div className="flex flex-wrap items-center justify-center gap-x-3">
        <a
          href="https://x.com/256"
          target="_blank"
          rel="noopener noreferrer"
          className="font-serif text-sm underline underline-offset-2 hover:text-foreground"
        >
          @256
        </a>
      </div>

      <div className="flex items-center gap-2">
        <span className="font-serif text-sm">
          fork of{" "}
          <a
            href="https://github.com/paradigmxyz/evmbench"
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2 hover:text-foreground"
          >
            evmbench
          </a>
        </span>
      </div>
    </footer>
  )
}
