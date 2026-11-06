import { useId } from "react";
import type { RallyStroke } from "@/lib/types";
import { ArrowMarkers, Board, CourtLines, HalfLabels, SCALE_WITH_CONTAINER, fromFull, px, py } from "./Geometry";
import { BOARD, FONT, SIZES } from "./theme";

/** A gentle quadratic curve from a to b: the bow is proportional to the length and capped. */
function curve(a: { X: number; Y: number }, b: { X: number; Y: number }): string {
  const dx = b.X - a.X;
  const dy = b.Y - a.Y;
  const len = Math.hypot(dx, dy) || 1;
  const bow = Math.min(0.16 * len, 1.0); // metres
  const nx = -dy / len;
  const ny = dx / len;
  const cx = (a.X + b.X) / 2 + nx * bow;
  const cy = (a.Y + b.Y) / 2 + ny * bow;
  return `M ${px(a.X)} ${py(a.Y)} Q ${px(cx)} ${py(cy)} ${px(b.X)} ${py(b.Y)}`;
}

/**
 * One rally on the board, the player on the left: each stroke is a curve from where it was hit
 * to where it landed. The key shot (the one the card is about) is gold and thick; the player's
 * other shots are solid light grey, the opponent's dashed slate. Numbered dots mark each hit
 * point; a cross marks where the rally ended. `range` limits the drawing to stroke numbers
 * [from, to] (inclusive); without it the whole rally is drawn.
 */
export function RallyCourt({
  strokes,
  me,
  title,
  range,
}: {
  strokes: RallyStroke[];
  me: string;
  title: string;
  range?: [number, number];
}) {
  const uid = useId();
  const inRange = (s: RallyStroke) => !range || (s.no >= range[0] && s.no <= range[1]);
  const drawable = strokes.filter((s) => s.from && s.to);
  const drawn = drawable.filter(inRange);
  const last = drawable[drawable.length - 1];
  const showEnd = last && drawn.includes(last);
  const skipped = strokes.length - drawable.length;
  return (
    <Board
      uid={uid}
      title={title}
      legend={`Solid: ${me} · dashed: opponent · gold: the shot this tip is about · ✕: where the rally ended${
        skipped ? ` · ${skipped} of ${strokes.length} shots had no recorded landing point` : ""
      }`}
    >
      <ArrowMarkers id={uid} />
      <CourtLines />
      <HalfLabels me={me} />
      {drawn.map((s) => {
        const a = fromFull(...(s.from as [number, number]));
        const b = fromFull(...(s.to as [number, number]));
        const colour = s.highlight ? BOARD.gold : s.by === "me" ? BOARD.me : BOARD.opp;
        const marker = s.highlight ? "gold" : s.by;
        const label = `${s.no}. ${s.by === "me" ? me : "opponent"}: ${s.shot.replace(/_/g, " ")}${s.highlight ? " (this is the shot)" : ""}`;
        return (
          <g key={s.no} aria-label={label} role="img">
            <path
              d={curve(a, b)}
              fill="none"
              stroke={colour}
              strokeWidth={s.highlight ? SIZES.keyW : SIZES.shotW}
              strokeOpacity={s.highlight ? 1 : 0.88}
              strokeLinecap="round"
              strokeDasharray={s.by === "opp" && !s.highlight ? "14 10" : undefined}
              markerEnd={`url(#${uid}-${marker})`}
            />
          </g>
        );
      })}
      {drawn.map((s) => {
        const a = fromFull(...(s.from as [number, number]));
        return (
          <g key={`dot-${s.no}`} aria-hidden="true" style={SCALE_WITH_CONTAINER}>
            <circle cx={px(a.X)} cy={py(a.Y)} r={SIZES.dotR} fill={s.highlight ? BOARD.gold : BOARD.opp} />
            <text
              x={px(a.X)}
              y={py(a.Y) + SIZES.fontSmall * 0.36}
              textAnchor="middle"
              fill={s.highlight ? BOARD.goldInk : BOARD.slateInk}
              style={{ fontSize: `${SIZES.fontSmall}px`, fontFamily: FONT, fontWeight: 700 }}
            >
              {s.no}
            </text>
          </g>
        );
      })}
      {showEnd &&
        (() => {
          const e = fromFull(...(last.to as [number, number]));
          const r = SIZES.dotR * 0.8;
          return (
            <g aria-label="where the rally ended" role="img" stroke={BOARD.net} strokeWidth={SIZES.shotW + 1} strokeLinecap="round" style={SCALE_WITH_CONTAINER}>
              <line x1={px(e.X) - r} y1={py(e.Y) - r} x2={px(e.X) + r} y2={py(e.Y) + r} />
              <line x1={px(e.X) - r} y1={py(e.Y) + r} x2={px(e.X) + r} y2={py(e.Y) - r} />
            </g>
          );
        })()}
    </Board>
  );
}
