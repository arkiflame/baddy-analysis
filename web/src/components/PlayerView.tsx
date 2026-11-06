"use client";

import { useMemo, useState, type ReactNode } from "react";
import { Badge } from "@/components/Badge";
import { HowToRead } from "@/components/HowToRead";
import { InsightCard, Numbers, PlainFlags } from "@/components/InsightCard";
import { Reveal } from "@/components/ShowNumbers";
import { WatchIt } from "@/components/WatchIt";
import {
  MeanTable,
  PredictabilityTable,
  RateTable,
  SetPlayTable,
  TendencyTable,
  XpTable,
} from "@/components/Tables";
import { HabitArrows } from "@/components/court/HabitArrows";
import { HeatCourt } from "@/components/court/HeatCourt";
import { HeroCourt } from "@/components/court/HeroCourt";
import { RallyCourt } from "@/components/court/RallyCourt";
import { ZoneCourt, ZoneLegend } from "@/components/court/ZoneCourt";
import { int, num, numCi, pct, pctCi, shotWords, situationWords } from "@/lib/format";
import type { CoachItem, Insight, PlayerFile, RallyStroke, RateRow } from "@/lib/types";

/* ------------------------------------------------------------------------------------ */
/* Small pieces                                                                          */
/* ------------------------------------------------------------------------------------ */

function Stat({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="rounded border border-line bg-surface px-3 py-2">
      <div className="text-xs text-ink-2">{label}</div>
      <div className="text-lg font-semibold tabular">{value}</div>
      {note && <div className="text-xs text-ink-2">{note}</div>}
    </div>
  );
}

function Section({
  id,
  title,
  lead,
  children,
}: {
  id: string;
  title: string;
  lead?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-h`} className="scroll-mt-4 space-y-3">
      <h2 id={`${id}-h`} className="text-xl font-semibold tracking-tight">
        {title}
      </h2>
      {lead && <p className="max-w-[70ch] text-ink-2">{lead}</p>}
      {children}
    </section>
  );
}

const keyOf = (i: Insight) => `${i.analysis}|${i.key}`;

/* ------------------------------------------------------------------------------------ */
/* Coach lists                                                                           */
/* ------------------------------------------------------------------------------------ */

function CoachCards({
  items,
  me,
  empty,
  trainingNote,
  renderRallyFor,
}: {
  items: CoachItem[];
  me: string;
  empty: string;
  trainingNote?: boolean;
  renderRallyFor: (strokes: RallyStroke[], title: string) => ReactNode;
}) {
  if (!items.length) return <p className="max-w-[70ch] text-ink-2">{empty}</p>;
  return (
    <ol className="space-y-3">
      {items.map((c, n) => (
        <li key={keyOf(c.insight)}>
          <InsightCard
            i={c.insight}
            me={me}
            number={n + 1}
            renderRally={renderRallyFor}
            aside={
              trainingNote ? (
                <p className="text-sm text-ink-2">
                  For {me}&apos;s own training: {c.title.replace(/\.$/, "").replace(/^./, (ch) => ch.toLowerCase())}.
                </p>
              ) : undefined
            }
          />
        </li>
      ))}
    </ol>
  );
}

/* ------------------------------------------------------------------------------------ */
/* Where points are won and lost (zone court with controls)                              */
/* ------------------------------------------------------------------------------------ */

function ZoneExplorer({ data, me }: { data: PlayerFile; me: string }) {
  const [role, setRole] = useState<"faced" | "hit">("faced");
  const [shot, setShot] = useState<string>("");
  const block = data.danger.all;
  const shotRows = useMemo(() => (role === "faced" ? block?.faced : block?.hit) ?? [], [block, role]);
  const zoneRows = (role === "faced" ? block?.faced_zone : block?.hit_zone) ?? [];
  const shots = useMemo(
    () => Array.from(new Set(shotRows.map((r) => r.shot).filter(Boolean) as string[])).sort(),
    [shotRows],
  );
  const rows: RateRow[] = shot ? shotRows.filter((r) => r.shot === shot) : zoneRows;
  const fhRight = data.coverage.handedness === "right";
  const base = data.positions.base;
  const what = shot ? shotWords(shot) : "any shot";
  const title =
    role === "faced"
      ? `${me}'s side of the court: where ${what} from the opponent costs ${me} the point, compared with most pros`
      : `The opponent's side: where ${me}'s ${what} costs ${me} the point, compared with most pros`;
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-4">
        <fieldset className="flex flex-wrap gap-3">
          <legend className="text-sm font-medium">Show</legend>
          {(["faced", "hit"] as const).map((r) => (
            <label key={r} className="flex items-center gap-1 text-sm">
              <input type="radio" name="zone-role" value={r} checked={role === r} onChange={() => setRole(r)} />
              {r === "faced" ? `shots played at ${me}` : `shots ${me} plays`}
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
      <p className="max-w-[70ch] text-sm text-ink-2">{title}. Tap or hover an area for the words.</p>
      <ZoneCourt
        frame={data.positions.frame}
        fhOnRight={role === "faced" ? fhRight : true}
        me={me}
        rows={rows}
        role={role}
        within={data.settings.within}
        minN={data.settings.min_n}
        bodyAt={
          role === "faced"
            ? { x: base.lat_right, y: base.depth }
            : { x: 0, y: data.positions.ref_base.depth_median }
        }
        title={title}
      />
      <ZoneLegend me={me} />
      <Reveal label="Show the tables">
        <RateTable
          rows={rows}
          caption={title}
          first={role === "faced" ? "area on the player's side" : "area on the opponent's side"}
          outcome={`lost within ${data.settings.within}`}
        />
      </Reveal>
    </div>
  );
}

/* ------------------------------------------------------------------------------------ */
/* The page                                                                              */
/* ------------------------------------------------------------------------------------ */

export function PlayerView({ data }: { data: PlayerFile }) {
  const me = data.surname;
  const c = data.coverage;
  const within = data.settings.within;
  const fhRight = data.coverage.handedness === "right";
  const h = data.habits;
  const p = data.positions;
  const x = data.xp;

  const rally = (strokes: RallyStroke[], title: string) => <RallyCourt strokes={strokes} me={me} title={title} />;

  // Hero: up to three takeaways drawn on the court, strongest first.
  const heroItems = data.summary.slice(0, 3).map((s, n) => ({
    n: n + 1,
    role: s.insight.role,
    zone: s.insight.zone,
    shot: s.insight.shot,
    kind: (s.insight.delta ?? 0) < 0 ? ("strong" as const) : ("weak" as const),
  }));

  // Habits: the situations with the most replies get a drawing; the rest are sentences.
  const habitSituations = useMemo(() => {
    const groups = new Map<string, { rows: typeof h.by_shot_zone; n: number }>();
    for (const r of h.by_shot_zone) {
      if (r.situation.endsWith("-> any")) continue;
      const g = groups.get(r.situation) ?? { rows: [], n: r.n };
      g.rows.push(r);
      groups.set(r.situation, g);
    }
    return Array.from(groups.entries())
      .filter(([, g]) => g.rows.length >= 2)
      .sort((a, b) => b[1].n - a[1].n)
      .slice(0, 2);
  }, [h]);
  const habitSentences = h.by_shot.filter((r) => r.habit).slice(0, 5);
  const easyToRead = h.predictability.filter((r) => r.more_predictable).slice(0, 3);
  const hardToRead = h.predictability.filter((r) => r.less_predictable).slice(0, 2);
  const openings = (["serve", "receive"] as const).map((role) => ({
    role,
    rows: (h.set_plays[`${role}3`] ?? []).filter((r) => r.candidate).slice(0, 2),
  }));

  const pullSignals = p.pull.filter((r) => r.signal && r.plain).slice(0, 3);
  const pullSame = p.pull.filter((r) => !r.signal && r.plain).slice(0, 2);
  const perHit = p.per_hit.find((r) => r.label === "all rallies");
  const finishing = x?.finishing.filter((r) => r.plain) ?? [];

  return (
    <div className="space-y-10">
      <header className="space-y-3">
        <h1 className="text-3xl font-semibold tracking-tight">{data.player}</h1>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
          <Stat label="Matches in the data" value={int(c.matches)} />
          <Stat label="Rallies" value={int(c.rallies)} />
          <Stat label="Rallies won" value={pct(c.win_rate)} />
          <Stat label="Plays" value={`${c.handedness}-handed`} note={c.handedness_known ? undefined : "assumed"} />
          <Stat
            label="Video available"
            value={`${data.footage.matches_with_video} of ${data.footage.matches}`}
            note="matches"
          />
        </div>
      </header>

      <HowToRead me={me} within={within} pressureFrom={data.settings.pressure_from} />

      <Section
        id="summary"
        title="In short"
        lead={
          data.summary.length
            ? `The findings that held up best, drawn on the court. Numbers on the markers match the list.`
            : `No pattern for ${me} is both solid and well tested yet, so there is no short version. The cards below say how sure we are about each one.`
        }
      >
        {data.summary.length > 0 && (
          <div className="grid gap-4 md:grid-cols-[minmax(0,360px)_1fr]">
            <HeroCourt
              items={heroItems}
              me={me}
              fhOnRight={fhRight}
              frame={p.frame}
              bodyAt={{ x: p.base.lat_right, y: p.base.depth }}
              title={`${me}'s three biggest takeaways drawn on the court`}
            />
            <ol className="space-y-3">
              {data.summary.slice(0, 3).map((s, n) => (
                <li key={keyOf(s.insight)} className="space-y-1">
                  <p>
                    <span className="mr-2 inline-flex h-6 w-6 items-center justify-center rounded-full bg-ink text-xs font-semibold text-page">
                      {n + 1}
                    </span>
                    <strong>{s.insight.headline}</strong>
                  </p>
                  <p className="max-w-[70ch] text-ink-2">{s.insight.evidence}</p>
                  <div className="flex flex-wrap gap-2">
                    <WatchIt examples={s.insight.examples} me={me} renderRally={rally} />
                    <Reveal label="Show the numbers">
                      <Numbers i={s.insight} me={me} />
                    </Reveal>
                  </div>
                </li>
              ))}
            </ol>
          </div>
        )}
      </Section>

      <Section
        id="beat"
        title={`How to beat ${me}`}
        lead={`Where ${me} loses the point more often than most pros. Each card is something an opponent can do.`}
      >
        <CoachCards
          items={data.coach.fix}
          me={me}
          empty={`Nothing here: no situation costs ${me} the point clearly more often than it costs most pros.`}
          trainingNote
          renderRallyFor={rally}
        />
      </Section>

      <Section
        id="strengths"
        title={`What ${me} does well`}
        lead={`Where ${me} loses the point less often than most pros. Each card is something an opponent should not count on.`}
      >
        <CoachCards
          items={data.coach.against}
          me={me}
          empty={`Nothing here: no situation is clearly safer for ${me} than for most pros.`}
          renderRallyFor={rally}
        />
        {data.coach.possible.length > 0 && (
          <details className="rounded border border-warn-line bg-surface p-4">
            <summary className="cursor-pointer font-semibold">
              Possible, not confident ({data.coach.possible.length})
            </summary>
            <p className="mb-3 mt-2 max-w-[70ch] text-ink-2">{data.coach.possible_note_plain}</p>
            <CoachCards items={data.coach.possible} me={me} empty="" renderRallyFor={rally} />
          </details>
        )}
      </Section>

      <Section
        id="habits"
        title="Habits"
        lead={`What ${me} tends to do next, compared with most pros in the same spot. Based on ${int(h.n_replies)} of ${me}'s replies.`}
      >
        {habitSituations.length > 0 && (
          <div className="grid gap-4 lg:grid-cols-2">
            {habitSituations.map(([situation, g]) => (
              <div key={situation} className="space-y-2 rounded border border-line bg-surface p-3">
                <h3 className="font-semibold">After {situationWords(situation, `${me}'s`)}</h3>
                <HabitArrows
                  situation={situation}
                  replies={g.rows.map((r) => ({ reply: r.reply, rate: r.rate, ref_rate: r.ref_rate, n: r.n }))}
                  me={me}
                  fhOnRight={fhRight}
                  frame={p.frame}
                  title={`Where ${me} usually hits after ${situationWords(situation, `${me}'s`)}`}
                />
              </div>
            ))}
          </div>
        )}
        {habitSentences.length > 0 ? (
          <ul className="space-y-2">
            {habitSentences.map((r) => (
              <li key={`${r.situation}|${r.reply}`} className="max-w-[70ch] rounded border border-line bg-surface p-3">
                {r.plain}
              </li>
            ))}
          </ul>
        ) : (
          <p className="max-w-[70ch] text-ink-2">No reply stands out from what most pros do.</p>
        )}
        {(easyToRead.length > 0 || hardToRead.length > 0) && (
          <div className="space-y-2">
            <h3 className="font-semibold">How predictable {me} is</h3>
            <ul className="space-y-2">
              {[...easyToRead, ...hardToRead].map((r) => (
                <li key={r.situation} className="max-w-[70ch] rounded border border-line bg-surface p-3">
                  {r.plain}
                </li>
              ))}
            </ul>
          </div>
        )}
        {openings.some((o) => o.rows.length) && (
          <div className="space-y-2">
            <h3 className="font-semibold">How {me}&apos;s rallies start</h3>
            <ul className="space-y-2">
              {openings.flatMap((o) =>
                o.rows.map((r) => (
                  <li key={`${o.role}-${r.sequence}`} className="max-w-[70ch] rounded border border-line bg-surface p-3">
                    {r.plain}
                  </li>
                )),
              )}
            </ul>
          </div>
        )}
        <Reveal label="Show the tables">
          <h4 className="font-semibold">Habits by reply shot</h4>
          <TendencyTable rows={h.by_shot.filter((r) => r.habit)} caption="Habits by reply shot type" limit={10} />
          <h4 className="font-semibold">Habits by reply shot and target area</h4>
          <TendencyTable rows={h.by_shot_zone.filter((r) => r.habit)} caption="Habits by reply shot and target zone" limit={10} />
          <h4 className="font-semibold">Predictability (Shannon entropy of the reply, bits)</h4>
          <PredictabilityTable rows={h.predictability.slice(0, 10)} caption="Most predictable situations" />
          <h4 className="font-semibold">Openings</h4>
          {(["serve", "receive"] as const).map((role) =>
            [3, 4].map((k) => (
              <div key={`${role}${k}`} className="space-y-1">
                <p className="text-ink-2">First {k} strokes when {me} {role}s</p>
                <SetPlayTable rows={h.set_plays[`${role}${k}`] ?? []} caption={`First ${k} strokes when ${me} ${role}s`} me={me} />
              </div>
            )),
          )}
        </Reveal>
      </Section>

      <Section
        id="movement"
        title="Movement"
        lead={`Where ${me} stands and how far ${me} is pulled. Positions are known only at the moment a shot is hit, so real distances are a little longer than these.`}
      >
        <p className="max-w-[70ch]">{p.plain_base}</p>
        <HeatCourt
          grid={p.grids.receive}
          base={{
            x: p.base.lat_right,
            y: p.base.depth,
            xq1: p.base.lat_q1,
            xq3: p.base.lat_q3,
            yq1: p.base.depth_q1,
            yq3: p.base.depth_q3,
          }}
          me={me}
          fhOnRight={fhRight}
          frame={p.frame}
          title={`Where ${me} stands when the opponent hits (${int(p.grids.receive.n)} shots)`}
        />
        <ul className="space-y-2">
          {[...pullSignals, ...pullSame].map((r) => (
            <li key={r.label} className="max-w-[70ch] rounded border border-line bg-surface p-3">
              {r.plain}
            </li>
          ))}
          {perHit?.plain && (
            <li className="max-w-[70ch] rounded border border-line bg-surface p-3">{perHit.plain}</li>
          )}
        </ul>
        <Reveal label="Show the tables">
          <p>
            Base position: median position when the opponent hits (n={int(p.base.n)}): {num(p.base.depth)} m from
            the net, {num(p.base.lat_right, 2, true)} m lateral (interquartile range {num(p.base.depth_q1)}–
            {num(p.base.depth_q3)} m deep). Other players&apos; bases: median {num(p.ref_base.depth_median)} m
            (range {num(p.ref_base.depth_min)}–{num(p.ref_base.depth_max)} m).
          </p>
          <h4 className="font-semibold">Pulled from base, by the opponent&apos;s shot</h4>
          <MeanTable rows={p.pull} caption="Pull from base by incoming shot" first="opponent's shot" unit="m" />
          <h4 className="font-semibold">Distance per rally</h4>
          <MeanTable rows={p.distance} caption="Distance per rally" first="rallies" unit="m" />
          <h4 className="font-semibold">Distance per own stroke</h4>
          <MeanTable rows={p.per_hit} caption="Distance per own stroke" first="per own hit" unit="m" />
        </Reveal>
      </Section>

      <Section
        id="how"
        title="How we know"
        lead="Four checks stand behind every card. The full story is on the Methods page."
      >
        <ol className="max-w-[70ch] list-decimal space-y-1 pl-5">
          <li>
            <strong>Count.</strong> For each kind of shot and each area of the court, we count how often {me}{" "}
            lost the point within the next {within === 2 ? "two" : within} shots.
          </li>
          <li>
            <strong>Compare.</strong> We count the same thing for every other player in the same situation.
            A pattern only counts if {me} differs from most pros, not just from {me}&apos;s own average.
          </li>
          <li>
            <strong>Doubt.</strong> Small numbers of shots can mislead, so each difference comes with a range
            of how far off it could be. If that range includes &ldquo;no difference&rdquo;, the card is not shown
            as a finding.
          </li>
          <li>
            <strong>Re-check.</strong> We removed one of {me}&apos;s {int(c.matches)} matches at a time and
            asked whether the pattern was still among the top five. Patterns that came and went are
            marked as leads, not findings.
          </li>
        </ol>
        <p className="max-w-[70ch] text-ink-2">
          <a href="/methods/" className="text-accent underline">
            Read the Methods page
          </a>{" "}
          for the replication results across players and the things that did not work.
        </p>

        <h3 className="pt-2 font-semibold">Where {me} wins and loses points</h3>
        <ZoneExplorer data={data} me={me} />

        {x && (
          <div className="space-y-2 pt-2">
            <h3 className="font-semibold">What we could not do</h3>
            <p className="max-w-[70ch]">{x.plain_note}</p>
            {finishing.length > 0 && (
              <>
                <h3 className="font-semibold">Finishing</h3>
                <ul className="space-y-2">
                  {finishing.map((r) => (
                    <li key={r.label} className="max-w-[70ch] rounded border border-line bg-surface p-3">
                      {r.plain}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}

        <Reveal label="Show the technical tables" className="pt-2">
          <p className="max-w-[70ch]">
            All comparisons: {me}&apos;s rate of losing the point within {within} shots after a shot, next to the
            same rate for typical pros (all other players in the same situation), with Newcombe&apos;s 95% interval
            on the difference. Minimum n = {data.settings.min_n} on both sides. Zones are from the receiver&apos;s
            point of view; rally-ending errors (out, net) are excluded. Baselines: {pct(data.danger.all?.baseline_faced ?? null, 1)}{" "}
            over all shots {me} faces, {pct(data.danger.all?.baseline_hit ?? null, 1)} over all shots {me} plays.
          </p>
          <h4 className="font-semibold">Ranked insights (the report&apos;s top-5)</h4>
          <ol className="space-y-2">
            {data.insights.top.map((i) => (
              <li key={keyOf(i)} className="rounded border border-line bg-surface p-3">
                <p>
                  <span className="mr-1 font-semibold">#{i.rank}</span>
                  {i.text}
                </p>
                <div className="mt-1 flex flex-wrap gap-1">
                  {i.tentative && <Badge variant="warn">tentative</Badge>}
                  {i.borderline && <Badge variant="warn">possible, not confident</Badge>}
                  <Badge>n={int(i.n)}</Badge>
                  <Badge>
                    selected in {i.selected_folds} of {i.folds} folds
                  </Badge>
                </div>
                <PlainFlags flags={i.flags} />
              </li>
            ))}
          </ol>
          {data.insights.less_stable.length > 0 && (
            <>
              <h4 className="font-semibold">Less stable (selected in fewer than half of the folds)</h4>
              <ul className="space-y-2">
                {data.insights.less_stable.map((i) => (
                  <li key={keyOf(i)} className="rounded border border-warn-line bg-surface p-3">
                    {i.text}
                  </li>
                ))}
              </ul>
            </>
          )}
          <h4 className="font-semibold">Shots {me} faces</h4>
          <RateTable rows={data.danger.all?.faced ?? []} caption={`Shots ${me} faces`} first="opponent shot → zone" outcome={`lost within ${within}`} limit={12} />
          <h4 className="font-semibold">Shots {me} plays</h4>
          <RateTable rows={data.danger.all?.hit ?? []} caption={`Shots ${me} plays`} first="shot → opponent zone" outcome={`lost within ${within}`} limit={12} />
          {data.danger.game3 && (
            <>
              <h4 className="font-semibold">Game 3 only</h4>
              <RateTable rows={data.danger.game3.faced ?? []} caption={`Game 3, shots ${me} faces`} first="opponent shot → zone" outcome={`lost within ${within}`} limit={8} />
              <RateTable rows={data.danger.game3.hit ?? []} caption={`Game 3, shots ${me} plays`} first="shot → opponent zone" outcome={`lost within ${within}`} limit={8} />
            </>
          )}
          {data.danger.pressure && (
            <>
              <h4 className="font-semibold">At {data.settings.pressure_from}+ only</h4>
              <RateTable rows={data.danger.pressure.faced ?? []} caption={`At ${data.settings.pressure_from}+, shots ${me} faces`} first="opponent shot → zone" outcome={`lost within ${within}`} limit={8} />
              <RateTable rows={data.danger.pressure.hit ?? []} caption={`At ${data.settings.pressure_from}+, shots ${me} plays`} first="shot → opponent zone" outcome={`lost within ${within}`} limit={8} />
            </>
          )}
          {x && (
            <>
              <h4 className="font-semibold">Expected points (xP): a negative result</h4>
              <p>{x.caveat}</p>
              <p>
                Holdout AUC {num(x.auc_nonfinal)} on non-final strokes (chance 0.50), {num(x.auc_final)} on final
                strokes, {num(x.leaky_auc_final, 3)} with the final landing zone leaked. {me}&apos;s points above
                expectation per rally: {num(x.overall.mean, 3, true)} (95% CI {numCi(x.overall.lo, x.overall.hi, 3, true)}, n=
                {int(x.overall.n)}); other pros {num(x.overall.ref_mean, 3, true)}.
              </p>
              <XpTable rows={x.finishing} caption="Finishing" first="final shot" value="points above expectation" unit="strokes" />
              <XpTable rows={x.by_shot} caption="Points above expectation by shot" first="shot" value="points above expectation" unit="rallies" withOwn />
            </>
          )}
          <p className="text-ink-2">
            Rally win rate {pct(c.win_rate, 1)} (95% CI {pctCi(c.win_lo, c.win_hi)}); {c.holdout_matches} of{" "}
            {c.matches} matches are in the holdout set. Generated {data.generated} by{" "}
            <code className="text-xs">{data.command}</code>.
          </p>
        </Reveal>
      </Section>
    </div>
  );
}
