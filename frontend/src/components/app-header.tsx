"use client"

import Link from "next/link"
import { AuthStatus } from "@/components/auth-status"
import { ModeToggle } from "@/components/mode-toggle"
import { cn } from "@/lib/utils"

interface AppHeaderProps {
  left?: React.ReactNode
  center?: React.ReactNode
  right?: React.ReactNode
  showLogo?: boolean
  showBorder?: boolean
  className?: string
}

export function AppHeader({
  left,
  center,
  right,
  showLogo = true,
  showBorder = true,
  className,
}: AppHeaderProps) {
  return (
    <header
      className={cn(
        "grid h-10 shrink-0 sticky inset-0 bg-background z-50 grid-cols-[1fr_auto_1fr] items-center px-3 text-xs",
        showBorder && "border-b",
        className,
      )}
    >
      <div className="flex min-w-0 items-center gap-1">
        {showLogo && (
          <div className="flex shrink-0 items-center gap-1">
            <video
              autoPlay
              loop
              muted
              playsInline
              className="size-7 rounded"
            >
              <source src="/happy.webm" type="video/webm" />
            </video>
          </div>
        )}
        {left}
      </div>
      <div className="flex min-w-0 items-center justify-center overflow-hidden">
        {showLogo ? (
          <Link
            href="/"
            className="hidden min-[350px]:block shrink-0 font-serif text-xl text-foreground"
          >
            svmbench
          </Link>
        ) : (
          center
        )}
      </div>
      <div className="flex shrink-0 items-center justify-end gap-1 sm:gap-3">
        {right}
        <AuthStatus />
        <ModeToggle />
      </div>
    </header>
  )
}
