# 0006. Curriculum as YAML content, imported by slug

- **Date:** 2026-10-11
- **Status:** accepted

## Context
The curriculum (courses, units, lessons, objectives, exercises) is hand-written and reviewed;
quality is the product's moat. More languages must be addable "as content rather than code".
Phase 1 needs a seed/import path; there are no content editors yet.

## Options
1. **Admin UI writing straight to the database**: friendly for non-developers later, but a lot
   of UI now, and content has no history or review.
2. **SQL/Python seed scripts**: simple, but content mixed with code and hard to review.
3. **YAML files in the repo, validated and imported by slug**: content is versioned, reviewed in
   PRs and checked in CI; an admin UI can be added later on top of the same importer.

## Decision
Option 3.
- `content/<lang>/<level>/course.yaml` + `units/*.yaml`, validated by strict Pydantic models
  (unknown keys rejected, cross-references checked) before any write.
- Import is an idempotent upsert keyed by slug in one transaction. Lesson steps and
  lesson↔objective links are replaced per lesson; exercises and objectives are only updated,
  never deleted, so attempts and mastery always reference something that exists.
- Exercises store a public `payload` and a private `answer` (key + explanation) in separate
  JSONB columns; API schemas are built from `payload` only, so answers can't leak by accident.
- Enums are VARCHAR + named CHECK constraints rather than native Postgres enums, so adding a
  step kind or exercise type is a simple migration.
- The content is baked into the image and imported on every start (Render free plan has no
  release step); imports of unchanged content write nothing.

## Consequences
- Content changes go through PRs and CI, like code.
- Deleting content requires an explicit migration or a future archive flag.
- Non-developer authoring will need tooling (an admin UI or a CMS export) later.
