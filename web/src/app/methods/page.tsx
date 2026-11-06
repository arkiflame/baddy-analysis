import type { Metadata } from "next";
import { readIndex } from "@/lib/data";
import { int, num, pct } from "@/lib/format";

export const metadata: Metadata = {
  title: "Methods",
  description:
    "Where the data comes from, what 'vs typical pros' means, how intervals and replication work, and the negative results.",
};

const SCHEME: Record<string, string> = {
  holdout: "holdout (ShuttleSet22's own validation and test matches, 1–3 per player)",
  lomo: "leave-one-match-out",
  looo: "leave-one-opponent-out",
};

export default async function Methods() {
  const idx = await readIndex();
  const d = idx.dataset;
  const st = idx.settings.stability;
  const ev = idx.evaluation;
  const xpMetrics = idx.xp.metrics.filter((m) => m.feature_set === "pre" && m.model === idx.xp.chosen.pre);

  return (
    <article className="max-w-3xl space-y-8 text-[15px] leading-relaxed">
      <h1 className="text-2xl font-semibold tracking-tight">Methods, in plain language</h1>

      <section id="data" className="scroll-mt-4 space-y-2">
        <h2 className="text-lg font-semibold">Where the data comes from</h2>
        <p>
          Every stroke on this site comes from <strong>ShuttleSet</strong> (Wang, Huang, Ik, Peng:
          &ldquo;ShuttleSet: A Human-Annotated Stroke-Level Singles Dataset for Badminton Tactical
          Analysis&rdquo;, KDD 2023) and <strong>ShuttleSet22</strong> (Wang, Du, Peng, IT4PSS at
          IJCAI 2023), published in the MIT-licensed{" "}
          <a className="text-accent underline" href="https://github.com/wywyWang/CoachAI-Projects">
            CoachAI-Projects
          </a>{" "}
          repository. Human annotators labelled each stroke&apos;s type, the hitter&apos;s and
          receiver&apos;s feet positions at the moment of the hit, where the shuttle landed, and how
          each rally ended. After removing matches that appear in both sets, this export used{" "}
          {int(d.matches)} matches, {int(d.strokes)} strokes and {int(d.rallies_known_winner)} rallies
          with a known winner, covering {d.players} players; players with at least{" "}
          {idx.settings.min_matches} matches get a page. No video was used.
        </p>
      </section>

      <section id="typical-pros" className="scroll-mt-4 space-y-2">
        <h2 className="text-lg font-semibold">What &ldquo;vs typical pros&rdquo; means</h2>
        <p>
          A rate on its own (&ldquo;loses 23% of points after smashes&rdquo;) is usually true of every
          player, so every rate is compared with the same situation over <em>all other players in the
          dataset</em>: the same shot type landing in the same zone, from the receiver&apos;s point of
          view, with the zones (front / mid / rear, forehand / backhand side, body) defined by each
          receiver&apos;s own racket hand. The player is never part of their own reference. The report
          ranks by the difference from typical pros, not by the player&apos;s own average. The reference
          pools men&apos;s and women&apos;s singles and players with one or two matches; it is a
          reference, not a ranking of peers.
        </p>
      </section>

      <section id="intervals" className="scroll-mt-4 space-y-2">
        <h2 className="text-lg font-semibold">Sample sizes and intervals</h2>
        <p>
          Every rate shows its n and a 95% Wilson interval. Every difference from typical pros shows
          Newcombe&apos;s 95% interval on the difference of two proportions. A row needs at least{" "}
          {idx.settings.min_n} strokes on both sides before it can be ranked, and it is only a finding
          when the interval on the difference excludes zero. Means (distances, expected points) use
          t-intervals and Welch intervals, computed over rallies where strokes in a rally share an
          outcome.
        </p>
      </section>

      <section id="stability" className="scroll-mt-4 space-y-2">
        <h2 className="text-lg font-semibold">Stability and the &ldquo;tentative&rdquo; flag</h2>
        <p>
          Screening hundreds of patterns and keeping the extremes inflates them. Two guards: the
          ranking uses the interval bound nearest zero (the smallest difference the data still
          supports), and the top-{idx.settings.top_k} is re-selected once per match of the player with
          that match left out. A pattern is ranked only if it is selected in at least{" "}
          {pct(st.min_share)} of those folds (shown as &ldquo;stable in X of N folds&rdquo;); the rest
          are listed as <em>less stable</em>. Any ranked insight whose interval on the difference is
          wider than {Math.round(st.tentative_ci_width * 100)} points, or whose n is under{" "}
          {st.tentative_min_n}, is marked <em>tentative</em>.
        </p>
      </section>

      <section id="replication" className="scroll-mt-4 space-y-2">
        <h2 className="text-lg font-semibold">Replication: do the insights hold on matches they were not found on?</h2>
        {ev ? (
          <>
            <p>
              For {ev.players.length} players ({ev.players.join(", ")}) the top-{idx.settings.top_k} was
              re-selected on part of the data and each insight re-measured on the rest, under three
              schemes. Verdicts: <strong>replicates</strong> (same direction and the out-of-sample
              interval on the difference excludes zero), <strong>same direction</strong>,{" "}
              <strong>fails</strong> (opposite direction), <strong>untestable</strong> (fewer than 10
              out-of-sample instances). All three schemes are reported together: the holdout has only
              1–3 matches per player, which cannot resolve differences of a few points, so its strict
              replicates are few and its fails are mostly wide intervals on the wrong side of zero; the
              two leave-one-out schemes test every insight on every match.
            </p>
            <div className="overflow-x-auto rounded border border-line bg-surface">
              <table className="tbl">
                <caption className="sr-only">Replication totals by scheme</caption>
                <thead>
                  <tr>
                    <th scope="col">scheme</th>
                    <th scope="col" className="num">replicates</th>
                    <th scope="col" className="num">same direction</th>
                    <th scope="col" className="num">fails</th>
                    <th scope="col" className="num">untestable</th>
                  </tr>
                </thead>
                <tbody>
                  {ev.totals.map((t) => (
                    <tr key={t.scheme}>
                      <th scope="row" className="font-normal">{SCHEME[t.scheme] ?? t.scheme}</th>
                      <td className="num">{t.REPLICATES}</td>
                      <td className="num">{t["SAME DIRECTION"]}</td>
                      <td className="num">{t.FAILS}</td>
                      <td className="num">{t.UNTESTABLE}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <details className="rounded border border-line bg-surface p-3">
              <summary className="cursor-pointer text-sm font-medium">Per player</summary>
              <div className="overflow-x-auto pt-3">
                <table className="tbl">
                  <caption className="sr-only">Replication per player and scheme</caption>
                  <thead>
                    <tr>
                      <th scope="col">player</th>
                      <th scope="col">scheme</th>
                      <th scope="col" className="num">folds</th>
                      <th scope="col" className="num">replicates</th>
                      <th scope="col" className="num">same direction</th>
                      <th scope="col" className="num">fails</th>
                      <th scope="col" className="num">untestable</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ev.summary.map((r) => (
                      <tr key={`${r.player}-${r.scheme}`}>
                        <th scope="row" className="font-normal">{r.player}</th>
                        <td>{r.scheme}</td>
                        <td className="num">{r.folds}</td>
                        <td className="num">{r.REPLICATES}</td>
                        <td className="num">{r["SAME DIRECTION"]}</td>
                        <td className="num">{r.FAILS}</td>
                        <td className="num">{r.UNTESTABLE}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </>
        ) : (
          <p className="text-ink-2">The replication schemes were not run in this export.</p>
        )}
      </section>

      <section id="negative-results" className="scroll-mt-4 space-y-2">
        <h2 className="text-lg font-semibold">Negative results</h2>
        <p>
          <strong>Expected points (xP).</strong> xP from shot and position data has no signal mid-rally
          in elite singles: on the {idx.xp.holdout_matches} holdout matches the chosen xP-pre model
          ({idx.xp.chosen.pre}) scores AUC {num(idx.xp.auc_nonfinal)} on strokes that did not end the
          rally (chance = 0.50). The same features reach {num(idx.xp.auc_final)} only on final strokes,
          which is classifying how an already-decisive stroke ends (winner or error), not predicting a
          rally. A model that is allowed to see the final stroke&apos;s out / net landing zone reaches{" "}
          {num(idx.xp.leaky_auc_final, 3)} on final strokes; that number is the outcome re-labelled and
          is what a careless xP model would report. The xP tab on each player page exists to show what
          a chance-level model does to per-shot claims, and keeps the one table (finishing) where the
          number is an execution measure.
        </p>
        {xpMetrics.length > 0 && (
          <div className="overflow-x-auto rounded border border-line bg-surface">
            <table className="tbl">
              <caption className="sr-only">xP-pre holdout metrics by stroke slice</caption>
              <thead>
                <tr>
                  <th scope="col">strokes</th>
                  <th scope="col" className="num">n</th>
                  <th scope="col" className="num">accuracy</th>
                  <th scope="col" className="num">log loss</th>
                  <th scope="col" className="num">Brier</th>
                  <th scope="col" className="num">AUC</th>
                </tr>
              </thead>
              <tbody>
                {xpMetrics.map((m) => (
                  <tr key={m.slice}>
                    <th scope="row" className="font-normal">{m.slice}</th>
                    <td className="num">{int(m.n)}</td>
                    <td className="num">{num(m.accuracy, 3)}</td>
                    <td className="num">{num(m.log_loss, 3)}</td>
                    <td className="num">{num(m.brier, 3)}</td>
                    <td className="num">{num(m.auc, 3)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p>
          <strong>Live advantage bar.</strong> Before building a &ldquo;who is winning this rally&rdquo;
          bar, the question was tested with a pass condition fixed in advance: live-prefix AUC of at
          least{" "}
          {idx.live.length ? num(idx.live[0].pass_auc) : "0.60"} on the holdout matches, using each
          stroke&apos;s type, both players&apos; positions, distances from base and recent movement.
          {idx.live.length ? (
            <>
              {" "}
              Result: best live-prefix AUC {idx.live.map((l) => num(l.best_live_auc, 3)).join(" and ")}{" "}
              ({idx.live.map((l) => l.file).join(", ")}), verdict{" "}
              {idx.live.every((l) => !l.pass) ? "FAIL" : "mixed"}. The bar was not built.
            </>
          ) : (
            " The experiment's output files were not present when this export ran, so its numbers are not shown here."
          )}
        </p>
      </section>

      <section id="reproducing" className="scroll-mt-4 space-y-2">
        <h2 className="text-lg font-semibold">Reproducing these pages</h2>
        <p>
          The JSON behind this site was written on {idx.generated} by{" "}
          <code className="text-xs">{idx.command}</code> in the project repository; the site renders those
          files and computes nothing itself. Thresholds (zone bands, body radius, minimum n) live in the
          repository&apos;s configuration files and are printed on each page where they apply.
        </p>
      </section>
    </article>
  );
}
