"use client"

import {
  Alert02Icon,
  CheckmarkCircle02Icon,
  InformationCircleIcon,
  Loading03Icon,
  MultiplicationSignCircleIcon,
} from "@hugeicons/core-free-icons"
import { HugeiconsIcon } from "@hugeicons/react"
import { useTheme } from "next-themes"
import { Toaster as Sonner, type ToasterProps } from "sonner"

const Toaster = ({ ...props }: ToasterProps) => {
  const { theme = "system" } = useTheme()

  return (
    <Sonner
      theme={theme as ToasterProps["theme"]}
      className="toaster group"
      icons={{
        success: (
          <HugeiconsIcon
            icon={CheckmarkCircle02Icon}
            strokeWidth={2}
            className="size-4"
          />
        ),
        info: (
          <HugeiconsIcon
            icon={InformationCircleIcon}
            strokeWidth={2}
            className="size-4"
          />
        ),
        warning: (
          <HugeiconsIcon
            icon={Alert02Icon}
            strokeWidth={2}
            className="size-4"
          />
        ),
        error: (
          <HugeiconsIcon
            icon={MultiplicationSignCircleIcon}
            strokeWidth={2}
            className="size-4"
          />
        ),
        loading: (
          <HugeiconsIcon
            icon={Loading03Icon}
            strokeWidth={2}
            className="size-4 animate-spin"
          />
        ),
      }}
      toastOptions={{
        classNames: {
          toast:
            "!bg-popover !text-popover-foreground !border-border !rounded-md !shadow-md !text-sm !tracking-tight px-3! py-2!",
          title: "!text-foreground !font-medium",
          description: "!text-muted-foreground !text-xs",
          actionButton:
            "!bg-primary !text-primary-foreground !rounded-md !text-xs !font-medium",
          cancelButton:
            "!bg-muted !text-muted-foreground !rounded-md !text-xs !font-medium",
          closeButton:
            "!bg-popover !text-muted-foreground !border-border hover:!bg-muted hover:!text-foreground",
          icon: "!text-muted-foreground",
          success: "!text-severity-low-foreground",
          error: "!text-destructive",
          warning: "!text-severity-medium-foreground",
          info: "!text-muted-foreground",
        },
      }}
      {...props}
    />
  )
}

export { Toaster }
