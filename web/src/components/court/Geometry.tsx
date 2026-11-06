/* Court geometry shared by the court components (D33): a real singles court drawn to scale in
   LANDSCAPE, the scouted player on the LEFT, the opponent on the right, the net vertical in the
   middle.

   Board frame, in metres: X along the court (0..13.40, the player's baseline at 0, the net at
   6.70), Y across it (0..6.10, top to bottom of the screen). A right-handed player on the left
   faces the net, so their right hand (forehand side) is the BOTTOM of the screen; the opponent
   faces left, so a right-handed opponent's forehand side is the TOP.

   The data arrive in two older frames and are converted here:
   - full-court frame (example rallies): fx across 0..6.10, fy along 0..13.40, the player's
     half being fy > 6.70 (`fromFull`);
   - half-court frame (zone tables, base position): x toward the player's own right, y from the
     net into that player's half (`fromHalf`). */

import type { ReactNode } from "react";
import { BOARD, FONT, SIZES } from "./theme";

export const W = 6.1; // across
export const L = 13.4; // along
export const NET = 6.7;
export const SINGLES_HALF = 2.59;
export const HALF_W = 3.05;
export const SHORT_SERVICE = 1.98;
export const DOUBLES_LONG_FROM_BASE = 0.76;

export const S = 100; // units per metre
const MX = 0.4; // metres of panel left and right of the court
const MT = 0.62; // metres above the court (room for the half labels)
const MB = 0.3; // metres below
export const VIEW_W = (L + 2 * MX) * S;
export const VIEW_H = (W + MT + MB) * S;
export const VIEW_BOX = `0 0 ${VIEW_W} ${VIEW_H}`;

export type Half = "player" | "opponent";

export interface Band {
  name: string;
  lo: number;
  hi: number;
}

export interface ZoneRect {
  zone: string;
  x: number; // board metres, left edge (along the court)
  y: number; // top edge (across)
  w: number;
  h: number;
}

export const px = (X: number) => (X + MX) * S;
export const py = (Y: number) => (Y + MT) * S;

/** Full-court frame (player at the bottom) -> board frame (player on the left). */
export function fromFull(fx: number, fy: number): { X: number; Y: number } {
  return { X: L - fy, Y: fx };
}

/** Half-court frame (x toward the player's own right, y from the net) -> board frame. */
export function fromHalf(x: number, y: number, half: Half): { X: number; Y: number } {
  return half === "player" ? { X: NET - y, Y: HALF_W + x } : { X: NET + y, Y: HALF_W - x };
}

/** Is the forehand side at the bottom of the screen for this half? */
export function forehandAtBottom(half: Half, fhOnRight: boolean): boolean {
  return half === "player" ? fhOnRight : false;
}

/** The six coach zones (front/mid/rear x forehand/backhand) of one half as board rectangles. */
export function zoneRects(bands: Band[], half: Half, fhOnRight: boolean): ZoneRect[] {
  const fhBottom = forehandAtBottom(half, fhOnRight);
  const out: ZoneRect[] = [];
  for (const b of bands) {
    const lo = b.lo;
    const hi = Math.min(b.hi, NET);
    for (const side of ["fh", "bh"] as const) {
      const bottom = side === "fh" ? fhBottom : !fhBottom;
      const y = bottom ? HALF_W : HALF_W - SINGLES_HALF;
      const x = half === "player" ? NET - hi : NET + lo;
      out.push({ zone: `${b.name}_${side}`, x, y, w: hi - lo, h: SINGLES_HALF });
    }
  }
  return out;
}

/** Centre of a zone in board metres; "body" and unknown zones -> the half's centre. */
export function zoneCentre(zone: string | null, bands: Band[], half: Half, fhOnRight: boolean): { X: number; Y: number } {
  const r = zone ? zoneRects(bands, half, fhOnRight).find((z) => z.zone === zone) : undefined;
  if (r) return { X: r.x + r.w / 2, Y: r.y + r.h / 2 };
  return { X: half === "player" ? NET / 2 : NET + NET / 2, Y: HALF_W };
}

/** The whole singles half as a rectangle. */
export function halfRect(half: Half): ZoneRect {
  return { zone: "any", x: half === "player" ? 0 : NET, y: HALF_W - SINGLES_HALF, w: NET, h: 2 * SINGLES_HALF };
}

const line = { stroke: BOARD.line, strokeWidth: SIZES.lineW, fill: "none" } as const;

/** Pills, dots and badges grow with `--court-font-scale` (set per container width in
 *  court.css) around their own centre, so they stay readable when the board is narrow. */
export const SCALE_WITH_CONTAINER = {
  transformBox: "fill-box",
  transformOrigin: "center",
  transform: "scale(var(--court-font-scale, 1))",
} as const;

/** The board: dark panel, the court to scale with singles sidelines, short and long service
 *  lines, centre lines, and the net extending a little past the sidelines. */
export function CourtLines() {
  return (
    <g aria-hidden="true">
      <rect x={0} y={0} width={VIEW_W} height={VIEW_H} fill={BOARD.bg} />
      <rect x={px(0)} y={py(0)} width={NET * S} height={W * S} fill={BOARD.myHalf} />
      <rect x={px(NET)} y={py(0)} width={NET * S} height={W * S} fill={BOARD.surface} />
      {/* outer (doubles) lines */}
      <rect x={px(0)} y={py(0)} width={L * S} height={W * S} {...line} />
      {/* singles sidelines */}
      <line x1={px(0)} y1={py(HALF_W - SINGLES_HALF)} x2={px(L)} y2={py(HALF_W - SINGLES_HALF)} {...line} />
      <line x1={px(0)} y1={py(HALF_W + SINGLES_HALF)} x2={px(L)} y2={py(HALF_W + SINGLES_HALF)} {...line} />
      {/* short service lines */}
      <line x1={px(NET - SHORT_SERVICE)} y1={py(0)} x2={px(NET - SHORT_SERVICE)} y2={py(W)} {...line} />
      <line x1={px(NET + SHORT_SERVICE)} y1={py(0)} x2={px(NET + SHORT_SERVICE)} y2={py(W)} {...line} />
      {/* doubles long service lines */}
      <line x1={px(DOUBLES_LONG_FROM_BASE)} y1={py(0)} x2={px(DOUBLES_LONG_FROM_BASE)} y2={py(W)} {...line} />
      <line x1={px(L - DOUBLES_LONG_FROM_BASE)} y1={py(0)} x2={px(L - DOUBLES_LONG_FROM_BASE)} y2={py(W)} {...line} />
      {/* centre lines, short service line to baseline on each side */}
      <line x1={px(0)} y1={py(HALF_W)} x2={px(NET - SHORT_SERVICE)} y2={py(HALF_W)} {...line} />
      <line x1={px(NET + SHORT_SERVICE)} y1={py(HALF_W)} x2={px(L)} y2={py(HALF_W)} {...line} />
      {/* net */}
      <line x1={px(NET)} y1={py(-0.25)} x2={px(NET)} y2={py(W + 0.25)} stroke={BOARD.net} strokeWidth={SIZES.netW} />
    </g>
  );
}

/** "Axelsen" over the left half, "Opponent" over the right. */
export function HalfLabels({ me }: { me: string }) {
  const y = py(0) - 22;
  return (
    <g aria-hidden="true" fill={BOARD.text} style={{ fontSize: `calc(var(--court-font-scale, 1) * ${SIZES.font}px)`, fontFamily: FONT, fontWeight: 600 }}>
      <text x={px(NET / 2)} y={y} textAnchor="middle">
        {me}
      </text>
      <text x={px(NET + NET / 2)} y={y} textAnchor="middle">
        Opponent
      </text>
    </g>
  );
}

/** A rounded label on the board: dark pill with light text, or gold with dark text. */
export function Pill({
  x,
  y,
  text,
  gold = false,
  anchor = "middle",
  size = SIZES.fontSmall,
}: {
  x: number; // units
  y: number; // units, vertical centre
  text: string;
  gold?: boolean;
  anchor?: "start" | "middle" | "end";
  size?: number;
}) {
  const w = text.length * size * 0.58 + size * 0.9;
  const h = size * 1.5;
  const left = anchor === "middle" ? x - w / 2 : anchor === "start" ? x : x - w;
  return (
    <g aria-hidden="true" style={SCALE_WITH_CONTAINER}>
      <rect x={left} y={y - h / 2} width={w} height={h} rx={h / 2} fill={gold ? BOARD.gold : BOARD.pill} />
      <text
        x={left + w / 2}
        y={y + size * 0.36}
        textAnchor="middle"
        fill={gold ? BOARD.goldInk : BOARD.me}
        style={{ fontSize: `${size}px`, fontFamily: FONT, fontWeight: 600 }}
      >
        {text}
      </text>
    </g>
  );
}

/** A small arrowhead marker in one colour. */
export function ArrowMarkers({ id }: { id: string }) {
  const head = (name: string, fill: string) => (
    <marker key={name} id={`${id}-${name}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="12" markerHeight="12" markerUnits="userSpaceOnUse" orient="auto-start-reverse">
      <path d="M 0 1 L 10 5 L 0 9 z" fill={fill} />
    </marker>
  );
  return (
    <defs>
      {head("me", BOARD.me)}
      {head("opp", BOARD.opp)}
      {head("gold", BOARD.gold)}
    </defs>
  );
}

/** The panel every court sits in: rounded dark board, the SVG, and a one-line legend. The
 *  board scales to its container and never grows past about 340 px tall. */
export function Board({
  title,
  uid,
  legend,
  children,
  className = "",
  onMouseLeave,
}: {
  title: string;
  uid: string;
  legend: ReactNode;
  children: ReactNode;
  className?: string;
  onMouseLeave?: () => void;
}) {
  return (
    <figure className={`court-wrap mx-auto w-full max-w-[680px] ${className}`}>
      <div className="overflow-hidden rounded-[10px]" style={{ background: BOARD.bg }}>
        <svg viewBox={VIEW_BOX} role="img" aria-labelledby={`${uid}-t`} className="block h-auto w-full select-none" onMouseLeave={onMouseLeave}>
          <title id={`${uid}-t`}>{title}</title>
          {children}
        </svg>
        <figcaption className="truncate px-3 pb-2 text-xs" style={{ color: BOARD.text }} title={typeof legend === "string" ? legend : undefined}>
          {legend}
        </figcaption>
      </div>
    </figure>
  );
}
