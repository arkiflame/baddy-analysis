"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/Badge";
import { Court, CourtLegend, type CourtMode } from "@/components/Court";
import { Tabs } from "@/components/Tabs";
import {
  MeanTable,
  PredictabilityTable,
  RateTable,
  SetPlayTable,
  TendencyTable,
  XpTable,
} from "@/components/Tables";
import { int, num, numCi, pct, pctCi, pts, ptsCi, shotWords } from "@/lib/format";
import type { CoachItem, Insight, PlayerFile, RateRow } from "@/lib/types";

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded border border-line bg-surface px-3 py-2">
      <div className="text-xs text-ink-2">{label}</div>
      <div className="text-lg font-semibold tabular">{value}</div>
      {note && <div className="text-xs text-ink-2">{note}</div>}
    </div>
  );
}

function keyOf(i: Insight) {
  return `${i.analysis}|${i.key}`;
}

function InsightBadges({
  i,
  stability,
}: {
  i: Insight;
  stability: Map<string, { where: "top" | "less_stable"; i: Insight }>;
}) {
  const s = stability.get(keyOf(i));
  const folds = s?.i.folds ?? i.folds;
  const sel = s?.i.selected_folds ?? i.selected_folds;
  return (
    <>
      {s?.where === "less_stable" && (
        <Badge variant="caution">less stable: selected in {sel} of {folds} folds</Badge>
      )}
      {s?.where === "top" && folds && (
        <Badge variant="good">
          stable in {sel} of {folds} folds
        </Badge>
      )}
      {i.tentative && <Badge variant="warn">tentative</Badge>}
      <Badge>n={int(i.n)}</Badge>
      <Badge>
        {pts(i.delta)} pts, 95% CI {ptsCi(i.delta_lo, i.delta_hi)}
      </Badge>
    </>
  );
}

function CoachList({
  items,
  stability,
  empty,
}: {
  items: CoachItem[];
  stability: Map<string, { where: "top" | "less_stable"; i: Insight }>;
  empty: string;
}) {
  if (!items.length) return <p className="text-sm text-ink-2">{empty}</p>;
  return (
    <ul className="space-y-3">
      {items.map((c) => (
        <li key={keyOf(c.insight)} className="space-y-1">
          <div>
            <span className="font-semibold">{c.title}</span> <span>{c.detail}</span>
          </div>
          <div className="flex flex-wrap gap-1">
            <InsightBadges i={c.insight} stability={stability} />
          </div>
        </li>
      ))}
    </ul>
  );
}

function ZoneCourt({ data }: { data: PlayerFile }) {
  const [role, setRole] = useState<"faced" | "hit">("faced");
  const [shot, setShot] = useState<string>("");
  const block = data.danger.all;
  const me = data.surname;
  const shotRows = useMemo(
    () => (role === "faced" ? block?.faced : block?.hit) ?? [],
    [block, role],
  );
  const zoneRows = (role === "faced" ? block?.faced_zone : block?.hit_zone) ?? [];
  const shots = useMemo(
    () => Array.from(new Set(shotRows.map((r) => r.shot).filter(Boolean) as string[])).sort(),
    [shotRows],
  );
  const rows: RateRow[] = shot ? shotRows.filter((r) => r.shot === shot) : zoneRows;
  const fhRight = role === "faced" ? data.coverage.handedness === "right" : true;
  const base = data.positions.base;
  const mode: CourtMode = {
    kind: "zones",
    rows,
    role,
    me,
    within: data.settings.within,
    minN: data.settings.min_n,
    bodyAt:
      role === "faced"
        ? { x: base.lat_right, y: base.depth }
        : { x: 0, y: data.positions.ref_base.depth_median },
    bodyNote:
      role === "faced"
        ? `drawn at ${me}'s base position`
        : "drawn at the other players' median base depth",
  };
  const sideLabels =
    role === "faced"
      ? fhRight
        ? { left: `${me}'s backhand side`, right: `${me}'s forehand side` }
        : { left: `${me}'s forehand side`, right: `${me}'s backhand side` }
      : { left: "opponent's backhand side", right: "opponent's forehand side" };
  const what = shot ? shotWords(shot) : "any shot";
  const title =
    role === "faced"
      ? `Zones on ${me}'s side: how often ${me} loses within ${data.settings.within} shots after ${what} there, vs typical pros`
      : `Zones on the opponent's side: how often ${me} loses within ${data.settings.within} shots after playing ${what} there, vs typical pros`;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-4">
        <fieldset className="flex gap-2">
          <legend className="text-sm font-medium">Court view</legend>
          {(["faced", "hit"] as const).map((r) => (
            <label key={r} className="flex items-center gap-1 text-sm">
              <input type="radio" name="role" value={r} checked={role === r} onChange={() => setRole(r)} />
              {r === "faced" ? `shots ${me} faces` : `shots ${me} plays`}
            </label>
          ))}
        </fieldset>
        <div className="flex flex-col gap-1">
          <label htmlFor="shot-filter" className="text-sm font-medium">
            Shot type
          </label>
          <select
            id="shot-filter"
            value={shot}
            onChange={(e) => setShot(e.target.value)}
            className="rounded border border-line bg-surface px-2 py-1 text-sm"
          >
            <option value="">any shot</option>
            {shots.map((s) => (
              <option key={s} value={s}>
                {shotWords(s)}
              </option>
            ))}
          </select>
        </div>
      </div>
      <p className="text-sm text-ink-2">{title}. Hover or focus a zone for n and the 95% intervals.</p>
      <Court frame={data.positions.frame} fhOnRight={fhRight} sideLabels={sideLabels} mode={mode} title={title} />
      <CourtLegend mode="zones" />
      <details className="rounded border border-line bg-surface p-3">
        <summary className="cursor-pointer text-sm font-medium">The same numbers as a table</summary>
        <div className="pt-3">
          <RateTable
            rows={rows}
            caption={title}
            first={role === "faced" ? "zone on the player's side" : "opponent zone"}
            outcome={`lost within ${data.settings.within}`}
          />
        </div>
      </details>
    </div>
  );
}

function HeatCourt({ data }: { data: PlayerFile }) {
  const [role, setRole] = useState<"hit" | "receive">("hit");
  const me = data.surname;
  const p = data.positions;
  const fhRight = p.handedness === "right";
  const grid = p.grids[role];
  const what = role === "hit" ? `where ${me} stands when hitting` : `where ${me} stands when the opponent hits`;
  const title = `Position map: ${what} (${int(grid.n)} strokes, 0.25 m cells)`;
  return (
    <div className="space-y-3">
      <fieldset className="flex flex-wrap gap-3">
        <legend className="text-sm font-medium">Positions</legend>
        {(["hit", "receive"] as const).map((r) => (
          <label key={r} className="flex items-center gap-1 text-sm">
            <input type="radio" name="posrole" value={r} checked={role === r} onChange={() => setRole(r)} />
            {r === "hit" ? `when ${me} hits` : `when the opponent hits`}
          </label>
        ))}
      </fieldset>
      <Court
        frame={p.frame}
        fhOnRight={fhRight}
        sideLabels={
          fhRight
            ? { left: `${me}'s backhand side`, right: `${me}'s forehand side` }
            : { left: `${me}'s forehand side`, right: `${me}'s backhand side` }
        }
        mode={{
          kind: "heat",
          grid,
          base: {
            x: p.base.lat_right,
            y: p.base.depth,
            xq1: p.base.lat_q1,
            xq3: p.base.lat_q3,
            yq1: p.base.depth_q1,
            yq3: p.base.depth_q3,
          },
          what,
        }}
        title={title}
      />
      <CourtLegend mode="heat" />
    </div>
  );
}

export function PlayerView({ data }: { data: PlayerFile }) {
  const me = data.surname;
  const c = data.coverage;
  const stability = useMemo(() => {
    const m = new Map<string, { where: "top" | "less_stable"; i: Insight }>();
    for (const i of data.insights.top) m.set(keyOf(i), { where: "top", i });
    for (const i of data.insights.less_stable) m.set(keyOf(i), { where: "less_stable", i });
    return m;
  }, [data]);
  const st = data.settings.stability;
  const within = data.settings.within;

  const insightsTab = (
    <div className="space-y-6">
      <section className="space-y-3">
        <h3 className="text-lg font-semibold">Top insights</h3>
        <p className="text-sm text-ink-2">
          Where {me} differs most from typical pros among patterns a coach can act on, ranked by the
          smallest difference the data still supports (the 95% interval bound nearest zero).
          {st.checked && st.folds
            ? ` Only patterns selected in at least ${pct(st.min_share)} of the ${st.folds} leave-one-match-out folds are ranked; the rest are listed as less stable.`
            : ""}{" "}
          <em>Tentative</em> = the interval on the difference is wider than{" "}
          {Math.round(st.tentative_ci_width * 100)} points or n is under {st.tentative_min_n}.
        </p>
        {data.insights.top.length === 0 && (
          <p className="text-sm text-ink-2">No pattern passes the sample-size, interval and stability tests.</p>
        )}
        <ol className="space-y-3">
          {data.insights.top.map((i) => (
            <li key={keyOf(i)} className="rounded border border-line bg-surface p-3">
              <div className="mb-1 flex flex-wrap items-center gap-1">
                <span className="mr-1 font-semibold">#{i.rank}</span>
                <InsightBadges i={i} stability={stability} />
              </div>
              <p className="text-sm">{i.text}</p>
            </li>
          ))}
        </ol>
        {data.insights.less_stable.length > 0 && (
          <div className="space-y-2">
            <h4 className="font-semibold">Less stable</h4>
            <p className="text-sm text-ink-2">
              Patterns the plain ranking would have shown but that fewer than half of the leave-one-match-out folds select. Read them as candidates, not findings.
            </p>
            <ul className="space-y-3">
              {data.insights.less_stable.map((i) => (
                <li key={keyOf(i)} className="rounded border border-warn-line bg-surface p-3">
                  <div className="mb-1 flex flex-wrap items-center gap-1">
                    <InsightBadges i={i} stability={stability} />
                  </div>
                  <p className="text-sm">{i.text}</p>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>
      <section className="space-y-3">
        <h3 className="text-lg font-semibold">Court zones</h3>
        <ZoneCourt data={data} />
      </section>
      <section className="space-y-3">
        <h3 className="text-lg font-semibold">The evidence: danger tables</h3>
        <p className="text-sm text-ink-2">
          Probability that {me} loses the point within {within} shots after that shot, next to the
          same probability for typical pros (all other players in the same situation) and the
          difference in percentage points with Newcombe&apos;s 95% interval. Zones are from the
          receiver&apos;s point of view; shots the rally ended on with an out or net error are excluded.
          Baselines: {pct(data.danger.all?.baseline_faced ?? null, 1)} over all shots {me} faces,{" "}
          {pct(data.danger.all?.baseline_hit ?? null, 1)} over all shots {me} plays.
        </p>
        <h4 className="font-semibold">Shots {me} faces</h4>
        <RateTable rows={data.danger.all?.faced ?? []} caption={`Shots ${me} faces`} first="opponent shot → zone" outcome={`lost within ${within}`} limit={12} />
        <h4 className="font-semibold">Shots {me} plays</h4>
        <RateTable rows={data.danger.all?.hit ?? []} caption={`Shots ${me} plays`} first="shot → opponent zone" outcome={`lost within ${within}`} limit={12} />
        {data.danger.game3 && (
          <details className="rounded border border-line bg-surface p-3">
            <summary className="cursor-pointer text-sm font-medium">Game 3 only</summary>
            <div className="space-y-3 pt-3">
              <RateTable rows={data.danger.game3.faced ?? []} caption={`Game 3, shots ${me} faces`} first="opponent shot → zone" outcome={`lost within ${within}`} limit={8} />
              <RateTable rows={data.danger.game3.hit ?? []} caption={`Game 3, shots ${me} plays`} first="shot → opponent zone" outcome={`lost within ${within}`} limit={8} />
            </div>
          </details>
        )}
        {data.danger.pressure && (
          <details className="rounded border border-line bg-surface p-3">
            <summary className="cursor-pointer text-sm font-medium">At {data.settings.pressure_from}+ only</summary>
            <div className="space-y-3 pt-3">
              <RateTable rows={data.danger.pressure.faced ?? []} caption={`At ${data.settings.pressure_from}+, shots ${me} faces`} first="opponent shot → zone" outcome={`lost within ${within}`} limit={8} />
              <RateTable rows={data.danger.pressure.hit ?? []} caption={`At ${data.settings.pressure_from}+, shots ${me} plays`} first="shot → opponent zone" outcome={`lost within ${within}`} limit={8} />
            </div>
          </details>
        )}
      </section>
    </div>
  );

  const h = data.habits;
  const habitsTab = (
    <div className="space-y-6">
      <p className="text-sm text-ink-2">
        Based on {int(h.n_replies)} of {me}&apos;s replies to a known in-play shot. A situation is the
        opponent&apos;s shot type and the zone it landed in (from {me}&apos;s view, body included);
        &ldquo;→ any&rdquo; pools the zones. A habit is a reply chosen significantly more often than
        typical pros in the same situation (n ≥ {data.settings.min_n} on both sides, Newcombe 95%
        interval on the difference of shares excludes zero).
      </p>
      <section className="space-y-2">
        <h3 className="text-lg font-semibold">Habits by reply shot type</h3>
        <TendencyTable rows={h.by_shot.filter((r) => r.habit)} caption="Habits by reply shot type" limit={10} />
      </section>
      <section className="space-y-2">
        <h3 className="text-lg font-semibold">Habits by reply shot and target zone</h3>
        <p className="text-sm text-ink-2">Target zone from the opponent&apos;s view; replies that ended the rally with an error are excluded.</p>
        <TendencyTable rows={h.by_shot_zone.filter((r) => r.habit)} caption="Habits by reply shot and target zone" limit={10} />
      </section>
      <section className="space-y-2">
        <h3 className="text-lg font-semibold">Predictability</h3>
        <p className="text-sm text-ink-2">
          Shannon entropy (bits, Miller-Madow corrected, bootstrap 95% interval) of {me}&apos;s reply per
          situation, next to typical pros&apos; entropy estimated by subsampling their replies to {me}&apos;s n
          (mean and 2.5–97.5 percentiles over 200 draws). Effective replies = 2^entropy. Flagged when
          the entropy falls outside the typical-pro band.
        </p>
        <h4 className="font-semibold">Most predictable situations</h4>
        <PredictabilityTable rows={h.predictability.slice(0, 10)} caption="Most predictable situations" />
        <h4 className="font-semibold">Least predictable situations</h4>
        <PredictabilityTable rows={[...h.predictability].sort((a, b) => b.delta - a.delta).slice(0, 5)} caption="Least predictable situations" />
      </section>
    </div>
  );

  const setPlaysTab = (
    <div className="space-y-6">
      <p className="text-sm text-ink-2">
        The first three and four strokes as shot types, ranked by how distinctive the opening is
        versus typical pros in the same role (difference in share of rallies, 95% interval), with the
        win rate attached. Openings seen fewer than {data.settings.min_n} times are omitted.
      </p>
      {(["serve", "receive"] as const).map((role) => (
        <section key={role} className="space-y-3">
          <h3 className="text-lg font-semibold">When {me} {role === "serve" ? "serves" : "receives"}</h3>
          {[3, 4].map((k) => (
            <div key={k} className="space-y-1">
              <h4 className="font-semibold">First {k} strokes</h4>
              <SetPlayTable rows={h.set_plays[`${role}${k}`] ?? []} caption={`First ${k} strokes when ${me} ${role}s`} me={me} />
            </div>
          ))}
        </section>
      ))}
    </div>
  );

  const p = data.positions;
  const side = p.base.lat_right * (p.handedness === "right" ? 1 : -1) >= 0 ? "forehand" : "backhand";
  const positionsTab = (
    <div className="space-y-6">
      <p className="text-sm text-ink-2">
        ShuttleSet records where each player stands only at the instant a stroke is hit, so these
        are position maps, not footwork paths, and every distance is a lower bound (straight lines
        between consecutive own-hit positions). The lateral axis is labelled with {me}&apos;s forehand
        and backhand side ({c.handedness}-handed{c.handedness_known ? "" : ", assumed"}).
      </p>
      <HeatCourt data={data} />
      <section className="space-y-2">
        <h3 className="text-lg font-semibold">Base position</h3>
        <p className="text-sm">
          Median position when the opponent hits a non-serve stroke (n={int(p.base.n)}):{" "}
          <strong>{num(p.base.depth)} m</strong> from the net, {num(Math.abs(p.base.lat_right))} m toward
          the {side} side (interquartile range {num(p.base.depth_q1)}–{num(p.base.depth_q3)} m deep,{" "}
          {num(p.base.lat_q1, 2, true)} to {num(p.base.lat_q3, 2, true)} m lateral). Typical pros: median
          of the {p.ref_base.players} other players&apos; bases {num(p.ref_base.depth_median)} m from the net
          (players range {num(p.ref_base.depth_min)}–{num(p.ref_base.depth_max)} m), {num(p.ref_base.lat_abs_median)} m
          from the centre line.
        </p>
      </section>
      <section className="space-y-2">
        <h3 className="text-lg font-semibold">Pulled from base, by the opponent&apos;s shot</h3>
        <p className="text-sm text-ink-2">Distance between {me}&apos;s base and where {me} played the reply; serves and serve returns excluded.</p>
        <MeanTable rows={p.pull} caption="Pull from base by incoming shot" first="opponent's shot" unit="m" />
      </section>
      <section className="space-y-2">
        <h3 className="text-lg font-semibold">Distance per rally</h3>
        <p className="text-sm text-ink-2">Sum of straight lines between {me}&apos;s consecutive hit positions (a lower bound), by game and by score pressure ({data.settings.pressure_from}+).</p>
        <MeanTable rows={p.distance} caption="Distance per rally" first="rallies" unit="m" />
        <h4 className="font-semibold">Per own stroke (controls for rally length)</h4>
        <MeanTable rows={p.per_hit} caption="Distance per own stroke" first="per own hit" unit="m" />
      </section>
    </div>
  );

  const x = data.xp;
  const xpTab = x ? (
    <div className="space-y-6">
      <div className="rounded border border-warn-line bg-warn-bg p-3 text-sm text-warn-ink" role="note">
        <strong>⚠ {x.caveat}</strong>
      </div>
      <p className="text-sm text-ink-2">
        xP is P(the hitter wins the rally | the shot just played), from a model trained on {x.dev_matches}{" "}
        development matches and checked on the {x.holdout_matches} holdout matches. Every number here
        uses xP-pre, which sees only what is known before the shuttle lands; chosen model:{" "}
        {x.chosen.pre}. Based on {int(x.n_shots)} of {me}&apos;s strokes in {int(x.n_rallies)} rallies.
        Mid-rally the model&apos;s expectation is close to the base rate for every shot, so &ldquo;points
        above expectation&rdquo; mostly measures how often the player wins rallies containing that shot;
        &ldquo;vs own overall&rdquo; removes the player&apos;s general edge. Intervals are over rallies.
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="holdout AUC, non-final strokes" value={num(x.auc_nonfinal)} note="chance = 0.50" />
        <Stat label="holdout AUC, final strokes" value={num(x.auc_final)} note="classifying how a decisive stroke ends" />
        <Stat label="AUC with the final zone leaked" value={num(x.leaky_auc_final, 3)} note="what a careless model reports" />
        <Stat label={`${me}: points above expectation`} value={num(x.overall.mean, 3, true)} note={`per rally, 95% CI ${numCi(x.overall.lo, x.overall.hi, 3, true)}, n=${int(x.overall.n)}; other pros ${num(x.overall.ref_mean, 3, true)}`} />
      </div>
      <section className="space-y-2">
        <h3 className="text-lg font-semibold">Finishing</h3>
        <p className="text-sm text-ink-2">
          Final strokes only, one per rally: given that {me}&apos;s stroke ended the rally, how often it
          was a winner rather than an error, minus what xP-pre expected. The one table where the model
          has signal.
        </p>
        <XpTable rows={x.finishing} caption="Finishing" first="final shot" value="points above expectation" unit="strokes" />
      </section>
      <section className="space-y-2">
        <h3 className="text-lg font-semibold">By shot type</h3>
        <XpTable rows={x.by_shot} caption="Points above expectation by shot" first="shot" value="points above expectation" unit="rallies" withOwn />
      </section>
      <section className="space-y-2">
        <h3 className="text-lg font-semibold">By shot and the court band it was hit from</h3>
        <XpTable rows={x.by_shot_band} caption="Points above expectation by shot and band" first="shot, hit from" value="points above expectation" unit="rallies" withOwn limit={12} />
      </section>
    </div>
  ) : (
    <p className="text-sm text-ink-2">The export did not include the xP section for this player.</p>
  );

  return (
    <div className="space-y-6">
      <header className="space-y-3">
        <h1 className="text-2xl font-semibold tracking-tight">{data.player}</h1>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
          <Stat label="Matches" value={int(c.matches)} note={`${c.holdout_matches} in the holdout set`} />
          <Stat label="Rallies" value={int(c.rallies)} note="with a known winner" />
          <Stat label="Strokes" value={int(c.strokes)} />
          <Stat label="Rally win rate" value={pct(c.win_rate, 1)} note={`95% CI ${pctCi(c.win_lo, c.win_hi)}`} />
          <Stat label="Racket hand" value={c.handedness} note={c.handedness_known ? "verified source in players.toml" : "not in players.toml, assumed"} />
        </div>
        <p className="text-sm text-ink-2">
          &ldquo;Typical pros&rdquo; = all other players in the dataset in the same situation; {me} is
          never part of {me}&apos;s own reference. Minimum n = {data.settings.min_n} on both sides of
          every comparison. Generated {data.generated}.
        </p>
      </header>

      <section aria-labelledby="scouting" className="grid gap-4 md:grid-cols-2">
        <h2 id="scouting" className="sr-only">
          Scouting summary
        </h2>
        <div className="rounded border border-line bg-surface p-4">
          <h3 className="mb-2 text-lg font-semibold">How to play against {me}</h3>
          <p className="mb-3 text-sm text-ink-2">
            For an opponent. Each line is a situation where {me}&apos;s record differs from typical pros
            with 95% confidence; &ldquo;loses within {within} shots&rdquo; means the point ended within{" "}
            {within} strokes of that shot and {me} lost it.
          </p>
          <CoachList items={data.coach.against} stability={stability} empty="Nothing passes the tests." />
        </div>
        <div className="rounded border border-line bg-surface p-4">
          <h3 className="mb-2 text-lg font-semibold">What {me} should fix</h3>
          <p className="mb-3 text-sm text-ink-2">Situations where {me} loses more often than typical pros.</p>
          <CoachList
            items={data.coach.fix}
            stability={stability}
            empty={`No situation where ${me} loses more than typical pros passes the sample-size and interval tests.`}
          />
        </div>
      </section>

      <Tabs
        tabs={[
          { id: "insights", label: "Insights", content: insightsTab },
          { id: "habits", label: "Habits", content: habitsTab },
          { id: "setplays", label: "Set plays", content: setPlaysTab },
          { id: "positions", label: "Position maps", content: positionsTab },
          { id: "xp", label: "xP", content: xpTab },
        ]}
      />
    </div>
  );
}
