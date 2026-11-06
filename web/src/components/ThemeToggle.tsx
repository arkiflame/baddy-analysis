"use client";

import { useSyncExternalStore } from "react";
import { Button } from "@/components/ui/button";

// The theme lives on <html class="dark">, set before paint by layout.tsx. This component reads
// that class as an external store (a MutationObserver keeps it in sync) and writes the user's
// choice to localStorage.
function subscribe(onChange: () => void) {
  const obs = new MutationObserver(onChange);
  obs.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });
  return () => obs.disconnect();
}
const getDark = () => document.documentElement.classList.contains("dark");
const getServerDark = () => false;

export function ThemeToggle() {
  const dark = useSyncExternalStore(subscribe, getDark, getServerDark);

  function toggle() {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("theme", next ? "dark" : "light");
    } catch {
      /* private mode: the choice just does not persist */
    }
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={toggle}
      aria-pressed={dark}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      className="border-white/30 bg-white/10 text-white hover:bg-white/20 hover:text-white dark:border-white/30 dark:bg-white/10"
    >
      {dark ? "☀ Light" : "☾ Dark"}
    </Button>
  );
}
