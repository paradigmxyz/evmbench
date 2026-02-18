"use client"

import { ScrollArea as ScrollAreaPrimitive } from "radix-ui"
import * as React from "react"

import { cn } from "@/lib/utils"

interface ScrollAreaProps
  extends React.ComponentProps<typeof ScrollAreaPrimitive.Root> {
  orientation?: "vertical" | "horizontal" | "both"
  fadeSize?: number
  fadeColor?: string
  fadeOffsets?: {
    top?: number | string
    bottom?: number | string
    left?: number | string
    right?: number | string
  }
  viewportRef?: React.Ref<HTMLDivElement>
}

function ScrollArea({
  className,
  children,
  orientation = "vertical",
  fadeSize = 24,
  fadeColor = "background",
  fadeOffsets = {},
  viewportRef,
  ...props
}: ScrollAreaProps) {
  const internalViewportRef = React.useRef<HTMLDivElement>(null)
  const [showTopFade, setShowTopFade] = React.useState(false)
  const [showBottomFade, setShowBottomFade] = React.useState(false)
  const [showLeftFade, setShowLeftFade] = React.useState(false)
  const [showRightFade, setShowRightFade] = React.useState(false)

  const hasVertical = orientation === "vertical" || orientation === "both"
  const hasHorizontal = orientation === "horizontal" || orientation === "both"

  const topOffset =
    typeof fadeOffsets.top === "number"
      ? `${fadeOffsets.top}px`
      : (fadeOffsets.top ?? "0px")
  const bottomOffset =
    typeof fadeOffsets.bottom === "number"
      ? `${fadeOffsets.bottom}px`
      : (fadeOffsets.bottom ?? "0px")
  const leftOffset =
    typeof fadeOffsets.left === "number"
      ? `${fadeOffsets.left}px`
      : (fadeOffsets.left ?? "0px")
  const rightOffset =
    typeof fadeOffsets.right === "number"
      ? `${fadeOffsets.right}px`
      : (fadeOffsets.right ?? "0px")

  const fadeColorValue =
    fadeColor.startsWith("var(") ||
    fadeColor.startsWith("#") ||
    fadeColor.startsWith("rgb") ||
    fadeColor === "transparent"
      ? fadeColor
      : `var(--${fadeColor})`

  React.useEffect(() => {
    const viewport = internalViewportRef.current
    if (!viewport || fadeSize <= 0) return

    const updateFades = () => {
      const {
        scrollTop,
        scrollHeight,
        clientHeight,
        scrollLeft,
        scrollWidth,
        clientWidth,
      } = viewport
      const threshold = 10

      if (hasVertical) {
        setShowTopFade(scrollTop > threshold)
        setShowBottomFade(scrollTop + clientHeight < scrollHeight - threshold)
      }

      if (hasHorizontal) {
        setShowLeftFade(scrollLeft > threshold)
        setShowRightFade(scrollLeft + clientWidth < scrollWidth - threshold)
      }
    }

    updateFades()

    viewport.addEventListener("scroll", updateFades, { passive: true })
    const resizeObserver = new ResizeObserver(updateFades)
    resizeObserver.observe(viewport)

    return () => {
      viewport.removeEventListener("scroll", updateFades)
      resizeObserver.disconnect()
    }
  }, [fadeSize, hasVertical, hasHorizontal])

  const setViewportRef = React.useCallback(
    (node: HTMLDivElement | null) => {
      internalViewportRef.current = node
      if (!viewportRef) return
      if (typeof viewportRef === "function") {
        viewportRef(node)
      } else {
        viewportRef.current = node
      }
    },
    [viewportRef],
  )

  return (
    <ScrollAreaPrimitive.Root
      data-slot="scroll-area"
      className={cn("relative min-w-0 overflow-hidden", className)}
      {...props}
    >
      <ScrollAreaPrimitive.Viewport
        ref={setViewportRef}
        data-slot="scroll-area-viewport"
        className={cn(
          "focus-visible:ring-ring/50 size-full min-w-0 rounded-[inherit] transition-[color,box-shadow] outline-none focus-visible:ring-[3px] focus-visible:outline-1 [&>div]:block! [&>div]:min-w-0!",
          hasHorizontal && "overscroll-x-none",
          hasVertical && "overscroll-y-none",
        )}
      >
        {children}
      </ScrollAreaPrimitive.Viewport>

      {hasVertical && fadeSize > 0 && (
        <>
          <div
            className={cn(
              "pointer-events-none absolute z-10 transition-opacity",
              showTopFade ? "opacity-100" : "opacity-0",
            )}
            style={{
              top: topOffset,
              left: leftOffset,
              right: rightOffset,
              height: `${fadeSize}px`,
              background: `linear-gradient(to bottom, ${fadeColorValue}, transparent)`,
            }}
            aria-hidden="true"
          />
          <div
            className={cn(
              "pointer-events-none absolute z-10 transition-opacity",
              showBottomFade ? "opacity-100" : "opacity-0",
            )}
            style={{
              bottom: bottomOffset,
              left: leftOffset,
              right: rightOffset,
              height: `${fadeSize}px`,
              background: `linear-gradient(to top, ${fadeColorValue}, transparent)`,
            }}
            aria-hidden="true"
          />
        </>
      )}

      {hasHorizontal && fadeSize > 0 && (
        <>
          <div
            className={cn(
              "pointer-events-none absolute z-10 transition-opacity",
              showLeftFade ? "opacity-100" : "opacity-0",
            )}
            style={{
              left: leftOffset,
              top: topOffset,
              bottom: bottomOffset,
              width: `${fadeSize}px`,
              background: `linear-gradient(to right, ${fadeColorValue}, transparent)`,
            }}
            aria-hidden="true"
          />
          <div
            className={cn(
              "pointer-events-none absolute z-10 transition-opacity",
              showRightFade ? "opacity-100" : "opacity-0",
            )}
            style={{
              right: rightOffset,
              top: topOffset,
              bottom: bottomOffset,
              width: `${fadeSize}px`,
              background: `linear-gradient(to left, ${fadeColorValue}, transparent)`,
            }}
            aria-hidden="true"
          />
        </>
      )}

      {hasVertical && <ScrollBar orientation="vertical" />}
      {hasHorizontal && <ScrollBar orientation="horizontal" />}
      <ScrollAreaPrimitive.Corner />
    </ScrollAreaPrimitive.Root>
  )
}

function ScrollBar({
  className,
  orientation = "vertical",
  ...props
}: React.ComponentProps<typeof ScrollAreaPrimitive.ScrollAreaScrollbar>) {
  return (
    <ScrollAreaPrimitive.ScrollAreaScrollbar
      data-slot="scroll-area-scrollbar"
      data-orientation={orientation}
      orientation={orientation}
      className={cn(
        "z-60 data-horizontal:h-2.5 data-horizontal:flex-col data-horizontal:border-t data-horizontal:border-t-transparent data-vertical:h-full data-vertical:w-2.5 data-vertical:border-l data-vertical:border-l-transparent flex touch-none p-px transition-colors select-none",
        className,
      )}
      {...props}
    >
      <ScrollAreaPrimitive.ScrollAreaThumb
        data-slot="scroll-area-thumb"
        className="rounded-full bg-ring relative flex-1"
      />
    </ScrollAreaPrimitive.ScrollAreaScrollbar>
  )
}

export { ScrollArea, ScrollBar }
