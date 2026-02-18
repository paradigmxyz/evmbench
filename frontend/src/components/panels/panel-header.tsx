import { ArrowDown01Icon } from "@hugeicons/core-free-icons"
import { HugeiconsIcon, type IconSvgElement } from "@hugeicons/react"
import { cn } from "@/lib/utils"

interface PanelHeaderProps {
  icon: IconSvgElement
  title: string
  isCollapsed?: boolean
  onToggleCollapse?: () => void
  showCollapseToggle?: boolean
  count?: number
  actions?: React.ReactNode
}

export function PanelHeader({
  icon,
  title,
  isCollapsed = false,
  onToggleCollapse,
  showCollapseToggle = true,
  count,
  actions,
}: PanelHeaderProps) {
  return (
    <div className="flex min-w-0 w-full items-center gap-1 px-3 text-sm">
      {showCollapseToggle && onToggleCollapse && (
        <button
          type="button"
          onClick={onToggleCollapse}
          className="shrink-0 text-muted-foreground hover:text-foreground"
        >
          <HugeiconsIcon
            icon={ArrowDown01Icon}
            strokeWidth={2}
            className={cn(
              "size-3.5 transition-transform",
              isCollapsed && "-rotate-90",
            )}
          />
        </button>
      )}
      <HugeiconsIcon
        icon={icon}
        strokeWidth={2}
        className="size-3.5 shrink-0 text-muted-foreground"
      />
      <span className="truncate">{title}</span>
      {typeof count === "number" && (
        <span className="text-xs text-muted-foreground/50">({count})</span>
      )}
      {actions && (
        <div className="ml-auto flex shrink-0 items-center gap-0.5">
          {actions}
        </div>
      )}
    </div>
  )
}
