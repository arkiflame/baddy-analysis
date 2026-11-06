/* Court geometry shared by the court components (D30).

   Full-court frame, in metres: x across the court (0..6.10, viewer's left to right), y along
   it (0..13.40), net at 6.70. The player's own half is the BOTTOM half (y > 6.70), the
   opponent's the top half. This is the frame the example-rally strokes are exported in.

   Half-court ("receiver") frame, as the zone tables use it: x = metres from the centre line
   toward the player's own right, y = metres from the net into the player's half. `toFull`
   converts it. On the opponent's half the opponent faces the viewer, so their right is the
   viewer's left; a right-handed opponent's forehand side is therefore drawn on the LEFT. */

export const W = 6.1;
export const L = 13.4;
export const NET = 6.7;
export const SINGLES_HALF = 2.59;
export const HALF_W = 3.05;
export const SHORT_SERVICE = 1.98;
export const DOUBLES_LONG_FROM_BASE = 0.76;

export const S = 100; // px per metre
export const MARGIN = 0.5; // metres of surface drawn outside the lines
const LABEL_ROOM = 44; // px above and below for side labels

export type Half = "player" | "opponent";
export type View = "full" | "player" | "opponent";

export interface Band {
  name: string;
  lo: number;
  hi: number;
}

export interface ZoneRect {
  zone: string;
  x: number; // full-court metres, left edge
  y: number; // top edge
  w: number;
  h: number;
}

export const px = (X: number) => (X + MARGIN) * S;
export const py = (Y: number) => (Y + MARGIN) * S;

export const VIEW_W = (W + 2 * MARGIN) * S;

/** viewBox string and its numbers for a full court or one half. */
export function viewBox(view: View): { vb: string; x0: number; y0: number; w: number; h: number } {
  const x0 = 0;
  const w = VIEW_W;
  if (view === "full") {
    const y0 = -LABEL_ROOM;
    const h = (L + 2 * MARGIN) * S + 2 * LABEL_ROOM;
    return { vb: `${x0} ${y0} ${w} ${h}`, x0, y0, w, h };
  }
  if (view === "player") {
    const y0 = py(NET) - 70;
    const h = py(L) + LABEL_ROOM + 10 - y0;
    return { vb: `${x0} ${y0} ${w} ${h}`, x0, y0, w, h };
  }
  const y0 = -LABEL_ROOM;
  const h = py(NET) + 70 - y0;
  return { vb: `${x0} ${y0} ${w} ${h}`, x0, y0, w, h };
}

/** Half-court frame -> full-court frame. */
export function toFull(x: number, y: number, half: Half): { X: number; Y: number } {
  return half === "player" ? { X: HALF_W + x, Y: NET + y } : { X: HALF_W - x, Y: NET - y };
}

/** Is the forehand side on the viewer's right for this half? */
export function forehandOnViewerRight(half: Half, fhOnRight: boolean): boolean {
  return half === "player" ? fhOnRight : false;
}

/** The six coach zones (front/mid/rear x forehand/backhand) as full-court rectangles. */
export function zoneRects(bands: Band[], half: Half, fhOnRight: boolean): ZoneRect[] {
  const fhRight = forehandOnViewerRight(half, fhOnRight);
  const out: ZoneRect[] = [];
  for (const b of bands) {
    const lo = b.lo;
    const hi = Math.min(b.hi, NET);
    for (const side of ["fh", "bh"] as const) {
      const right = side === "fh" ? fhRight : !fhRight;
      const x = right ? HALF_W : HALF_W - SINGLES_HALF;
      const y = half === "player" ? NET + lo : NET - hi;
      out.push({ zone: `${b.name}_${side}`, x, y, w: SINGLES_HALF, h: hi - lo });
    }
  }
  return out;
}

/** Centre of a zone in full-court metres; "body" and unknown zones -> the half's centre. */
export function zoneCentre(
  zone: string | null,
  bands: Band[],
  half: Half,
  fhOnRight: boolean,
): { X: number; Y: number } {
  const r = zone ? zoneRects(bands, half, fhOnRight).find((z) => z.zone === zone) : undefined;
  if (r) return { X: r.x + r.w / 2, Y: r.y + r.h / 2 };
  return { X: HALF_W, Y: half === "player" ? NET + NET / 2 : NET / 2 };
}

/** The whole singles half as a rectangle. */
export function halfRect(half: Half): ZoneRect {
  return {
    zone: "any",
    x: HALF_W - SINGLES_HALF,
    y: half === "player" ? NET : 0,
    w: 2 * SINGLES_HALF,
    h: NET,
  };
}

const line = { stroke: "var(--court-white)", strokeWidth: 4, fill: "none" } as const;

/** A real court: surface, doubles and singles lines, service lines, centre lines, net. */
export function CourtLines({ view }: { view: View }) {
  const v = viewBox(view);
  return (
    <g aria-hidden="true">
      <rect x={v.x0} y={v.y0} width={v.w} height={v.h} fill="var(--court-green-out)" />
      <rect x={px(0)} y={py(0)} width={W * S} height={L * S} fill="var(--court-green)" />
      {/* outer (doubles) lines */}
      <rect x={px(0)} y={py(0)} width={W * S} height={L * S} {...line} />
      {/* singles sidelines */}
      <line x1={px(HALF_W - SINGLES_HALF)} y1={py(0)} x2={px(HALF_W - SINGLES_HALF)} y2={py(L)} {...line} />
      <line x1={px(HALF_W + SINGLES_HALF)} y1={py(0)} x2={px(HALF_W + SINGLES_HALF)} y2={py(L)} {...line} />
      {/* short service lines */}
      <line x1={px(0)} y1={py(NET - SHORT_SERVICE)} x2={px(W)} y2={py(NET - SHORT_SERVICE)} {...line} />
      <line x1={px(0)} y1={py(NET + SHORT_SERVICE)} x2={px(W)} y2={py(NET + SHORT_SERVICE)} {...line} />
      {/* doubles long service lines */}
      <line x1={px(0)} y1={py(DOUBLES_LONG_FROM_BASE)} x2={px(W)} y2={py(DOUBLES_LONG_FROM_BASE)} {...line} />
      <line x1={px(0)} y1={py(L - DOUBLES_LONG_FROM_BASE)} x2={px(W)} y2={py(L - DOUBLES_LONG_FROM_BASE)} {...line} />
      {/* centre lines, short service line to baseline on each side */}
      <line x1={px(HALF_W)} y1={py(0)} x2={px(HALF_W)} y2={py(NET - SHORT_SERVICE)} {...line} />
      <line x1={px(HALF_W)} y1={py(NET + SHORT_SERVICE)} x2={px(HALF_W)} y2={py(L)} {...line} />
      {/* net */}
      <line x1={px(-0.3)} y1={py(NET)} x2={px(W + 0.3)} y2={py(NET)} stroke="var(--net)" strokeWidth={10} />
      <text x={px(W + 0.3)} y={py(NET) - 10} textAnchor="end" style={{ fontSize: "calc(var(--court-font-scale, 1) * 16px)" }} fill="var(--court-white)">
        net
      </text>
    </g>
  );
}

/** Side labels above (opponent's half) or below (player's half) the court. */
/** "Axelsen's forehand side" -> "forehand" for narrow courts; the half caption says whose. */
const shortSide = (s: string) => (s.includes("forehand") ? "forehand" : s.includes("backhand") ? "backhand" : s);

export function SideLabels({ half, left, right }: { half: Half; left: string; right: string }) {
  const y = half === "player" ? py(L) + 34 : py(0) - 16;
  return (
    <g aria-hidden="true" style={{ fontSize: "calc(var(--court-font-scale, 1) * 18px)" }} fill="var(--court-white)">
      <text className="court-long" x={px(HALF_W - SINGLES_HALF / 2)} y={y} textAnchor="middle">
        {left}
      </text>
      <text className="court-long" x={px(HALF_W + SINGLES_HALF / 2)} y={y} textAnchor="middle">
        {right}
      </text>
      <text className="court-short" x={px(HALF_W - SINGLES_HALF / 2)} y={y} textAnchor="middle">
        {shortSide(left)}
      </text>
      <text className="court-short" x={px(HALF_W + SINGLES_HALF / 2)} y={y} textAnchor="middle">
        {shortSide(right)}
      </text>
    </g>
  );
}

/** Side labels for one half from the player's racket hand. */
export function sideLabelsFor(half: Half, me: string, fhOnRight: boolean): { left: string; right: string } {
  if (half === "opponent") return { left: "opponent's forehand side", right: "opponent's backhand side" };
  return fhOnRight
    ? { left: `${me}'s backhand side`, right: `${me}'s forehand side` }
    : { left: `${me}'s forehand side`, right: `${me}'s backhand side` };
}

/** Arrowhead markers for rally and habit arrows. */
export function ArrowMarkers({ id }: { id: string }) {
  const head = (name: string, fill: string) => (
    <marker
      key={name}
      id={`${id}-${name}`}
      viewBox="0 0 10 10"
      refX="8"
      refY="5"
      markerWidth="18"
      markerHeight="18"
      markerUnits="userSpaceOnUse"
      orient="auto-start-reverse"
    >
      <path d="M 0 0 L 10 5 L 0 10 z" fill={fill} stroke="var(--stroke-outline)" strokeWidth="1" />
    </marker>
  );
  return (
    <defs>
      {head("me", "var(--stroke-me)")}
      {head("opp", "var(--stroke-opp)")}
      {head("habit", "var(--stroke-opp)")}
    </defs>
  );
}
