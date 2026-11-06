import Link from "next/link";
import { PlayerSearch } from "@/components/PlayerSearch";
import { readIndex, readPlayer } from "@/lib/data";
import { int } from "@/lib/format";
import type { IndexFile, SummaryItem } from "@/lib/types";

// The player whose first takeaway opens the landing page. Falls back to the first player in
// the index with a takeaway if this one is missing from the export.
const DEMO_SLUG = "viktor-axelsen";

async function demoTakeaway(
  idx: IndexFile,
): Promise<{ slug: string; player: string; surname: string; item: SummaryItem } | null> {
  const order = [DEMO_SLUG, ...idx.players.map((p) => p.slug).filter((s) => s !== DEMO_SLUG)];
  for (const slug of order) {
    if (!idx.players.some((p) => p.slug === slug)) continue;
    const data = await readPlayer(slug);
    if (data.summary.length) return { slug, player: data.player, surname: data.surname, item: data.summary[0] };
  }
  return null;
}

export default async function Home() {
  const idx = await readIndex();
  const d = idx.dataset;
  const demo = await demoTakeaway(idx);
  const ev = idx.evaluation;
  const lomo = ev?.totals.find((t) => t.scheme === "lomo");
  const lomoTotal = lomo ? lomo.REPLICATES + lomo["SAME DIRECTION"] + lomo.FAILS + lomo.UNTESTABLE : 0;

  return (
    <div className="space-y-10">
      <section aria-labelledby="hero" className="space-y-4">
        <h1 id="hero" className="text-3xl font-semibold tracking-tight">
          Scouting reports for the world&apos;s best badminton singles players
        </h1>
        <div className="max-w-[70ch] space-y-3 text-[17px]">
          <h2 className="text-lg font-semibold">What this is</h2>
          <p className="text-ink-2">
            Pick a player and you get a one-page scouting report: how to beat them, what they do well,
            their habits, where they stand, and a video of each pattern from a real match. Everything comes
            from {int(d.matches)} professional matches in which people wrote down every shot (
            {int(d.strokes)} shots). Every card compares the player with most pros in the same situation
            and says how sure we are. The data is the ShuttleSet and ShuttleSet22 collections from the
            CoachAI research group, published free.{" "}
            <Link href="/methods/" className="text-accent underline">
              How we check a pattern is real
            </Link>
            .
          </p>
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          {demo && (
            <article className="rounded border border-line bg-surface p-4">
              <h2 className="mb-1 text-sm font-semibold text-ink-2">One takeaway</h2>
              <p>
                <strong>{demo.item.insight.headline}</strong>
              </p>
              <p className="mt-1 text-ink-2">{demo.item.insight.evidence}</p>
              <p className="mt-2 text-sm">
                <Link href={`/players/${demo.slug}/`} className="text-accent underline">
                  {demo.player}&apos;s report
                </Link>
              </p>
            </article>
          )}
          <article className="rounded border border-line bg-surface p-4">
            <h2 className="mb-1 text-sm font-semibold text-ink-2">What did not work</h2>
            <p>
              We tried to predict who wins a rally while it is still going, from the shots and where both
              players stood. The model was no better than a coin flip. We say so instead of hiding it.
            </p>
            <p className="mt-2 text-sm">
              <Link href="/methods/#negative-results" className="text-accent underline">
                Why that matters
              </Link>
            </p>
          </article>
          <article className="rounded border border-line bg-surface p-4">
            <h2 className="mb-1 text-sm font-semibold text-ink-2">Do the findings hold up?</h2>
            {ev && lomo ? (
              <p>
                For the {ev.players.length} players with the most matches, we re-tested every top finding on
                matches it was not found on. {lomo.REPLICATES} of {lomoTotal} held up fully and{" "}
                {lomo["SAME DIRECTION"]} more pointed the same way; {lomo.FAILS} went the other way.
              </p>
            ) : (
              <p className="text-ink-2">The re-tests were not run in this export.</p>
            )}
            <p className="mt-2 text-sm">
              <Link href="/methods/#replication" className="text-accent underline">
                All three ways of testing
              </Link>
            </p>
          </article>
        </div>
      </section>
      <section className="space-y-2">
        <h2 className="text-xl font-semibold tracking-tight">Players</h2>
        <p className="max-w-[70ch] text-sm text-ink-2">
          {idx.players.length} players with at least {idx.settings.min_matches} matches in the data. Video is
          available for {idx.footage.live} of the {d.matches} matches.
        </p>
        <PlayerSearch players={idx.players} />
      </section>
    </div>
  );
}
