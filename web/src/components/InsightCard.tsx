import type { ReactNode } from "react";
import { Badge } from "@/components/Badge";
import { Reveal } from "@/components/ShowNumbers";
import { WatchIt } from "@/components/WatchIt";
import { int, pct, pts, ptsCi } from "@/lib/format";
import type { Insight, RallyStroke } from "@/lib/types";

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

/** One insight: the coaching takeaway in bold, one plain sentence of evidence, the warnings a
 *  reader must not miss, then "Watch it" and "Show the numbers" one click away. */
export function InsightCard({
  i,
  me,
  renderRally,
  number,
  aside,
}: {
  i: Insight;
  me: string;
  renderRally: (strokes: RallyStroke[], title: string) => ReactNode;
  number?: number;
  aside?: ReactNode;
}) {
  return (
    <article className="space-y-2 rounded border border-line bg-surface p-4">
      <p className="text-base leading-snug">
        {number !== undefined && <span className="mr-2 text-ink-2">{number}.</span>}
        <strong>{i.headline}</strong>
      </p>
      <p className="max-w-[70ch] text-ink-2">{i.evidence}</p>
      {aside}
      <PlainFlags flags={i.flags} />
      <div className="flex flex-wrap items-start gap-2 pt-1">
        <WatchIt examples={i.examples} me={me} renderRally={renderRally} />
        <Reveal label="Show the numbers">
          <Numbers i={i} me={me} />
        </Reveal>
      </div>
    </article>
  );
}
