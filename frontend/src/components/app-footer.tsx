"use client"

import Image from "next/image"
import { cn } from "@/lib/utils"
import osecLogo from "../../public/osec.svg"

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
        <span className="font-serif text-sm">
          &copy; {new Date().getFullYear()} All rights reserved.
        </span>
      </div>

      <div className="flex items-center gap-2">
        <span className="font-serif text-sm">Built in collaboration with</span>
        <a
          href="https://osec.io"
          target="_blank"
          rel="noopener noreferrer"
          className="opacity-50 transition-opacity hover:opacity-100"
        >
          <Image
            src={osecLogo}
            alt="OtterSec"
            className="h-4.5 w-auto dark:invert"
          />
        </a>
      </div>
    </footer>
  )
}
