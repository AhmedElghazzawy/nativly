# Curriculum content

Courses are authored here as YAML and imported into the database by slug
([ADR 0006](../docs/decisions/0006-curriculum-as-yaml-content.md)). Deploys import automatically;
locally run:

```bash
cd api && uv run python -m app.learning.importer ../content
```

The import validates everything first and writes nothing if any file is invalid. CI also
checks that this folder always imports (`test_repository_content_is_valid`).

## Layout

```
content/<language>/<level>/course.yaml        course + its learning objectives
content/<language>/<level>/units/NN-name.yaml one unit, with its lessons and steps
```

## Rules

- **Slugs are permanent IDs.** Lowercase words joined by `-`, unique across all content.
  Renaming a slug creates a new item; learner progress stays on the old one. Convention:
  `en-a2-u01-l02-ex03` (language, level, unit, lesson, exercise).
- **Never delete an exercise or objective** that has shipped: learner history points at it.
  Removing it from a lesson's steps is fine.
- Every lesson lists the objectives it teaches; every exercise names the one it practises.
- Step bodies are Markdown. Explanations say *why*, with a short example.
- **Quote YAML traps:** `on`, `off`, `yes`, `no`, `true`, `false`, `null`, `?` and strings
  starting with `:` or `-` must be in quotes, or YAML turns them into booleans/null/syntax.

## Exercise types

```yaml
- kind: exercise
  exercise:
    slug: en-a2-u01-l01-ex01
    objective: en-a2-past-simple-regular
    type: mcq                 # one correct option
    difficulty: 1             # 1 (easy) to 5
    prompt: "Yesterday I ___ my grandmother."
    options: [visit, visited, visitted]
    answer: 1                 # index into options
    explanation: Shown after the learner answers.

    # type: cloze             # fill the blanks, one ___ per blank
    # text: "We ___ in Izmir."
    # answers: [[lived]]      # accepted answers per blank

    # type: reorder           # tokens are shuffled automatically on import
    # answer: [She, played, tennis, last, weekend]
```
