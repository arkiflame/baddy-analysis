import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import { Barlow_Condensed, Inter } from "next/font/google";
import "./globals.css";
import { ThemeToggle } from "@/components/ThemeToggle";

// Inter for body text, Barlow Condensed for the big numbers; both self-hosted by next/font so
// the page makes no request to Google at run time.
const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const barlow = Barlow_Condensed({
  subsets: ["latin"],
  weight: ["600", "700"],
  variable: "--font-barlow",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "Baddy Analysis", template: "%s · Baddy Analysis" },
  description:
    "One-page scouting reports for professional badminton singles players: how to beat them, " +
    "what they do well, their habits and movement, with a real-match video for each pattern.",
};

// Runs before paint so the page never flashes the wrong theme. Stored choice wins; otherwise
// the OS setting.
const themeScript = `(function(){try{var s=localStorage.getItem('theme');var d=s?s==='dark':matchMedia('(prefers-color-scheme: dark)').matches;if(d)document.documentElement.classList.add('dark');}catch(e){}})();`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`h-full antialiased ${inter.variable} ${barlow.variable}`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-full flex flex-col bg-page text-ink">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-yellow focus:px-4 focus:py-3 focus:text-yellow-ink"
        >
          Skip to content
        </a>
        <header className="bg-navy text-navy-ink">
          <nav
            aria-label="Main"
            className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3"
          >
            <Link href="/" className="flex items-center gap-2 py-1">
              <span aria-hidden="true" className="inline-block h-3 w-3 rounded-full bg-yellow" />
              <span className="display text-2xl uppercase tracking-wide">Baddy Analysis</span>
            </Link>
            <div className="flex items-center gap-1 text-sm">
              <Link href="/" className="rounded-md px-3 py-2 text-white/85 hover:bg-white/10 hover:text-white">
                Players
              </Link>
              <Link href="/methods/" className="rounded-md px-3 py-2 text-white/85 hover:bg-white/10 hover:text-white">
                How we check
              </Link>
            </div>
            <div className="ml-auto">
              <ThemeToggle />
            </div>
          </nav>
        </header>
        <main id="main" className="w-full flex-1">
          {children}
        </main>
        <footer className="border-t border-line bg-surface">
          <div className="mx-auto max-w-6xl px-4 py-5 text-sm text-ink-2">
            Data: the ShuttleSet and ShuttleSet22 collections (Wang and colleagues, 2023), published
            free by the{" "}
            <a
              className="text-link underline"
              href="https://github.com/wywyWang/CoachAI-Projects"
            >
              CoachAI research group
            </a>
            . Videos are BWF TV broadcasts on YouTube, linked, never copied. Every number on this site
            was computed once, offline, and the site only shows it; see{" "}
            <Link href="/methods/" className="text-link underline">
              How we check a pattern is real
            </Link>
            .
          </div>
        </footer>
      </body>
    </html>
  );
}
