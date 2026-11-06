import type { ReactNode } from "react";

type Variant = "neutral" | "warn" | "good" | "caution";

const STYLES: Record<Variant, string> = {
  neutral: "border-line bg-page text-ink-2",
  warn: "border-warn-line bg-warn-bg text-warn-ink",
  good: "border-line bg-page text-ink",
  caution: "border-warn-line bg-warn-bg text-warn-ink",
};

const ICON: Record<Variant, string> = { neutral: "", warn: "⚠ ", good: "✓ ", caution: "↯ " };

/** Small labelled chip. Meaning is carried by the text and icon, never by colour alone. */
export function Badge({ variant = "neutral", children }: { variant?: Variant; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-1.5 py-0.5 text-xs font-medium ${STYLES[variant]}`}
    >
      {ICON[variant]}
      {children}
    </span>
  );
}
