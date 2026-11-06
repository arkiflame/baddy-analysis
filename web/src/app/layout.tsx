import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import "./globals.css";
import { ThemeToggle } from "@/components/ThemeToggle";

export const metadata: Metadata = {
  title: { default: "Badminton scouting reports", template: "%s · Badminton scouting" },
  description:
    "One-page scouting reports for professional badminton singles players: how to beat them, " +
    "what they do well, their habits and movement, with a real-match video for each pattern.",
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
                How we check
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
            Data: the ShuttleSet and ShuttleSet22 collections (Wang and colleagues, 2023), published
            free by the{" "}
            <a
              className="text-accent underline"
              href="https://github.com/wywyWang/CoachAI-Projects"
            >
              CoachAI research group
            </a>
            . Videos are BWF TV broadcasts on YouTube, linked, never copied. Every number on this site
            was computed once, offline, and the site only shows it; see{" "}
            <Link href="/methods/" className="text-accent underline">
              How we check a pattern is real
            </Link>
            .
          </div>
        </footer>
      </body>
    </html>
  );
}
