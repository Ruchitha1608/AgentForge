/**
 * layout.tsx — Root layout. Dark background, AgentForge header.
 */

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentForge",
  description: "Multi-agent task orchestration — parallel AI agents, real speedup.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full bg-[#0a0a0a] antialiased">
        {/* Global header */}
        <header className="border-b border-zinc-800 bg-[#0a0a0a] sticky top-0 z-10">
          <div className="mx-auto max-w-4xl px-4 h-12 flex items-center justify-between">
            <span className="text-sm font-semibold text-zinc-100 tracking-tight">
              AgentForge
            </span>
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/health`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 rounded-full bg-green-500/15 border border-green-500/30
                         text-green-400 text-xs px-2.5 py-0.5 hover:bg-green-500/25 transition-colors"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-green-400 inline-block" />
              Live on AWS
            </a>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
