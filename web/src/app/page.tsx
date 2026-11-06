import Link from "next/link";
import { PlayerSearch } from "@/components/PlayerSearch";
import { Card, CardContent } from "@/components/ui/card";
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
    <div>
      {/* Hero band: site name, one-line pitch, the search front and centre; the grid below. */}
      <PlayerSearch
        players={idx.players}
        hero={
          <>
            <p className="mb-2 text-sm font-semibold uppercase tracking-[0.2em] text-yellow">Scouting reports</p>
            <h1 id="hero" className="display text-5xl uppercase tracking-wide md:text-7xl">
              Baddy Analysis
            </h1>
            <p className="mx-auto mt-3 max-w-[60ch] text-lg text-white/85">
              How to beat the world&apos;s best badminton singles players, with a real-match video for
              every pattern.
            </p>
          </>
        }
      />

      <div className="mx-auto max-w-6xl space-y-10 px-4 py-10">
        <section className="space-y-3">
          <h2 className="text-xl font-semibold">What this is</h2>
          <p className="max-w-[70ch] text-ink-2">
            Pick a player and you get a one-page scouting report: how to beat them, what they do well,
            their habits, where they stand, and a video of each pattern from a real match. Everything comes
            from {int(d.matches)} professional matches in which people wrote down every shot (
            {int(d.strokes)} shots). Every card compares the player with most pros in the same situation
            and says how sure we are. The data is the ShuttleSet and ShuttleSet22 collections from the
            CoachAI research group, published free.{" "}
            <Link href="/methods/" className="text-link underline">
              How we check a pattern is real
            </Link>
            .
          </p>
          <p className="max-w-[70ch] text-sm text-ink-2">
            {idx.players.length} players with at least {idx.settings.min_matches} matches in the data. Video is
            available for {idx.footage.live} of the {d.matches} matches.
          </p>
        </section>

        <section aria-labelledby="takeaways" className="space-y-3">
          <h2 id="takeaways" className="text-xl font-semibold">
            Three things to know
          </h2>
          <div className="grid gap-4 md:grid-cols-3">
            {demo && (
              <Card className="shadow-card ring-0 border border-line border-t-4 border-t-yellow">
                <CardContent className="space-y-2 text-base">
                  <p className="text-xs font-semibold uppercase tracking-wider text-ink-2">One takeaway</p>
                  <p className="text-lg">
                    <strong>{demo.item.insight.headline}</strong>
                  </p>
                  <p className="text-ink-2">{demo.item.insight.evidence}</p>
                  <p className="text-sm">
                    <Link href={`/players/${demo.slug}/`} className="text-link underline">
                      {demo.player}&apos;s report
                    </Link>
                  </p>
                </CardContent>
              </Card>
            )}
            <Card className="shadow-card ring-0 border border-line border-t-4 border-t-navy dark:border-t-link">
              <CardContent className="space-y-2 text-base">
                <p className="text-xs font-semibold uppercase tracking-wider text-ink-2">What did not work</p>
                <p>
                  We tried to predict who wins a rally while it is still going, from the shots and where both
                  players stood. The model was no better than a coin flip. We say so instead of hiding it.
                </p>
                <p className="text-sm">
                  <Link href="/methods/#negative-results" className="text-link underline">
                    Why that matters
                  </Link>
                </p>
              </CardContent>
            </Card>
            <Card className="shadow-card ring-0 border border-line border-t-4 border-t-green">
              <CardContent className="space-y-2 text-base">
                <p className="text-xs font-semibold uppercase tracking-wider text-ink-2">Do the findings hold up?</p>
                {ev && lomo ? (
                  <p>
                    For the {ev.players.length} players with the most matches, we re-tested every top finding on
                    matches it was not found on.{" "}
                    <span className="display text-3xl text-green">{lomo.REPLICATES}</span> of {lomoTotal} held up
                    fully and {lomo["SAME DIRECTION"]} more pointed the same way; {lomo.FAILS} went the other way.
                  </p>
                ) : (
                  <p className="text-ink-2">The re-tests were not run in this export.</p>
                )}
                <p className="text-sm">
                  <Link href="/methods/#replication" className="text-link underline">
                    All three ways of testing
                  </Link>
                </p>
              </CardContent>
            </Card>
          </div>
        </section>
      </div>
    </div>
  );
}
