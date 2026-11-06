import { useId } from "react";
import { aShot, areaShort, shotWords, wholePct } from "@/lib/format";
import {
  type Band,
  ArrowMarkers,
  CourtLines,
  HALF_W,
  L,
  S,
  SideLabels,
  halfRect,
  px,
  py,
  sideLabelsFor,
  viewBox,
  zoneCentre,
  zoneRects,
} from "./Geometry";

export interface HabitReply {
  reply: string; // "smash -> mid_fh" or "smash"
  rate: number; // share of the player's replies in this situation
  ref_rate: number; // the same share for most pros
  n: number;
}

/**
 * "After a clear to the back backhand corner, where does the player hit next?" The incoming
 * shot's landing zone is marked on the player's half; one arrow per reply goes to the zone it
 * targets on the opponent's half, thicker when the player chooses it more often.
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
  const v = viewBox("full");
  const [inShot, inZone] = situation.split(" -> ");
  const origin =
    inZone && inZone !== "any"
      ? (zoneRects(frame.coach_bands, "player", fhOnRight).find((z) => z.zone === inZone) ?? halfRect("player"))
      : halfRect("player");
  const o = { X: origin.x + origin.w / 2, Y: origin.y + origin.h / 2 };
  const labels = sideLabelsFor("player", me, fhOnRight);
  const topLabels = sideLabelsFor("opponent", me, fhOnRight);
  const sorted = [...replies].sort((a, b) => b.rate - a.rate);
  const stack: Record<string, number> = {}; // labels per target zone, stacked downward

  return (
    <figure className="mx-auto w-full max-w-[560px]">
      <svg viewBox={v.vb} role="img" aria-labelledby={`${uid}-t`} className="h-auto w-full select-none">
        <title id={`${uid}-t`}>{title}</title>
        <ArrowMarkers id={uid} />
        <CourtLines view="full" />
        <SideLabels half="opponent" left={topLabels.left} right={topLabels.right} />
        <SideLabels half="player" left={labels.left} right={labels.right} />
        <g aria-label={`${aShot(inShot)} lands here`} role="img">
          <rect
            x={px(origin.x) + 4}
            y={py(origin.y) + 4}
            width={origin.w * S - 8}
            height={origin.h * S - 8}
            rx={6}
            fill="#ffffff"
            fillOpacity="0.22"
            stroke="var(--court-white)"
            strokeWidth="3"
            strokeDasharray="10 8"
          />
          <text x={px(o.X)} y={py(Math.min(o.Y + 0.9, L - 1.1))} textAnchor="middle" fontSize="17" fontWeight="600" fill="var(--court-white)">
            {aShot(inShot)} lands here
          </text>
        </g>
        {sorted.map((r, i) => {
          const [shot, zone] = r.reply.split(" -> ");
          const t = zoneCentre(zone ?? null, frame.coach_bands, "opponent", fhOnRight);
          const w = Math.max(2, Math.min(14, 2 + 12 * r.rate));
          // shorten the arrow so the head stops inside the target zone
          const dx = t.X - o.X;
          const dy = t.Y - o.Y;
          const len = Math.hypot(dx, dy) || 1;
          const ex = t.X - (dx / len) * 0.35;
          const ey = t.Y - (dy / len) * 0.35;
          const label = `${shotWords(shot)} ${wholePct(r.rate)}`;
          const sub = `most pros ${wholePct(r.ref_rate)}`;
          const slot = stack[zone ?? "any"] ?? 0;
          stack[zone ?? "any"] = slot + 1;
          const ly = py(t.Y) - 20 + slot * 40;
          return (
            <g key={`${r.reply}-${i}`} role="img" aria-label={`${label} to the ${zone ? areaShort(zone) : "opponent's half"}; ${sub}`}>
              <line x1={px(o.X)} y1={py(o.Y)} x2={px(ex)} y2={py(ey)} stroke="var(--stroke-outline)" strokeWidth={w + 3} strokeLinecap="round" strokeOpacity="0.6" />
              <line
                x1={px(o.X)}
                y1={py(o.Y)}
                x2={px(ex)}
                y2={py(ey)}
                stroke="var(--stroke-opp)"
                strokeWidth={w}
                strokeLinecap="round"
                markerEnd={`url(#${uid}-habit)`}
              />
              <rect x={px(t.X) - 92} y={ly - 17} width={184} height={36} rx={5} fill="var(--stroke-outline)" fillOpacity="0.72" />
              <text x={px(t.X)} y={ly - 2} textAnchor="middle" fontSize="15" fontWeight="600" fill="#ffffff">
                {label}
              </text>
              <text x={px(t.X)} y={ly + 14} textAnchor="middle" fontSize="12" fill="#ffffff">
                {sub}
              </text>
            </g>
          );
        })}
        <text x={px(HALF_W)} y={py(0) - 42} textAnchor="middle" fontSize="14" fill="var(--court-white)" aria-hidden="true">
          where {me} hits next
        </text>
      </svg>
      <figcaption className="mt-1 text-xs text-ink-2">
        Thicker arrow = {me} plays it more often. Only replies seen often enough to compare are drawn.
      </figcaption>
    </figure>
  );
}
