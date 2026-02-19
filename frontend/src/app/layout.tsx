import type { Metadata } from "next"
import localFont from "next/font/local"
import { NuqsAdapter } from "nuqs/adapters/next/app"
import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import "@/styles/globals.css"

const fantasque = localFont({
  src: [
    { path: "../fonts/FantasqueSansMono-Regular.woff2", weight: "400", style: "normal" },
    { path: "../fonts/FantasqueSansMono-Italic.woff2", weight: "400", style: "italic" },
    { path: "../fonts/FantasqueSansMono-Bold.woff2", weight: "700", style: "normal" },
    { path: "../fonts/FantasqueSansMono-BoldItalic.woff2", weight: "700", style: "italic" },
  ],
  variable: "--font-fantasque",
})

export const metadata: Metadata = {
  title: "svmbench",
  description: "solana program vulnerability detection",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="en"
      className={cn(fantasque.variable, "antialiased")}
      suppressHydrationWarning
    >
      <body
        className={cn(fantasque.variable, "font-mono antialiased")}
      >
        <NuqsAdapter>
          <ThemeProvider
            attribute="class"
            defaultTheme="dark"
            enableSystem
            disableTransitionOnChange
          >
            <TooltipProvider>
              {children}
              <Toaster />
            </TooltipProvider>
          </ThemeProvider>
        </NuqsAdapter>
      </body>
    </html>
  )
}
