# web: the scouting site

Statically exported Next.js app (App Router, TypeScript, Tailwind) that renders the reports in
`public/data/` (written by `../scripts/export_web.py`). The site computes nothing; see the
repository README for the deploy steps.

```
npm install
npm run dev      # http://localhost:3000
npm run build    # static site in out/
npm run lint
```

Layout: `src/app` (pages: `/`, `/players/[slug]/`, `/methods/`), `src/components` (PlayerView,
InsightCard, WatchIt, HowToRead, Tables, ThemeToggle, PlayerSearch, Badge, ShowNumbers with the
`Reveal` disclosure, and `court/` for the SVG courts: ZoneCourt, RallyCourt, HabitArrows,
HeroCourt, HeatCourt), `src/lib` (types mirroring the JSON, build-time readers, number and
plain-language formatting).

Plain language (D30): the main text of every page is written for a reader with no statistics.
The exact figures sit inside `Reveal` disclosures, which carry a `data-technical` attribute;
`uv run python scripts/jargon_check.py` (after `npm run build`) parses `out/` and lists any
banned term that is still in the main text. Footage is embedded from youtube-nocookie.com only
after the reader presses "Watch it"; nothing loads from YouTube before that.
