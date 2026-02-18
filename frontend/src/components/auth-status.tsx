"use client"

import { Logout01Icon, WorkHistoryIcon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import Image from "next/image"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { useAuth } from "@/hooks/use-auth"
import { API_BASE } from "@/lib/api"
import { cn } from "@/lib/utils"

interface AuthStatusProps {
  className?: string
}

export function AuthStatus({ className }: AuthStatusProps) {
  const { user, isLoading, isAuthEnabled } = useAuth()

  if (isLoading || !isAuthEnabled) return null

  if (!user) {
    return (
      <div className={cn("flex items-center gap-2 text-xs", className)}>
        <span className="hidden font-serif text-base text-muted-foreground sm:inline">
          Authorization required
        </span>
        <Button asChild size="sm" variant="outline">
          <a href={`${API_BASE}/v1/auth/`}>Authorize</a>
        </Button>
      </div>
    )
  }

  const avatar = user.avatar_url ? (
    <Image
      src={user.avatar_url}
      alt={`${user.username} avatar`}
      width={24}
      height={24}
      className="size-6 rounded-full object-cover"
      referrerPolicy="no-referrer"
      unoptimized
    />
  ) : (
    <div className="flex size-6 items-center justify-center rounded-full bg-muted text-xs uppercase">
      {user.username.slice(0, 1)}
    </div>
  )

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className={cn(
            "flex shrink-0 items-center gap-1.5 rounded-md px-1.5 py-0.5 text-xs text-foreground hover:bg-muted/40",
            className,
          )}
        >
          {avatar}
          <span className="hidden max-w-32 truncate sm:inline">
            {user.username}
          </span>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem asChild>
          <Link href="/history" className="flex items-center gap-2">
            <HugeiconsIcon icon={WorkHistoryIcon} strokeWidth={2} />
            History
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem asChild>
          <a
            href={`${API_BASE}/v1/auth/logout`}
            className="flex items-center gap-2"
          >
            <HugeiconsIcon icon={Logout01Icon} strokeWidth={2} />
            Log out
          </a>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
