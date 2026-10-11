# Nativly web

Next.js 16 (App Router, Cache Components) + TypeScript + Tailwind 4. The learner-facing app:
sign-up, course outline, lesson player and progress.

```bash
npm ci
API_URL=http://localhost:8000 npm run dev      # API must be running (see ../README.md)
npm run lint && npm run typecheck && npm test  # checks
npm run e2e                                    # Playwright, against a running stack
npm run gen:api                                # regenerate API types after API changes
```

- **Auth:** the Next.js server is the only API client. Tokens live in httpOnly cookies;
  `src/proxy.ts` refreshes them before pages render. See `docs/decisions/0007`.
- **Data:** `src/lib/data.ts` (reads) and server actions (writes) go through `src/lib/api.ts`.
- **Types:** `src/lib/api-schema.d.ts` is generated from the API's OpenAPI schema; never edit it.
