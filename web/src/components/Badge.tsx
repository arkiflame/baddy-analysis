import type { ReactNode } from "react";
import { Badge as UiBadge } from "@/components/ui/badge";

type Variant = "neutral" | "warn" | "good" | "caution";

const STYLES: Record<Variant, string> = {
  neutral: "border-line bg-muted text-ink-2",
  warn: "border-warn-line bg-warn-bg text-warn-ink",
  good: "border-green-soft bg-green-soft text-green-soft-ink",
  caution: "border-warn-line bg-warn-bg text-warn-ink",
};

const ICON: Record<Variant, string> = { neutral: "", warn: "⚠ ", good: "✓ ", caution: "↯ " };

/** Small labelled chip on the shadcn badge. Meaning is carried by the text and icon, never by
 *  colour alone. Long warnings are allowed to wrap. */
export function Badge({ variant = "neutral", children }: { variant?: Variant; children: ReactNode }) {
  return (
    <UiBadge
      variant="outline"
      className={`h-auto whitespace-normal rounded-md px-2 py-0.5 text-xs font-medium ${STYLES[variant]}`}
    >
      {ICON[variant]}
      {children}
    </UiBadge>
  );
}
