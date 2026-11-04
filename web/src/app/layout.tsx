import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import "./globals.css";
import { ThemeToggle } from "@/components/ThemeToggle";

export const metadata: Metadata = {
  title: { default: "Badminton scouting reports", template: "%s · Badminton scouting" },
  description:
    "Scouting reports for professional singles players built from ShuttleSet stroke data: " +
    "how to play against a player, what they should fix, habits, position maps, and the " +
    "evidence behind every claim.",
};

// Runs before paint so the page never flashes the wrong theme. Stored choice wins; otherwise
// the OS setting.
const themeScript = `(function(){try{var s=localStorage.getItem('theme');var d=s?s==='dark':matchMedia('(prefers-color-scheme: dark)').matches;if(d)document.documentElement.classList.add('dark');}catch(e){}})();`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="h-full antialiased" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-full flex flex-col bg-page text-ink">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-accent focus:px-4 focus:py-3 focus:text-accent-ink"
        >
          Skip to content
        </a>
        <header className="border-b border-line bg-surface">
          <nav
            aria-label="Main"
            className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3"
          >
            <Link href="/" className="py-2 text-lg font-semibold tracking-tight">
              Badminton scouting
            </Link>
            <div className="flex items-center gap-2 text-sm">
              <Link href="/" className="px-2 py-2 hover:underline">
                Players
              </Link>
              <Link href="/methods/" className="px-2 py-2 hover:underline">
                Methods
              </Link>
            </div>
            <div className="ml-auto">
              <ThemeToggle />
            </div>
          </nav>
        </header>
        <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-6">
          {children}
        </main>
        <footer className="border-t border-line bg-surface">
          <div className="mx-auto max-w-6xl px-4 py-4 text-sm text-ink-2">
            Data: ShuttleSet (Wang et al., KDD 2023) and ShuttleSet22 (Wang, Du, Peng, IT4PSS
            2023), from the MIT-licensed{" "}
            <a
              className="text-accent underline"
              href="https://github.com/wywyWang/CoachAI-Projects"
            >
              CoachAI-Projects
            </a>{" "}
            repository. Every number on this site comes from{" "}
            <code className="text-xs">scripts/export_web.py</code>; see{" "}
            <Link href="/methods/" className="text-accent underline">
              Methods
            </Link>
            .
          </div>
        </footer>
      </body>
    </html>
  );
}
