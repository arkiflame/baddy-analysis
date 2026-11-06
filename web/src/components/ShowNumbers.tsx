"use client";

import { useId, useState, type ReactNode } from "react";

/** A disclosure for the technical layer (D30). Everything inside is marked `data-technical`
 *  so the jargon check (scripts/jargon_check.py) knows it is one click away from the main text.
 *  `label` is the closed state ("Show the numbers", "How we know", "Show the tables"). */
export function Reveal({
  label,
  hideLabel,
  children,
  className = "",
}: {
  label: string;
  hideLabel?: string;
  children: ReactNode;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div className={className}>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
        className="rounded border border-line bg-surface px-2.5 py-1 text-sm text-ink-2 hover:text-ink"
      >
        {open ? (hideLabel ?? label.replace(/^Show /, "Hide ")) : label}
      </button>
      <div id={id} hidden={!open} data-technical="" className="mt-2 space-y-2 text-sm">
        {open && children}
      </div>
    </div>
  );
}

/** Kept for the pills: the same disclosure with the original label. */
export function ShowNumbers({ children }: { children: ReactNode }) {
  return <Reveal label="Show the numbers">{children}</Reveal>;
}
