import Link from "next/link";
import { PlayerSearch } from "@/components/PlayerSearch";
import { readIndex, readPlayer } from "@/lib/data";
import { int, num } from "@/lib/format";
import type { IndexFile, SummaryItem } from "@/lib/types";

// The player whose first takeaway opens the landing page. Falls back to the first player in
// the index with a stable, non-tentative takeaway if this one is missing from the export.
const DEMO_SLUG = "viktor-axelsen";

async function demoTakeaway(idx: IndexFile): Promise<{ slug: string; player: string; item: SummaryItem } | null> {
  const order = [DEMO_SLUG, ...idx.players.map((p) => p.slug).filter((s) => s !== DEMO_SLUG)];
  for (const slug of order) {
    if (!idx.players.some((p) => p.slug === slug)) continue;
    const data = await readPlayer(slug);
    if (data.summary.length) return { slug, player: data.player, item: data.summary[0] };
  }
  return null;
}

const SCHEME_SHORT: Record<string, string> = {
  holdout: "Holdout",
  lomo: "Leave-one-match-out",
  looo: "Leave-one-opponent-out",
};

export default async function Home() {
  const idx = await readIndex();
  const d = idx.dataset;
  const demo = await demoTakeaway(idx);
  const ev = idx.evaluation;
  const byScheme = (s: string) => ev?.totals.find((t) => t.scheme === s);
  const lomo = byScheme("lomo");
  const looo = byScheme("looo");
  const holdout = byScheme("holdout");
  const line = (s: string) => {
    const t = byScheme(s);
    return t
      ? `${SCHEME_SHORT[s]}: ${t.REPLICATES} replicate, ${t["SAME DIRECTION"]} same direction, ${t.FAILS} fail, ${t.UNTESTABLE} untestable`
      : null;
  };

  return (
    <div className="space-y-8">
      <section aria-labelledby="hero" className="space-y-4">
        <h1 id="hero" className="text-2xl font-semibold tracking-tight">
          Scouting reports for professional badminton singles, with the evidence attached
        </h1>
        <p className="max-w-3xl text-ink-2">
          For each of {idx.players.length} players with at least {idx.settings.min_matches} annotated
          matches: how to play against them, what they should fix, their habits and position maps,
          every claim compared with typical pros in the same situation and carrying its sample size
          and 95% interval. Built from {int(d.matches)} professional matches ({int(d.strokes)} strokes)
          in the ShuttleSet and ShuttleSet22 datasets (CoachAI, MIT licence); see{" "}
          <Link href="/methods/" className="text-accent underline">
            Methods
          </Link>{" "}
          for how the numbers are made.
        </p>
        <div className="grid gap-3 md:grid-cols-3">
          {demo && (
            <article className="rounded border border-line bg-surface p-4">
              <h2 className="mb-1 text-sm font-semibold text-ink-2">A scouting takeaway</h2>
              <p>{demo.item.text}</p>
              <p className="mt-2 text-sm">
                <Link href={`/players/${demo.slug}/`} className="text-accent underline">
                  {demo.player}&apos;s report
                </Link>{" "}
                <span className="text-ink-2">has the numbers, the interval and the fold count.</span>
              </p>
            </article>
          )}
          <article className="rounded border border-line bg-surface p-4">
            <h2 className="mb-1 text-sm font-semibold text-ink-2">A negative result</h2>
            <p>
              Expected points from shot and position data has no signal mid-rally in elite singles
              (holdout AUC {num(idx.xp.auc_nonfinal)}, chance is 0.50). The same features reach{" "}
              {num(idx.xp.auc_final)} only on the stroke that ends the rally, which is classifying
              how an already-decisive stroke ends.
            </p>
            <p className="mt-2 text-sm">
              <Link href="/methods/#negative-results" className="text-accent underline">
                Why that matters
              </Link>
            </p>
          </article>
          <article className="rounded border border-line bg-surface p-4">
            <h2 className="mb-1 text-sm font-semibold text-ink-2">Do the insights replicate?</h2>
            {ev && lomo && looo && holdout ? (
              <>
                <p>
                  The top insights of {ev.players.length} players were re-tested on matches they were
                  not found on. {line("lomo")}. {line("looo")}. {line("holdout")}. The holdout has
                  1–3 matches per player, which cannot resolve differences of a few points.
                </p>
                <p className="mt-2 text-sm">
                  <Link href="/methods/#replication" className="text-accent underline">
                    All three schemes, per player
                  </Link>
                </p>
              </>
            ) : (
              <p className="text-ink-2">The replication schemes were not run in this export.</p>
            )}
          </article>
        </div>
      </section>
      <section className="space-y-2">
        <h2 className="text-xl font-semibold tracking-tight">Players</h2>
        <p className="max-w-3xl text-sm text-ink-2">
          {int(d.rallies_known_winner)} rallies with a known winner. Generated {idx.generated}.
        </p>
        <PlayerSearch players={idx.players} />
      </section>
    </div>
  );
}
