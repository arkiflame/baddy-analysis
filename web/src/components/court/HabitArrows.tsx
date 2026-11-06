import { useId } from "react";
import { aShot, areaShort, shotWords, wholePct } from "@/lib/format";
import { type Band, ArrowMarkers, Board, CourtLines, HalfLabels, L, Pill, S, SCALE_WITH_CONTAINER, W, halfRect, px, py, zoneCentre, zoneRects } from "./Geometry";
import { BOARD, SIZES } from "./theme";

export interface HabitReply {
  reply: string; // "smash -> mid_fh" or "smash"
  rate: number; // share of the player's replies in this situation
  ref_rate: number; // the same share for most pros
  n: number;
}

export const HABIT_ARROWS = 3; // replies drawn per board; the rest are listed as text

const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** Where a reply's pill goes: past the arrowhead along the arrow, pulled back inside the board
 *  when that would clip, and lifted above the line for short arrows so it never sits on one. */
function pillSpot(target: { X: number; Y: number }, ux: number, uy: number, len: number, text: string, awayFromOrigin: number) {
  const halfW = (text.length * SIZES.fontSmall * 0.58 + SIZES.fontSmall * 0.9) / 2 / S; // metres
  let X = target.X + ux * 0.95;
  let Y = target.Y + uy * 0.35;
  if (X + halfW > L + 0.3) X = Math.min(target.X, L + 0.3 - halfW);
  if (len < 2.6) Y = target.Y + awayFromOrigin * 0.5; // short arrow: the pill goes on the side the origin pill is not on
  Y = Math.max(0.35, Math.min(W - 0.35, Y));
  return { X, Y };
}

/**
 * "After a clear to the back backhand corner, where does the player hit next?" One origin dot
 * where the incoming shot lands on the player's half; an arrow to each of the three most common
 * landing areas on the opponent's half, thicker when chosen more often, the most common one
 * gold. Each arrow ends in a pill ("Smash 75%"); pills that would share a spot are nudged apart.
 * "Most pros" shares go in the legend line, not on the board.
 */
export function HabitArrows({
  situation,
  replies,
  me,
  fhOnRight,
  frame,
  title,
}: {
  situation: string;
  replies: HabitReply[];
  me: string;
  fhOnRight: boolean;
  frame: { coach_bands: Band[] };
  title: string;
}) {
  const uid = useId();
  const [inShot, inZone] = situation.split(" -> ");
  const origin =
    inZone && inZone !== "any"
      ? (zoneRects(frame.coach_bands, "player", fhOnRight).find((z) => z.zone === inZone) ?? halfRect("player"))
      : halfRect("player");
  const o = { X: origin.x + origin.w / 2, Y: origin.y + origin.h / 2 };
  const sorted = [...replies].sort((a, b) => b.rate - a.rate).slice(0, HABIT_ARROWS);
  // the origin pill goes below the dot when the arrows head upward, above when they head down
  const meanDy = sorted.reduce((s, r) => s + (zoneCentre(r.reply.split(" -> ")[1] ?? null, frame.coach_bands, "opponent", fhOnRight).Y - o.Y), 0);
  const originSide = meanDy < 0 ? 1 : -1;
  const seen: Record<string, number> = {};
  const items = sorted.map((r, i) => {
    const [shot, zone] = r.reply.split(" -> ");
    const t = zoneCentre(zone ?? null, frame.coach_bands, "opponent", fhOnRight);
    const key = zone ?? "any";
    const k = seen[key] ?? 0;
    seen[key] = k + 1;
    // nudge arrows and pills that share a landing area: alternate above / below the centre
    const nudge = k === 0 ? 0 : k === 1 ? -0.55 : 0.55;
    const target = { X: t.X, Y: t.Y + nudge };
    const dx = target.X - o.X;
    const dy = target.Y - o.Y;
    const len = Math.hypot(dx, dy) || 1;
    const ux = dx / len;
    const uy = dy / len;
    return {
      r,
      shot,
      zone,
      gold: i === 0,
      w: Math.max(SIZES.arrowMin, SIZES.arrowMax * r.rate),
      end: { X: target.X - ux * 0.1, Y: target.Y - uy * 0.1 }, // the head stops at the landing spot
      pill: pillSpot(target, ux, uy, len, `${cap(shotWords(shot))} ${wholePct(r.rate)}`, -originSide),
      label: `${cap(shotWords(shot))} ${wholePct(r.rate)}`,
      aria: `${shotWords(shot)} ${wholePct(r.rate)} of the time, to the ${zone ? areaShort(zone) : "opponent's half"}; most pros ${wholePct(r.ref_rate)}`,
    };
  });
  const legend = `Gold: most common · most pros: ${items
    .map((it) => `${shotWords(it.shot)} ${wholePct(it.r.ref_rate)}`)
    .join(", ")}`;

  return (
    <Board uid={uid} title={title} legend={legend}>
      <ArrowMarkers id={uid} />
      <CourtLines />
      <HalfLabels me={me} />
      {/* origin: where the incoming shot lands, so where the player hits from */}
      <g aria-label={`${aShot(inShot)} lands here`} role="img">
        <g style={SCALE_WITH_CONTAINER}>
          <circle cx={px(o.X)} cy={py(o.Y)} r={SIZES.dotR * 0.9} fill={BOARD.me} />
        </g>
        <Pill x={px(o.X)} y={py(o.Y) + originSide * SIZES.dotR * 2.6} text={`${cap(aShot(inShot))} lands here`} />
      </g>
      {items.map((it) => (
        <g key={it.r.reply} role="img" aria-label={it.aria}>
          <line
            x1={px(o.X)}
            y1={py(o.Y)}
            x2={px(it.end.X)}
            y2={py(it.end.Y)}
            stroke={it.gold ? BOARD.gold : BOARD.opp}
            strokeWidth={it.w}
            strokeLinecap="round"
            markerEnd={`url(#${uid}-${it.gold ? "gold" : "opp"})`}
          />
        </g>
      ))}
      {items.map((it) => (
        <Pill key={`pill-${it.r.reply}`} x={px(it.pill.X)} y={py(it.pill.Y)} text={it.label} gold={it.gold} />
      ))}
    </Board>
  );
}
