import type {
  MeanRow,
  PredictabilityRow,
  RateRow,
  SetPlayRow,
  TendencyRow,
  XpRow,
} from "@/lib/types";
import { int, num, numCi, pct, pctCi, pts, ptsCi, sequenceWords, shotWords, zoneWords } from "@/lib/format";

function Flag({ row }: { row: { reliable: boolean; ref_reliable?: boolean; signal?: boolean } }) {
  if (!row.reliable) return <span className="text-ink-2">too few</span>;
  if (row.ref_reliable === false) return <span className="text-ink-2">ref too few</span>;
  if (row.signal) return <span className="font-medium">● signal</span>;
  return null;
}

function Wrap({ caption, children }: { caption: string; children: React.ReactNode }) {
  return (
    <div className="overflow-x-auto rounded border border-line bg-surface">
      <table className="tbl">
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}

export function rowLabel(r: RateRow): string {
  if (r.shot && r.zone) return `${shotWords(r.shot)} → ${zoneWords(r.zone)}`;
  if (r.zone) return zoneWords(r.zone);
  if (r.shot) return shotWords(r.shot);
  return r.label ?? "";
}

/** Danger-table rows: P(point lost within k shots | condition), player vs typical pros. */
export function RateTable({
  rows,
  caption,
  first,
  outcome,
  limit,
}: {
  rows: RateRow[];
  caption: string;
  first: string;
  outcome: string;
  limit?: number;
}) {
  const shown = limit ? rows.slice(0, limit) : rows;
  if (!shown.length) return <p className="text-sm text-ink-2">No rows reach the minimum n.</p>;
  return (
    <Wrap caption={caption}>
      <thead>
        <tr>
          <th scope="col">{first}</th>
          <th scope="col" className="num">n</th>
          <th scope="col" className="num">{outcome}</th>
          <th scope="col" className="num">95% CI</th>
          <th scope="col" className="num">typical pros</th>
          <th scope="col" className="num">difference (95% CI)</th>
          <th scope="col">flag</th>
        </tr>
      </thead>
      <tbody>
        {shown.map((r, i) => (
          <tr key={`${r.label ?? ""}-${i}`}>
            <th scope="row" className="font-normal">{rowLabel(r)}</th>
            <td className="num">{int(r.n)}</td>
            <td className="num">{pct(r.rate)}</td>
            <td className="num">{pctCi(r.ci_lo, r.ci_hi)}</td>
            <td className="num">
              {pct(r.ref_rate)} {r.ref_n !== null && <span className="text-ink-2">(n={int(r.ref_n)})</span>}
            </td>
            <td className="num">
              {pts(r.delta)} <span className="text-ink-2">({ptsCi(r.delta_lo, r.delta_hi)})</span>
            </td>
            <td><Flag row={r} /></td>
          </tr>
        ))}
      </tbody>
    </Wrap>
  );
}

export function MeanTable({
  rows,
  caption,
  first,
  unit,
  digits = 2,
}: {
  rows: MeanRow[];
  caption: string;
  first: string;
  unit: string;
  digits?: number;
}) {
  if (!rows.length) return <p className="text-sm text-ink-2">No data.</p>;
  return (
    <Wrap caption={caption}>
      <thead>
        <tr>
          <th scope="col">{first}</th>
          <th scope="col" className="num">n</th>
          <th scope="col" className="num">mean {unit}</th>
          <th scope="col" className="num">95% CI</th>
          <th scope="col" className="num">typical pros</th>
          <th scope="col" className="num">difference (95% CI)</th>
          <th scope="col">flag</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.label}>
            <th scope="row" className="font-normal">{r.label}</th>
            <td className="num">{int(r.n)}</td>
            <td className="num">{num(r.mean, digits)}</td>
            <td className="num">{numCi(r.lo, r.hi, digits)}</td>
            <td className="num">
              {num(r.ref_mean, digits)} <span className="text-ink-2">(n={int(r.ref_n)})</span>
            </td>
            <td className="num">
              {num(r.delta, digits, true)}{" "}
              <span className="text-ink-2">({numCi(r.delta_lo, r.delta_hi, digits, true)})</span>
            </td>
            <td><Flag row={r} /></td>
          </tr>
        ))}
      </tbody>
    </Wrap>
  );
}

export function XpTable({
  rows,
  caption,
  first,
  value,
  unit,
  withOwn = false,
  limit,
}: {
  rows: XpRow[];
  caption: string;
  first: string;
  value: string;
  unit: string;
  withOwn?: boolean;
  limit?: number;
}) {
  const shown = limit ? rows.slice(0, limit) : rows;
  if (!shown.length) return <p className="text-sm text-ink-2">No data.</p>;
  return (
    <Wrap caption={caption}>
      <thead>
        <tr>
          <th scope="col">{first}</th>
          <th scope="col" className="num">{unit}</th>
          <th scope="col" className="num">xP</th>
          <th scope="col" className="num">{value} (95% CI)</th>
          <th scope="col" className="num">typical pros</th>
          <th scope="col" className="num">difference (95% CI)</th>
          {withOwn && <th scope="col" className="num">vs own overall (95% CI)</th>}
          <th scope="col">flag</th>
        </tr>
      </thead>
      <tbody>
        {shown.map((r) => (
          <tr key={r.label}>
            <th scope="row" className="font-normal">{r.label}</th>
            <td className="num">{int(r.n)}</td>
            <td className="num">{num(r.xp, 3)}</td>
            <td className="num">
              {num(r.mean, 3, true)} <span className="text-ink-2">({numCi(r.lo, r.hi, 3, true)})</span>
            </td>
            <td className="num">
              {num(r.ref_mean, 3, true)} <span className="text-ink-2">(n={int(r.ref_n)})</span>
            </td>
            <td className="num">
              {num(r.delta, 3, true)}{" "}
              <span className="text-ink-2">({numCi(r.delta_lo, r.delta_hi, 3, true)})</span>
            </td>
            {withOwn && (
              <td className="num">
                {num(r.own_delta, 3, true)}{" "}
                <span className="text-ink-2">({numCi(r.own_lo, r.own_hi, 3, true)})</span>
              </td>
            )}
            <td>
              <Flag row={r} />
              {withOwn && r.own_signal && r.reliable ? " / shot-specific" : ""}
            </td>
          </tr>
        ))}
      </tbody>
    </Wrap>
  );
}

export function TendencyTable({ rows, caption, limit }: { rows: TendencyRow[]; caption: string; limit?: number }) {
  const shown = (limit ? rows.slice(0, limit) : rows);
  if (!shown.length) {
    return (
      <p className="text-sm text-ink-2">
        No reply is chosen significantly more often than typical pros (situation n ≥ 30 on both sides).
      </p>
    );
  }
  return (
    <Wrap caption={caption}>
      <thead>
        <tr>
          <th scope="col">situation (incoming shot → zone)</th>
          <th scope="col">reply</th>
          <th scope="col" className="num">n (situations)</th>
          <th scope="col" className="num">share (95% CI)</th>
          <th scope="col" className="num">typical pros</th>
          <th scope="col" className="num">difference (95% CI)</th>
        </tr>
      </thead>
      <tbody>
        {shown.map((r) => (
          <tr key={`${r.situation}|${r.reply}`}>
            <th scope="row" className="font-normal">{r.situation}</th>
            <td>{r.reply}</td>
            <td className="num">{int(r.n)}</td>
            <td className="num">
              {pct(r.rate)} <span className="text-ink-2">({pctCi(r.ci_lo, r.ci_hi)})</span>
            </td>
            <td className="num">
              {pct(r.ref_rate)} <span className="text-ink-2">(n={int(r.ref_n)})</span>
            </td>
            <td className="num">
              {pts(r.delta)} <span className="text-ink-2">({ptsCi(r.delta_lo, r.delta_hi)})</span>
            </td>
          </tr>
        ))}
      </tbody>
    </Wrap>
  );
}

export function PredictabilityTable({ rows, caption }: { rows: PredictabilityRow[]; caption: string }) {
  if (!rows.length) return <p className="text-sm text-ink-2">No situation reaches n ≥ 30 on both sides.</p>;
  return (
    <Wrap caption={caption}>
      <thead>
        <tr>
          <th scope="col">situation</th>
          <th scope="col" className="num">n</th>
          <th scope="col" className="num">entropy, bits (95% CI)</th>
          <th scope="col" className="num">typical pros at same n</th>
          <th scope="col" className="num">effective replies</th>
          <th scope="col">most common reply</th>
          <th scope="col">flag</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.situation}>
            <th scope="row" className="font-normal">{r.situation}</th>
            <td className="num">{int(r.n)}</td>
            <td className="num">
              {num(r.entropy_bits)} <span className="text-ink-2">({numCi(r.lo, r.hi)})</span>
            </td>
            <td className="num">
              {num(r.ref_entropy_bits)}{" "}
              <span className="text-ink-2">({numCi(r.ref_lo, r.ref_hi)})</span>
            </td>
            <td className="num">{num(r.effective_replies, 1)}</td>
            <td>
              {r.top_reply} <span className="text-ink-2">({pct(r.top_share)})</span>
            </td>
            <td>
              {r.more_predictable ? "● more predictable" : r.less_predictable ? "○ less predictable" : ""}
            </td>
          </tr>
        ))}
      </tbody>
    </Wrap>
  );
}

export function SetPlayTable({ rows, caption, me, limit = 8 }: { rows: SetPlayRow[]; caption: string; me: string; limit?: number }) {
  const shown = rows.slice(0, limit);
  if (!shown.length) return <p className="text-sm text-ink-2">No opening sequence occurs 30 times or more.</p>;
  return (
    <Wrap caption={caption}>
      <thead>
        <tr>
          <th scope="col">opening</th>
          <th scope="col" className="num">rallies</th>
          <th scope="col" className="num">share (95% CI)</th>
          <th scope="col" className="num">typical pros</th>
          <th scope="col" className="num">difference (95% CI)</th>
          <th scope="col" className="num">{me} wins (95% CI)</th>
          <th scope="col" className="num">typical pros win</th>
          <th scope="col">flag</th>
        </tr>
      </thead>
      <tbody>
        {shown.map((r) => (
          <tr key={r.sequence}>
            <th scope="row" className="font-normal">{sequenceWords(r.sequence, me)}</th>
            <td className="num">{int(r.wins)}</td>
            <td className="num">
              {pct(r.rate)} <span className="text-ink-2">({pctCi(r.ci_lo, r.ci_hi)})</span>
            </td>
            <td className="num">
              {pct(r.ref_rate)} <span className="text-ink-2">(n={int(r.ref_n)})</span>
            </td>
            <td className="num">
              {r.ref_n ? (
                <>
                  {pts(r.delta)} <span className="text-ink-2">({ptsCi(r.delta_lo, r.delta_hi)})</span>
                </>
              ) : (
                "–"
              )}
            </td>
            <td className="num">
              {pct(r.win_rate)} <span className="text-ink-2">({pctCi(r.win_lo, r.win_hi)})</span>
            </td>
            <td className="num">{pct(r.ref_win_rate)}</td>
            <td>{r.candidate ? "● distinctive" : ""}</td>
          </tr>
        ))}
      </tbody>
    </Wrap>
  );
}
