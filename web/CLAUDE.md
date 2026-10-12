# web/ conventions (Next.js app)

Loaded when working inside web/. Root CLAUDE.md rules apply. Next.js 16 differs from older
versions: read `node_modules/next/dist/docs/` before using an unfamiliar API (see AGENTS.md).

- Server-first: pages are Server Components; `"use client"` only for interactivity.
- Cache Components is on: anything reading cookies/params/searchParams sits inside `<Suspense>`.
- All API calls go through `src/lib/api.ts` (`apiFetch` for the learner, `publicFetch` for
  auth). Reads live in `src/lib/data.ts`; writes are Server Actions that re-check auth.
- Never expose tokens to the browser; never add `NEXT_PUBLIC_` secrets.
- API types come from `npm run gen:api`; CI fails if they drift from the API.
- Tailwind theme tokens live in `src/app/globals.css` (`@theme`). Don't name a color after a
  Tailwind utility (e.g. `right`, `center`): `text-right` would collide with text-align.
- Every user-facing flow gets a Playwright test in `e2e/`.
- Formatting is Prettier (+ Tailwind class sorting): run `npm run format`; CI checks it.
