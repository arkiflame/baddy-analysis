"use client";

import { useId, useState } from "react";
import { RallyCourt } from "@/components/court/RallyCourt";
import type { Example, RallyStroke } from "@/lib/types";

const WINDOW = 4; // shots drawn at once in the step view

/** The rally drawing with controls: by default the last four shots up to and including the
 *  shot the card is about, drawn large; Prev / Next move one shot at a time; "Show whole rally"
 *  draws everything. */
export function RallyViewer({ strokes, me, title }: { strokes: RallyStroke[]; me: string; title: string }) {
  const last = strokes.length ? strokes[strokes.length - 1].no : 0;
  const first = strokes.length ? strokes[0].no : 1;
  const focus = strokes.find((s) => s.highlight)?.no ?? last;
  const [end, setEnd] = useState(focus);
  const [whole, setWhole] = useState(false);
  const start = Math.max(first, end - (WINDOW - 1));
  const range: [number, number] | undefined = whole ? undefined : [start, end];
  const showing = whole ? `All ${strokes.length} shots.` : `Shots ${start} to ${end} of ${last}.`;
  return (
    <div className="space-y-2">
      <RallyCourt strokes={strokes} me={me} title={title} range={range} />
      <div className="flex flex-wrap items-center gap-1 text-sm">
        <span className="mr-1 text-ink-2">{showing}</span>
        {!whole && (
          <>
            <button
              type="button"
              className="rounded border border-line px-2 py-1 disabled:opacity-40"
              onClick={() => setEnd((e) => Math.max(first, e - 1))}
              disabled={end <= first}
            >
              ◀ Prev shot
            </button>
            <button
              type="button"
              className="rounded border border-line px-2 py-1 disabled:opacity-40"
              onClick={() => setEnd((e) => Math.min(last, e + 1))}
              disabled={end >= last}
            >
              Next shot ▶
            </button>
          </>
        )}
        <button
          type="button"
          className="rounded border border-line px-2 py-1"
          aria-pressed={whole}
          onClick={() => {
            setWhole((w) => !w);
            setEnd(focus);
          }}
        >
          {whole ? `Show the last ${WINDOW} shots` : "Show whole rally"}
        </button>
      </div>
    </div>
  );
}

/** "Watch it": a button that opens an embedded YouTube player (youtube-nocookie.com) a few
 *  seconds before an example rally, with the rally's shot sequence drawn next to it (D30).
 *  Nothing loads from YouTube until the reader presses the button. The button is not rendered
 *  when an insight has no example with live footage. */
export function WatchIt({ examples, me }: { examples: Example[]; me: string }) {
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
            <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_280px]">
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
              <RallyViewer
                key={`${ex.match_id}-${ex.stroke_no}`}
                strokes={ex.strokes}
                me={me}
                title={`Shot sequence of the rally: ${ex.label}, game ${ex.game}`}
              />
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
