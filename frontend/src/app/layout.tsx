import type { Metadata } from "next"
import { Crimson_Pro, Roboto_Mono } from "next/font/google"
import { NuqsAdapter } from "nuqs/adapters/next/app"
import { ThemeProvider } from "@/components/theme-provider"
import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"
import "@/styles/globals.css"

const crimson = Crimson_Pro({
  subsets: ["latin"],
  variable: "--font-crimson-pro",
})

const mono = Roboto_Mono({
  subsets: ["latin"],
  variable: "--font-roboto-mono",
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
      className={cn(mono.variable, crimson.variable, "antialiased")}
      suppressHydrationWarning
    >
      <body
        className={cn(mono.variable, crimson.variable, "font-mono antialiased")}
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
