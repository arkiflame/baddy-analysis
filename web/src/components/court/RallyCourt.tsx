import { useId } from "react";
import type { RallyStroke } from "@/lib/types";
import { ArrowMarkers, CourtLines, HALF_W, L, px, py, viewBox } from "./Geometry";

/**
 * One rally drawn on a full court, the player's half at the bottom: every stroke is an arrow
 * from where it was hit to where it landed, numbered in order. The stroke the insight is about
 * is drawn thicker with a halo. Strokes without a recorded endpoint are skipped.
 */
export function RallyCourt({ strokes, me, title }: { strokes: RallyStroke[]; me: string; title: string }) {
  const uid = useId();
  const v = viewBox("full");
  const drawn = strokes.filter((s) => s.from && s.to);
  return (
    <figure className="mx-auto w-full max-w-[560px]">
      <svg viewBox={v.vb} role="img" aria-labelledby={`${uid}-t`} className="h-auto w-full select-none">
        <title id={`${uid}-t`}>{title}</title>
        <ArrowMarkers id={uid} />
        <CourtLines view="full" />
        <text x={px(HALF_W)} y={py(0) - 16} textAnchor="middle" fontSize="18" fill="var(--court-white)" aria-hidden="true">
          opponent
        </text>
        <text x={px(HALF_W)} y={py(L) + 34} textAnchor="middle" fontSize="18" fill="var(--court-white)" aria-hidden="true">
          {me}
        </text>
        {drawn.map((s) => {
          const [x1, y1] = s.from as [number, number];
          const [x2, y2] = s.to as [number, number];
          const colour = s.by === "me" ? "var(--stroke-me)" : "var(--stroke-opp)";
          const w = s.highlight ? 10 : 5;
          const label = `${s.no}. ${s.by === "me" ? me : "opponent"}: ${s.shot.replace(/_/g, " ")}${s.highlight ? " (this is the shot)" : ""}`;
          return (
            <g key={s.no} aria-label={label} role="img">
              {s.highlight && (
                <line x1={px(x1)} y1={py(y1)} x2={px(x2)} y2={py(y2)} stroke="#ffffff" strokeOpacity="0.45" strokeWidth={w + 14} strokeLinecap="round" />
              )}
              <line x1={px(x1)} y1={py(y1)} x2={px(x2)} y2={py(y2)} stroke="var(--stroke-outline)" strokeWidth={w + 3} strokeLinecap="round" />
              <line
                x1={px(x1)}
                y1={py(y1)}
                x2={px(x2)}
                y2={py(y2)}
                stroke={colour}
                strokeWidth={w}
                strokeLinecap="round"
                markerEnd={`url(#${uid}-${s.by})`}
              />
              <circle cx={px(x1)} cy={py(y1)} r={16} fill={colour} stroke="var(--stroke-outline)" strokeWidth="2" />
              <text x={px(x1)} y={py(y1) + 6} textAnchor="middle" fontSize="17" fontWeight="700" fill="#0b0b0b">
                {s.no}
              </text>
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-1 text-xs text-ink-2">
        White arrows: {me}&apos;s shots. Yellow arrows: the opponent&apos;s. The thick arrow is the shot this
        insight is about. Numbers give the order.
        {drawn.length < strokes.length ? ` ${strokes.length - drawn.length} of ${strokes.length} strokes had no recorded landing point and are not drawn.` : ""}
      </figcaption>
    </figure>
  );
}
