import type { ReactNode } from "react";
import { Badge } from "@/components/Badge";
import { Reveal } from "@/components/ShowNumbers";
import { WatchIt } from "@/components/WatchIt";
import { Card, CardContent } from "@/components/ui/card";
import { freqPair, int, pct, pts, ptsCi } from "@/lib/format";
import type { Insight } from "@/lib/types";

/** The technical layer of one insight, one click away (D30): the exact figures, each with a
 *  one-sentence explanation of the term it uses. */
export function Numbers({ i, me }: { i: Insight; me: string }) {
  const folds = i.folds ?? 0;
  return (
    <div className="space-y-2">
      {i.held_up && <p>{i.held_up}</p>}
      <div className="flex flex-wrap gap-1">
        <Badge>n = {int(i.n)}</Badge>
        <Badge>
          {pct(i.rate)} vs {pct(i.ref_rate)} for typical pros
        </Badge>
        <Badge>
          {pts(i.delta)} points, 95% CI {ptsCi(i.delta_lo, i.delta_hi)}
        </Badge>
        {folds ? (
          <Badge variant={i.selected_folds !== null && i.selected_folds >= folds / 2 ? "good" : "caution"}>
            selected in {i.selected_folds} of {folds} folds
          </Badge>
        ) : (
          <Badge>stability not checked</Badge>
        )}
      </div>
      <dl className="grid gap-x-4 gap-y-1 text-xs text-ink-2 sm:grid-cols-[auto_1fr]">
        <dt className="font-medium">n</dt>
        <dd>how many shots of this kind {me} faced or played in the data.</dd>
        <dt className="font-medium">typical pros</dt>
        <dd>every other player in the data in the same situation; {me} is never part of it.</dd>
        <dt className="font-medium">points</dt>
        <dd>the difference between the two rates, in percentage points.</dd>
        <dt className="font-medium">95% CI</dt>
        <dd>
          the confidence interval: the range the true difference would fall in 19 times out of 20
          if we had new matches. If it includes zero, we do not call it a finding.
        </dd>
        <dt className="font-medium">folds</dt>
        <dd>
          re-checks: we left out one of {me}&apos;s matches at a time and asked whether the pattern
          was still in the top five. Fewer than half means it came and went.
        </dd>
      </dl>
    </div>
  );
}

export function PlainFlags({ flags }: { flags: string[] }) {
  if (!flags.length) return null;
  return (
    <ul className="flex flex-wrap gap-1">
      {flags.map((f) => (
        <li key={f}>
          <Badge variant="warn">{f}</Badge>
        </li>
      ))}
    </ul>
  );
}

/** The "1 in X vs 1 in Y" comparison as two small bars: the player against most pros. The bars
 *  show the two rates the sentence already states (formatting only, D32); the longer bar is the
 *  one who loses the point quickly more often. */
export function RateBars({ i, me }: { i: Insight; me: string }) {
  if (i.ref_rate === null || i.ref_rate === undefined) return null;
  const [mine, theirs] = freqPair(i.rate, i.ref_rate);
  const max = Math.max(i.rate, i.ref_rate, 0.0001);
  const rows: { who: string; v: number; words: string; cls: string }[] = [
    { who: me, v: i.rate, words: mine, cls: "bg-navy dark:bg-yellow" },
    { who: "most pros", v: i.ref_rate, words: theirs, cls: "bg-axis" },
  ];
  return (
    <figure className="w-full max-w-[280px] text-xs" aria-label={`${me} loses the point quickly ${mine}; most pros ${theirs}`}>
      <div className="space-y-1.5">
        {rows.map((r) => (
          <div key={r.who} className="grid grid-cols-[5.5rem_1fr] items-center gap-2">
            <span className="truncate text-ink-2">{r.who}</span>
            <span className="flex items-center gap-2">
              <span
                aria-hidden="true"
                className={`block h-2.5 rounded-full ${r.cls}`}
                style={{ width: `${Math.max(4, (r.v / max) * 100)}%` }}
              />
              <span className="shrink-0 whitespace-nowrap text-ink-2">{r.words.replace(/^about /, "")}</span>
            </span>
          </div>
        ))}
      </div>
      <figcaption className="mt-1 text-[11px] text-ink-2">loses the point quickly</figcaption>
    </figure>
  );
}

/** The headline, evidence, warnings and the two buttons: the body of every card. */
export function InsightBody({ i, me, aside }: { i: Insight; me: string; aside?: ReactNode }) {
  return (
    <>
      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_280px] md:items-start">
        <p className="max-w-[70ch] text-ink-2">{i.evidence}</p>
        <RateBars i={i} me={me} />
      </div>
      {aside}
      <PlainFlags flags={i.flags} />
      <div className="flex flex-wrap items-start gap-2 pt-1">
        <WatchIt examples={i.examples} me={me} />
        <Reveal label="Show the numbers">
          <Numbers i={i} me={me} />
        </Reveal>
      </div>
    </>
  );
}

/** One insight: the coaching takeaway in bold, one plain sentence of evidence with the two
 *  bars, the warnings a reader must not miss, then "Watch it" and "Show the numbers". */
export function InsightCard({
  i,
  me,
  number,
  aside,
}: {
  i: Insight;
  me: string;
  number?: number;
  aside?: ReactNode;
}) {
  return (
    <Card className="shadow-card ring-0 border border-line">
      <CardContent className="space-y-2 text-base">
        <p className="text-lg leading-snug">
          {number !== undefined && <span className="display mr-2 text-xl text-ink-2">{number}</span>}
          <strong>{i.headline}</strong>
        </p>
        <InsightBody i={i} me={me} aside={aside} />
      </CardContent>
    </Card>
  );
}
