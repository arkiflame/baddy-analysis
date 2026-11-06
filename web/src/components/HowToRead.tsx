/** The box at the top of every player page: how to read the cards, in six lines (D30). */
export function HowToRead({
  me,
  within,
  pressureFrom,
}: {
  me: string;
  within: number;
  pressureFrom: number;
}) {
  const twoShots = within === 2 ? "two shots" : `${within} shots`;
  return (
    <details className="rounded border border-line bg-surface p-4" open>
      <summary className="cursor-pointer text-lg font-semibold">How to read this page</summary>
      <ul className="mt-2 max-w-[70ch] list-disc space-y-1 pl-5 text-ink-2">
        <li>
          Each card starts with what to do, in bold. Under it, one sentence says how often the
          situation costs {me} the point, and how often it costs most pros.
        </li>
        <li>
          &ldquo;Loses the point quickly&rdquo; means {me} lost the point within the next {twoShots}.
        </li>
        <li>&ldquo;Most pros&rdquo; means every other player in the data, in the same situation.</li>
        <li>
          A yellow line under a card means the evidence is thin. We show the card anyway and say so.
        </li>
        <li>
          &ldquo;Watch it&rdquo; plays a real rally that shows the pattern. &ldquo;Show the
          numbers&rdquo; opens the exact figures.
        </li>
        <li>
          &ldquo;Late in a game&rdquo; means either player has {pressureFrom} points or more.
          &ldquo;Deciding game&rdquo; means the third game.
        </li>
      </ul>
    </details>
  );
}
