"use client";

import { useId, useState, type ReactNode } from "react";

/** Plain language first: the n / interval / difference pills for one item sit behind this
 *  toggle, one click away. The same numbers stay in the evidence tables. */
export function ShowNumbers({ children, label = "numbers" }: { children: ReactNode; label?: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <div className="text-xs">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((o) => !o)}
        className="rounded border border-line bg-surface px-2 py-1 text-xs font-medium text-ink-2 hover:bg-page"
      >
        {open ? `Hide the ${label}` : `Show the ${label}`}
      </button>
      <div id={id} hidden={!open} className="mt-1 flex flex-wrap gap-1">
        {children}
      </div>
    </div>
  );
}
