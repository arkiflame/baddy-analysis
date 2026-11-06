"use client";

import { useId, useMemo, useState } from "react";
import type { RateRow } from "@/lib/types";
import { areaShort, freqPair } from "@/lib/format";
import {
  type Band,
  type Half,
  CourtLines,
  NET,
  S,
  SideLabels,
  px,
  py,
  sideLabelsFor,
  toFull,
  viewBox,
  zoneRects,
} from "./Geometry";

export interface ZoneCourtFrame {
  coach_bands: Band[];
  body_radius_m: number;
}

type Status = "strong" | "weak" | "none" | "few";

function statusOf(r: RateRow | undefined, minN: number): Status {
  if (!r || r.n < minN || !r.reliable || r.delta === null) return "few";
  if (!r.signal) return "none";
  return r.delta < 0 ? "strong" : "weak";
}

function fillFor(st: Status): string {
  return st === "strong" ? "var(--zone-strong)" : st === "weak" ? "var(--zone-weak)" : "none";
}

function line2(st: Status, me: string, short = false): string {
  if (st === "strong") return short ? "wins more" : `${me} wins more here`;
  if (st === "weak") return short ? "loses more" : `${me} loses more here`;
  if (st === "none") return short ? "no clear diff." : "no clear difference";
  return short ? "too few" : "too few shots";
}

function describe(r: RateRow | undefined, st: Status, me: string, minN: number): string[] {
  if (st === "few") return [`Too few shots here to say (fewer than ${minN}).`];
  if (!r || r.ref_rate === null) return [`${me} loses the point quickly here; no comparison available.`];
  const [f1, f2] = freqPair(r.rate, r.ref_rate);
  return [
    `${me} loses the point quickly ${f1} here.`,
    `Most pros: ${f2}.`,
    st === "none" ? "The difference is too small to be sure of." : line2(st, me) + ".",
  ];
}

interface Tip {
  x: number; // % of width
  y: number; // % of height
  title: string;
  lines: string[];
}

/**
 * One half of the court with the six coach zones and the body circle, each filled by what the
 * numbers say: blue "wins more here", red "loses more here", plain green otherwise. role
 * "faced" draws the player's own half (shots the player receives); "hit" draws the opponent's
 * half (where the player's own shots land).
 */
export function ZoneCourt({
  frame,
  fhOnRight,
  me,
  rows,
  role,
  within,
  minN,
  bodyAt,
  title,
}: {
  frame: ZoneCourtFrame;
  fhOnRight: boolean;
  me: string;
  rows: RateRow[];
  role: "faced" | "hit";
  within: number;
  minN: number;
  bodyAt: { x: number; y: number }; // half-court frame: toward the player's right, from the net
  title: string;
}) {
  const uid = useId();
  const [tip, setTip] = useState<Tip | null>(null);
  const half: Half = role === "faced" ? "player" : "opponent";
  const v = viewBox(half);
  const byZone = useMemo(() => new Map(rows.filter((r) => r.zone).map((r) => [r.zone as string, r])), [rows]);
  const zones = zoneRects(frame.coach_bands, half, fhOnRight);
  const labels = sideLabelsFor(half, me, fhOnRight);
  const body = toFull(bodyAt.x, bodyAt.y, half);
  const rr = frame.body_radius_m * S;

  const pct = (X: number, Y: number) => ({ x: ((px(X) - v.x0) / v.w) * 100, y: ((py(Y) - v.y0) / v.h) * 100 });

  return (
    <div className="relative mx-auto w-full max-w-[560px]">
      <svg viewBox={v.vb} role="img" aria-labelledby={`${uid}-t`} className="h-auto w-full select-none" onMouseLeave={() => setTip(null)}>
        <title id={`${uid}-t`}>{title}</title>
        <CourtLines view={half} />
        {zones.map((z) => {
          const r = byZone.get(z.zone);
          const st = statusOf(r, minN);
          const lines = describe(r, st, me, minN);
          const cx = z.x + z.w / 2;
          // keep text clear of the doubles long service line in the rear band
          const nearBase = half === "player" ? z.y + z.h > 13 : z.y < 0.4;
          const cy = nearBase ? (half === "player" ? z.y + z.h / 2 - 0.3 : z.y + z.h / 2 + 0.3) : z.y + z.h / 2;
          const t = pct(cx, cy);
          const tipObj = { ...t, title: areaShort(z.zone), lines };
          return (
            <g
              key={z.zone}
              tabIndex={0}
              role="img"
              aria-label={`${areaShort(z.zone)}: ${lines.join(" ")}`}
              onMouseEnter={() => setTip(tipObj)}
              onFocus={() => setTip(tipObj)}
              onBlur={() => setTip(null)}
            >
              <rect x={px(z.x) + 4} y={py(z.y) + 4} width={z.w * S - 8} height={z.h * S - 8} rx={6} fill={fillFor(st)} fillOpacity={st === "strong" || st === "weak" ? 0.92 : 0} />
              <text x={px(cx)} y={py(cy) - 6} textAnchor="middle" fontSize="19" fontWeight="600" fill="var(--zone-ink)">
                {areaShort(z.zone)}
              </text>
              <text x={px(cx)} y={py(cy) + 18} textAnchor="middle" fontSize="16" fill="var(--zone-ink)">
                {line2(st, me)}
              </text>
            </g>
          );
        })}
        {(() => {
          const r = byZone.get("body");
          const st = statusOf(r, minN);
          const lines = describe(r, st, me, minN);
          const t = pct(body.X, body.Y);
          const tipObj = { ...t, title: "straight at the body", lines };
          return (
            <g
              tabIndex={0}
              role="img"
              aria-label={`Straight at the body: ${lines.join(" ")}`}
              onMouseEnter={() => setTip(tipObj)}
              onFocus={() => setTip(tipObj)}
              onBlur={() => setTip(null)}
            >
              <circle cx={px(body.X)} cy={py(body.Y)} r={rr} fill={st === "strong" || st === "weak" ? fillFor(st) : "var(--court-green)"} stroke="var(--court-white)" strokeWidth="3" />
              <text x={px(body.X)} y={py(body.Y) - 4} textAnchor="middle" fontSize="15" fontWeight="600" fill="var(--zone-ink)">
                body
              </text>
              <text x={px(body.X)} y={py(body.Y) + 14} textAnchor="middle" fontSize="12" fill="var(--zone-ink)">
                {line2(st, me, true)}
              </text>
            </g>
          );
        })()}
        <SideLabels half={half} left={labels.left} right={labels.right} />
        <text x={px(0)} y={half === "player" ? py(NET) - 28 : py(NET) + 40} fontSize="15" fill="var(--court-white)">
          {half === "player" ? `${me}'s half: shots ${me} receives` : `opponent's half: where ${me}'s shots land`}
        </text>
      </svg>
      {tip && (
        <div
          role="tooltip"
          className="pointer-events-none absolute z-10 w-64 -translate-x-1/2 -translate-y-full rounded border border-line bg-surface p-2 text-xs shadow"
          style={{ left: `${Math.min(Math.max(tip.x, 25), 75)}%`, top: `${tip.y}%` }}
        >
          <div className="font-semibold">{tip.title}</div>
          {tip.lines.map((l, i) => (
            <div key={i} className="text-ink-2">
              {l}
            </div>
          ))}
          <div className="mt-1 text-ink-2">&ldquo;Quickly&rdquo; means within the next {within} shots.</div>
        </div>
      )}
    </div>
  );
}

/** Three swatches with words; the words carry the meaning. */
export function ZoneLegend({ me }: { me: string }) {
  const sw = (bg: string, border: string) => (
    <span className="inline-block h-3.5 w-6 rounded-sm border" style={{ background: bg, borderColor: border }} />
  );
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-ink-2">
      <li className="inline-flex items-center gap-1.5">
        {sw("var(--zone-strong)", "var(--zone-strong)")} {me} wins more here
      </li>
      <li className="inline-flex items-center gap-1.5">
        {sw("var(--zone-weak)", "var(--zone-weak)")} {me} loses more here
      </li>
      <li className="inline-flex items-center gap-1.5">
        {sw("var(--court-green)", "var(--court-green)")} no clear difference or too few shots
      </li>
    </ul>
  );
}
