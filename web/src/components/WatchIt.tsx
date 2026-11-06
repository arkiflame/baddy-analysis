"use client";

import { useId, useState, type ReactNode } from "react";
import type { Example, RallyStroke } from "@/lib/types";

/** "Watch it": a button that opens an embedded YouTube player (youtube-nocookie.com) a few
 *  seconds before an example rally, with the rally's shot sequence drawn next to it (D30).
 *  Nothing loads from YouTube until the reader presses the button. The button is not rendered
 *  when an insight has no example with live footage. */
export function WatchIt({
  examples,
  me,
  renderRally,
}: {
  examples: Example[];
  me: string;
  renderRally: (strokes: RallyStroke[], title: string) => ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [idx, setIdx] = useState(0);
  const id = useId();
  if (!examples.length) return null;
  const ex = examples[Math.min(idx, examples.length - 1)];
  const outcome = ex.outcome === "lost" ? `${me} lost the point` : `${me} won the point`;
  return (
    <div>
      <button
        type="button"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
        className="rounded border border-accent bg-surface px-2.5 py-1 text-sm font-medium text-accent hover:bg-page"
      >
        {open ? "Hide the video" : `▶ Watch it${examples.length > 1 ? ` (${examples.length} rallies)` : ""}`}
      </button>
      <div id={id} hidden={!open} className="mt-3 space-y-3 rounded border border-line bg-page p-3">
        {open && (
          <>
            {examples.length > 1 && (
              <div className="flex flex-wrap gap-1" role="group" aria-label="Example rallies">
                {examples.map((e, i) => (
                  <button
                    key={`${e.match_id}-${e.stroke_no}`}
                    type="button"
                    aria-pressed={i === idx}
                    onClick={() => setIdx(i)}
                    className={`rounded border px-2 py-1 text-xs ${
                      i === idx ? "border-accent font-medium text-ink" : "border-line text-ink-2"
                    }`}
                  >
                    Rally {i + 1}
                  </button>
                ))}
              </div>
            )}
            <p className="text-sm">
              <span className="font-medium">{ex.label}</span>, game {ex.game}
              {ex.rally_no ? `, rally ${ex.rally_no}` : ""}. {outcome}
              {ex.ends_in <= 2 ? " within two shots." : "."}
            </p>
            <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_260px]">
              <div className="aspect-video w-full overflow-hidden rounded bg-black">
                <iframe
                  key={ex.embed}
                  src={ex.embed}
                  title={`${ex.label}: the rally this card is about`}
                  className="h-full w-full"
                  loading="lazy"
                  allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                  referrerPolicy="strict-origin-when-cross-origin"
                  allowFullScreen
                />
              </div>
              <div>{renderRally(ex.strokes, `Shot sequence of the rally: ${ex.label}, game ${ex.game}`)}</div>
            </div>
            <p className="text-xs text-ink-2">
              The clip starts a few seconds before the shot. Broadcast timings can be a little
              off; if the rally has passed, scrub back a few seconds.{" "}
              <a className="text-accent underline" href={ex.watch} target="_blank" rel="noreferrer">
                Open on YouTube at this moment
              </a>
              . Footage is BWF TV&apos;s; nothing is stored here.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
