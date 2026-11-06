"use client";

import { useId, useMemo, useState } from "react";
import type { RateRow } from "@/lib/types";
import { areaShort, freqPair } from "@/lib/format";
import {
  type Band,
  type Half,
  Board,
  CourtLines,
  HalfLabels,
  Pill,
  S,
  VIEW_H,
  VIEW_W,
  fromHalf,
  px,
  py,
  zoneRects,
} from "./Geometry";
import { BOARD, SIZES } from "./theme";

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

function tint(st: Status): string | undefined {
  return st === "strong" ? BOARD.tealTint : st === "weak" ? BOARD.goldTint : undefined;
}

function line2(st: Status, me: string, short = false): string {
  if (st === "strong") return short ? "wins more" : `${me} wins more here`;
  if (st === "weak") return short ? "loses more" : `${me} loses more here`;
  if (st === "none") return short ? "about the same" : "about the same";
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

const shortArea = (zone: string) => areaShort(zone).replace(", forehand side", " forehand").replace(", backhand side", " backhand");

/**
 * The win / loss map: the six coach zones and the body circle of one half as tinted tiles
 * inside the court lines. Teal tint: the player wins more here than most pros; gold tint: loses
 * more; no tint: about the same or too few shots. role "faced" tints the player's half (shots the
 * player receives); "hit" tints the opponent's half (where the player's own shots land).
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
  const byZone = useMemo(() => new Map(rows.filter((r) => r.zone).map((r) => [r.zone as string, r])), [rows]);
  const zones = zoneRects(frame.coach_bands, half, fhOnRight);
  const body = fromHalf(bodyAt.x, bodyAt.y, half);
  const rr = frame.body_radius_m * S;
  const pct = (X: number, Y: number) => ({ x: (px(X) / VIEW_W) * 100, y: (py(Y) / VIEW_H) * 100 });
  const legend = `Teal tint: ${me} wins more here · gold tint: ${me} loses more here · no tint: about the same or too few shots`;

  return (
    <div className="relative">
      <Board uid={uid} title={title} legend={legend} onMouseLeave={() => setTip(null)}>
        <CourtLines />
        <HalfLabels me={me} />
        {zones.map((z) => {
          const r = byZone.get(z.zone);
          const st = statusOf(r, minN);
          const lines = describe(r, st, me, minN);
          const cx = z.x + z.w / 2;
          const cy = z.y + z.h / 2;
          const t = pct(cx, cy);
          const tipObj = { ...t, title: areaShort(z.zone), lines };
          const fill = tint(st);
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
              <rect x={px(z.x) + 3} y={py(z.y) + 3} width={z.w * S - 6} height={z.h * S - 6} rx={4} fill={fill ?? "transparent"} />
              <Pill x={px(cx)} y={py(cy) - SIZES.fontSmall * 0.85} text={shortArea(z.zone)} />
              <Pill x={px(cx)} y={py(cy) + SIZES.fontSmall * 0.85} text={line2(st, me, true)} gold={st === "weak"} />
            </g>
          );
        })}
        {(() => {
          const r = byZone.get("body");
          const st = statusOf(r, minN);
          const lines = describe(r, st, me, minN);
          const t = pct(body.X, body.Y);
          const tipObj = { ...t, title: "straight at the body", lines };
          const fill = tint(st);
          return (
            <g
              tabIndex={0}
              role="img"
              aria-label={`Straight at the body: ${lines.join(" ")}`}
              onMouseEnter={() => setTip(tipObj)}
              onFocus={() => setTip(tipObj)}
              onBlur={() => setTip(null)}
            >
              <circle cx={px(body.X)} cy={py(body.Y)} r={rr} fill={fill ?? BOARD.bg} fillOpacity={fill ? 1 : 0.6} stroke={BOARD.line} strokeWidth={SIZES.lineW} />
              <Pill x={px(body.X)} y={py(body.Y)} text={`body · ${line2(st, me, true)}`} gold={st === "weak"} />
            </g>
          );
        })()}
      </Board>
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

/** The legend now lives inside the board; kept as a no-op export for callers. */
export function ZoneLegend(_props: { me: string }) {
  void _props;
  return null;
}
