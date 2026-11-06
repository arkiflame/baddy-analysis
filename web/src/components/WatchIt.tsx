"use client";

import { useId, useState } from "react";
import { RallyCourt } from "@/components/court/RallyCourt";
import { Button } from "@/components/ui/button";
import type { Example, RallyStroke } from "@/lib/types";

const WINDOW = 4; // shots drawn at once in the step view

/** The rally drawing with controls: by default the last four shots up to and including the
 *  shot the card is about, drawn large; Prev / Next move one shot at a time; "Show whole rally"
 *  draws everything. */
export function RallyViewer({ strokes, me, title }: { strokes: RallyStroke[]; me: string; title: string }) {
  const last = strokes.length ? strokes[strokes.length - 1].no : 0;
  const first = strokes.length ? strokes[0].no : 1;
  const focus = strokes.find((s) => s.highlight)?.no ?? last;
  // the key shot and the three before it; plus the shot after it when that one ended the rally
  const initialEnd = focus + 1 === last ? last : focus;
  const [end, setEnd] = useState(initialEnd);
  const [whole, setWhole] = useState(false);
  const start = Math.max(first, Math.min(end, focus) - (WINDOW - 1));
  const range: [number, number] | undefined = whole ? undefined : [start, end];
  const showing = whole ? `All ${strokes.length} shots.` : `Shots ${start} to ${end} of ${last}.`;
  return (
    <div className="space-y-2">
      <RallyCourt strokes={strokes} me={me} title={title} range={range} />
      <div className="flex flex-wrap items-center gap-1.5 text-sm">
        <span className="mr-1 text-ink-2">{showing}</span>
        {!whole && (
          <>
            <Button variant="outline" size="sm" onClick={() => setEnd((e) => Math.max(first, e - 1))} disabled={end <= first}>
              ◀ Prev shot
            </Button>
            <Button variant="outline" size="sm" onClick={() => setEnd((e) => Math.min(last, e + 1))} disabled={end >= last}>
              Next shot ▶
            </Button>
          </>
        )}
        <Button
          variant="secondary"
          size="sm"
          aria-pressed={whole}
          onClick={() => {
            setWhole((w) => !w);
            setEnd(initialEnd);
          }}
        >
          {whole ? `Show the last ${WINDOW} shots` : "Show whole rally"}
        </Button>
      </div>
    </div>
  );
}

/** "Watch it": a button that opens an embedded YouTube player (youtube-nocookie.com) a few
 *  seconds before an example rally, with the rally's shot sequence drawn beside it (D30).
 *  Nothing loads from YouTube until the reader presses the button. The button is not rendered
 *  when an insight has no example with live footage. The panel takes the full width of the
 *  card (`basis-full` inside the card's wrapping button row): video and court side by side
 *  from 768 px up, stacked on phones. */
export function WatchIt({ examples, me }: { examples: Example[]; me: string }) {
  const [open, setOpen] = useState(false);
  const [idx, setIdx] = useState(0);
  const id = useId();
  if (!examples.length) return null;
  const ex = examples[Math.min(idx, examples.length - 1)];
  const outcome = ex.outcome === "lost" ? `${me} lost the point` : `${me} won the point`;
  return (
    <>
      <Button
        variant={open ? "outline" : "default"}
        size="sm"
        aria-expanded={open}
        aria-controls={id}
        onClick={() => setOpen((v) => !v)}
      >
        {open ? "Hide the video" : `▶ Watch it${examples.length > 1 ? ` (${examples.length} rallies)` : ""}`}
      </Button>
      <div
        id={id}
        hidden={!open}
        className="basis-full space-y-3 rounded-lg border border-line bg-page p-3 md:p-4"
      >
        {open && (
          <>
            <div className="flex flex-wrap items-center gap-2">
              {examples.length > 1 && (
                <div className="flex flex-wrap gap-1" role="group" aria-label="Example rallies">
                  {examples.map((e, i) => (
                    <Button
                      key={`${e.match_id}-${e.stroke_no}`}
                      variant={i === idx ? "default" : "outline"}
                      size="xs"
                      aria-pressed={i === idx}
                      onClick={() => setIdx(i)}
                    >
                      Rally {i + 1}
                    </Button>
                  ))}
                </div>
              )}
              <p className="text-sm">
                <span className="font-medium">{ex.label}</span>, game {ex.game}
                {ex.rally_no ? `, rally ${ex.rally_no}` : ""}. {outcome}
                {ex.ends_in <= 2 ? " within two shots." : "."}
              </p>
            </div>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="aspect-video w-full overflow-hidden rounded-lg bg-black">
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
              <a className="text-link underline" href={ex.watch} target="_blank" rel="noreferrer">
                Open on YouTube at this moment
              </a>
              . Footage is BWF TV&apos;s; nothing is stored here.
            </p>
          </>
        )}
      </div>
    </>
  );
}
