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

Layout: `src/app` (pages: `/`, `/players/[slug]/`, `/methods/`), `src/components` (Court, PlayerView,
Tables, Tabs, ThemeToggle, PlayerSearch, Badge), `src/lib` (types mirroring the JSON, build-time
readers, number formatting).
