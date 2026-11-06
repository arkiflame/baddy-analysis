import type { Metadata } from "next";
import { readIndex } from "@/lib/data";
import { int, num, pct } from "@/lib/format";

export const metadata: Metadata = {
  title: "How we check a pattern is real",
  description:
    "Where the data comes from, how a pattern is counted, compared, doubted and re-checked, and what did not work.",
};

const SCHEME_PLAIN: Record<string, string> = {
  holdout: "Matches set aside from the start (0–3 per player)",
  lomo: "Leaving out one match at a time",
  looo: "Leaving out one opponent at a time",
};

export default async function Methods() {
  const idx = await readIndex();
  const d = idx.dataset;
  const st = idx.settings.stability;
  const ev = idx.evaluation;
  const fo = idx.footage;
  const xpMetrics = idx.xp.metrics.filter((m) => m.feature_set === "pre" && m.model === idx.xp.chosen.pre);
  const lomo = ev?.totals.find((t) => t.scheme === "lomo");

  return (
    <article className="max-w-[70ch] space-y-8 text-[17px] leading-relaxed">
      <h1 className="text-3xl font-semibold tracking-tight">How we check a pattern is real</h1>
      <p className="text-ink-2">
        Every card on a player page went through the same four steps. Here they are in plain words,
        with the technical version folded underneath each one.
      </p>

      <section id="data" className="scroll-mt-4 space-y-2">
        <h2 className="text-xl font-semibold">Where the data comes from</h2>
        <p>
          People watched {int(d.matches)} professional singles matches and wrote down every shot: what
          kind it was, where both players stood, where the shuttle landed and who won the rally. That is{" "}
          {int(d.strokes)} shots. The two collections are called ShuttleSet and ShuttleSet22, published
          free by the CoachAI research group. Players with at least {idx.settings.min_matches} matches
          get a page here ({d.players} players in total).
        </p>
        <details className="rounded border border-line bg-surface p-3 text-[15px]" data-technical="">
          <summary className="cursor-pointer font-medium">Technical version</summary>
          <p className="pt-2">
            ShuttleSet (Wang, Huang, Ik, Peng, KDD 2023) and ShuttleSet22 (Wang, Du, Peng, IT4PSS at
            IJCAI 2023), MIT-licensed, from{" "}
            <a className="text-accent underline" href="https://github.com/wywyWang/CoachAI-Projects">
              CoachAI-Projects
            </a>
            . Stroke type, hitter and receiver positions at contact, landing point and rally outcome per
            stroke; camera pixels mapped to court metres with each match&apos;s homography. After
            removing matches present in both sets: {int(d.matches)} matches, {int(d.strokes)} strokes,{" "}
            {int(d.rallies_known_winner)} rallies with a known winner. No video was processed.
          </p>
        </details>
      </section>

      <section id="steps" className="scroll-mt-4 space-y-4">
        <h2 className="text-xl font-semibold">The four steps</h2>

        <div className="space-y-2">
          <h3 className="text-lg font-semibold">1. Count</h3>
          <p>
            For each kind of shot and each area of the court, we count how often the player lost the
            point within the next {idx.settings.within === 2 ? "two" : idx.settings.within} shots. We do
            the same for shots the player hits and for shots hit at the player.
          </p>
          <details className="rounded border border-line bg-surface p-3 text-[15px]" data-technical="">
            <summary className="cursor-pointer font-medium">Technical version</summary>
            <p className="pt-2">
              Outcome: P(point lost within {idx.settings.within} strokes | shot type × receiver zone).
              Zones are front / mid / rear by depth from the net and forehand / backhand by the
              receiver&apos;s racket hand, plus a body circle; thresholds live in the repository&apos;s
              zone configuration. The rally-ending stroke is never a condition and out / net errors are
              excluded, so the count cannot rediscover that errors lose points.
            </p>
          </details>
        </div>

        <div className="space-y-2">
          <h3 className="text-lg font-semibold">2. Compare</h3>
          <p>
            Every player loses points after a good smash. So each count is compared with the same
            count over every other player in the same situation, which we call &ldquo;most pros&rdquo;
            on the cards. A pattern is only interesting when the player differs from most pros, not just
            from their own average.
          </p>
          <details className="rounded border border-line bg-surface p-3 text-[15px]" data-technical="">
            <summary className="cursor-pointer font-medium">Technical version</summary>
            <p className="pt-2">
              The reference is role-based: all strokes of the same type into the same zone received (or
              hit) by any other player, the player themself excluded. It pools men&apos;s and
              women&apos;s singles. Ranking is by the difference from this reference, with Newcombe&apos;s
              95% interval on the difference of two proportions.
            </p>
          </details>
        </div>

        <div className="space-y-2">
          <h3 className="text-lg font-semibold">3. Doubt</h3>
          <p>
            A handful of shots can mislead. Every difference therefore comes with a range that says how
            far off it can be. If the range includes &ldquo;no difference&rdquo;, the card is not shown as
            a finding. If it only just clears it, the card is listed as &ldquo;too close to call&rdquo;.
            If the range is very wide, or the count is small, the card says &ldquo;early sign&rdquo;.
          </p>
          <details className="rounded border border-line bg-surface p-3 text-[15px]" data-technical="">
            <summary className="cursor-pointer font-medium">Technical version</summary>
            <p className="pt-2">
              Wilson 95% interval on each rate; a row needs n ≥ {idx.settings.min_n} on both sides.
              A candidate needs the Newcombe interval on the difference to exclude zero, and by at least
              half a percentage point to count as confident (otherwise &ldquo;possible&rdquo;).
              &ldquo;Tentative&rdquo; (early sign) means the interval is wider than{" "}
              {Math.round(st.tentative_ci_width * 100)} points or n is under {st.tentative_min_n}. The
              ranking uses the interval bound nearest zero, which penalises small-n extremes (the
              winner&apos;s curse from screening hundreds of patterns).
            </p>
          </details>
        </div>

        <div className="space-y-2">
          <h3 className="text-lg font-semibold">4. Re-check</h3>
          <p>
            We remove one of the player&apos;s matches at a time and ask whether the pattern would still
            have made the top five. A pattern that only showed up in some matches is marked as a hunch.
            For the players with the most matches we also tested each finding on matches it was not
            found on; the results are below.
          </p>
          <details className="rounded border border-line bg-surface p-3 text-[15px]" data-technical="">
            <summary className="cursor-pointer font-medium">Technical version</summary>
            <p className="pt-2">
              Leave-one-match-out selection stability: the top-{idx.settings.top_k} is re-selected once
              per match with that match left out; a pattern is ranked only if selected in at least{" "}
              {pct(st.min_share)} of the folds (&ldquo;selected in X of N folds&rdquo;). Replication under
              three schemes (holdout, leave-one-match-out, leave-one-opponent-out) with verdicts
              REPLICATES (same sign, out-of-sample interval excludes zero), SAME DIRECTION, FAILS,
              UNTESTABLE (fewer than 10 out-of-sample instances).
            </p>
          </details>
        </div>
      </section>

      <section id="replication" className="scroll-mt-4 space-y-3">
        <h2 className="text-xl font-semibold">Did the findings hold up on other matches?</h2>
        {ev && lomo ? (
          <>
            <p>
              For the {ev.players.length} players with the most matches, we took each top-five finding
              and tested it on matches it was not found on. Leaving out one match at a time,{" "}
              {lomo.REPLICATES} of {lomo.REPLICATES + lomo["SAME DIRECTION"] + lomo.FAILS + lomo.UNTESTABLE}{" "}
              findings held up fully, {lomo["SAME DIRECTION"]} pointed the same way but with a wider margin,
              and {lomo.FAILS} went the other way. The table shows all three ways of testing.
            </p>
            <div className="overflow-x-auto rounded border border-line bg-surface text-[15px]">
              <table className="tbl">
                <caption className="sr-only">How many findings held up, for each way of testing</caption>
                <thead>
                  <tr>
                    <th scope="col">How we tested</th>
                    <th scope="col" className="num">held up</th>
                    <th scope="col" className="num">same way, wider margin</th>
                    <th scope="col" className="num">went the other way</th>
                    <th scope="col" className="num">too few shots to tell</th>
                  </tr>
                </thead>
                <tbody>
                  {ev.totals.map((t) => (
                    <tr key={t.scheme}>
                      <th scope="row" className="font-normal">{SCHEME_PLAIN[t.scheme] ?? t.scheme}</th>
                      <td className="num">{t.REPLICATES}</td>
                      <td className="num">{t["SAME DIRECTION"]}</td>
                      <td className="num">{t.FAILS}</td>
                      <td className="num">{t.UNTESTABLE}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-ink-2">
              The matches set aside from the start are only a few per player, which is too little to
              settle differences of a few points. That is why the two leave-one-out rows carry more
              weight, and why all three are always shown together.
            </p>
            <details className="rounded border border-line bg-surface p-3 text-[15px]" data-technical="">
              <summary className="cursor-pointer font-medium">Per player, technical</summary>
              <div className="overflow-x-auto pt-3">
                <table className="tbl">
                  <caption className="sr-only">The same counts per player and way of testing</caption>
                  <thead>
                    <tr>
                      <th scope="col">player</th>
                      <th scope="col">scheme</th>
                      <th scope="col" className="num">folds</th>
                      <th scope="col" className="num">REPLICATES</th>
                      <th scope="col" className="num">SAME DIRECTION</th>
                      <th scope="col" className="num">FAILS</th>
                      <th scope="col" className="num">UNTESTABLE</th>
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
          <p className="text-ink-2">The re-tests were not run in this export.</p>
        )}
      </section>

      <section id="negative-results" className="scroll-mt-4 space-y-2">
        <h2 className="text-xl font-semibold">What did not work</h2>
        <p>
          We tried to predict, in the middle of a rally, who would win it, from the shots so far and
          where both players stood. It did not work: the model was no better than a coin flip. It only
          looks good on the very last shot, when the point is already decided. We also tried building a
          live &ldquo;who is ahead&rdquo; bar the same way, with a pass mark set in advance; it failed
          the pass mark and was not built. Both are reported rather than hidden.
        </p>
        <details className="rounded border border-line bg-surface p-3 text-[15px]" data-technical="">
          <summary className="cursor-pointer font-medium">Technical version</summary>
          <p className="pt-2">
            Expected points (xP) from shot and position data: on the {idx.xp.holdout_matches} holdout
            matches the chosen xP-pre model ({idx.xp.chosen.pre}) scores AUC {num(idx.xp.auc_nonfinal)} on
            strokes that did not end the rally (chance 0.50) and {num(idx.xp.auc_final)} on final strokes,
            which is classifying how an already-decisive stroke ends. A model allowed to see the final
            stroke&apos;s out / net landing zone reaches {num(idx.xp.leaky_auc_final, 3)}: the outcome
            re-labelled, and what a careless xP model would report.
            {idx.live.length
              ? ` Live-advantage bar: pass condition live-prefix AUC ≥ ${num(idx.live[0].pass_auc)} on the holdout; result ${idx.live
                  .map((l) => num(l.best_live_auc, 3))
                  .join(" and ")} (${idx.live.map((l) => l.file).join(", ")}), verdict ${
                  idx.live.every((l) => !l.pass) ? "FAIL" : "mixed"
                }.`
              : ""}
          </p>
          {xpMetrics.length > 0 && (
            <div className="overflow-x-auto pt-2">
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
        </details>
      </section>

      <section id="footage" className="scroll-mt-4 space-y-2">
        <h2 className="text-xl font-semibold">About the videos</h2>
        <p>
          {fo.with_url} of the {fo.matches} matches come with a link to the official BWF TV broadcast on
          YouTube, and the data records the second at which every shot happens. &ldquo;Watch it&rdquo;
          opens that broadcast a few seconds before an example rally. We checked that all {fo.live} links
          still work{fo.checked ? ` on ${fo.checked.slice(0, 10)}` : ""}. The other matches have no
          public link, so their players have no buttons. Nothing is downloaded or stored: the footage
          belongs to BWF.
        </p>
      </section>

      <section id="reproducing" className="scroll-mt-4 space-y-2">
        <h2 className="text-xl font-semibold">Reproducing these pages</h2>
        <p className="text-[15px]" data-technical="">
          The JSON behind this site was written on {idx.generated} by{" "}
          <code className="text-xs">{idx.command}</code> in the project repository; the site renders
          those files and computes nothing itself. Thresholds (zone bands, body radius, minimum n) live
          in the repository&apos;s configuration files.
        </p>
      </section>
    </article>
  );
}
