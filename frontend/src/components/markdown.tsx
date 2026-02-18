"use client"

import React, { useEffect, useState } from "react"
import ReactMarkdown, { type Components } from "react-markdown"
import remarkGfm from "remark-gfm"
import { codeToHtml } from "shiki"
import { resolveShikiLanguage, SHIKI_THEMES } from "@/lib/shiki"
import { cn } from "@/lib/utils"

function hasBlockElement(children: React.ReactNode): boolean {
  return React.Children.toArray(children).some((child) => {
    if (!React.isValidElement(child)) return false
    const props = child.props as { "data-markdown-block"?: boolean } | null
    return child.type === "pre" || Boolean(props?.["data-markdown-block"])
  })
}

const CODE_BLOCK_CLASS =
  "my-4 [&_pre]:rounded-md [&_pre]:bg-muted/50 [&_pre]:border [&_pre]:py-2 [&_pre]:px-4 [&_pre]:overflow-x-auto [&_pre]:max-h-[min(68vh,1000px)] [&_pre]:overflow-y-auto [&_pre]:leading-5 [&_code]:font-mono"

function ShikiCode({
  className,
  children,
}: {
  className?: string
  children?: React.ReactNode
}) {
  const [html, setHtml] = useState<string | null>(null)
  const code = String(children).replace(/\n$/, "")
  const match = /language-(\w+)/.exec(className || "")
  const lang = match?.[1] || ""

  const isBlock = !!lang || code.includes("\n")

  useEffect(() => {
    if (!lang) return

    const validLang = resolveShikiLanguage(lang)
    codeToHtml(code, {
      lang: validLang,
      themes: SHIKI_THEMES,
      defaultColor: false,
    })
      .then(setHtml)
      .catch(() => setHtml(null))
  }, [code, lang])

  if (!isBlock) {
    return (
      <code
        data-markdown-inline
        className="bg-muted px-1.5 py-0.25 rounded text-xs text-foreground font-mono border"
      >
        {children}
      </code>
    )
  }

  if (!lang) {
    return (
      <div data-markdown-block className={CODE_BLOCK_CLASS}>
        <pre>
          <code>{code}</code>
        </pre>
      </div>
    )
  }

  if (html) {
    return (
      <div
        data-markdown-block
        className={CODE_BLOCK_CLASS}
        // biome-ignore lint/security/noDangerouslySetInnerHtml: shiki output is trusted
        dangerouslySetInnerHTML={{ __html: html }}
      />
    )
  }

  return (
    <div data-markdown-block className={CODE_BLOCK_CLASS}>
      <pre>
        <code>{code}</code>
      </pre>
    </div>
  )
}

const components: Components = {
  code: ShikiCode as Components["code"],
  pre: ({ children }) => <>{children}</>,
  p: ({ children }) =>
    hasBlockElement(children) ? <div>{children}</div> : <p>{children}</p>,
}

interface MarkdownProps {
  children: string
  className?: string
}

export function Markdown({ children, className }: MarkdownProps) {
  return (
    <div className={cn("prose text-base tracking-tight", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  )
}

function InlineCode({ children }: { children?: React.ReactNode }) {
  return (
    <code className="bg-muted px-1 rounded text-xs text-foreground font-mono border">
      {children}
    </code>
  )
}

const inlineComponents: Components = {
  code: InlineCode as Components["code"],
  p: ({ children }) => <>{children}</>,
  pre: ({ children }) => <>{children}</>,
  // Inline contexts (titles, labels) must never emit block-level tags.
  h1: ({ children }) => <>{children}</>,
  h2: ({ children }) => <>{children}</>,
  h3: ({ children }) => <>{children}</>,
  h4: ({ children }) => <>{children}</>,
  h5: ({ children }) => <>{children}</>,
  h6: ({ children }) => <>{children}</>,
  ul: ({ children }) => <>{children}</>,
  ol: ({ children }) => <>{children}</>,
  li: ({ children }) => <>{children}</>,
}

interface InlineMarkdownProps {
  children: string
  className?: string
}

export function InlineMarkdown({ children, className }: InlineMarkdownProps) {
  return (
    <span
      className={cn("inline text-base font-serif leading-tight", className)}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={inlineComponents}>
        {children}
      </ReactMarkdown>
    </span>
  )
}
