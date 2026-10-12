import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { getMistakes, getProgress } from "@/lib/data";
import type { Mistake } from "@/lib/types";

export const metadata: Metadata = { title: "Progress" };

const SKILL_LABEL: Record<string, string> = {
  grammar: "Grammar",
  vocab: "Vocabulary",
  reading: "Reading",
  listening: "Listening",
  writing: "Writing",
  speaking: "Speaking",
};

export default function ProgressPage() {
  return (
    <>
      <h1 className="font-display text-4xl text-ink">Your progress</h1>
      <p className="mt-2 text-muted">
        Mastery grows as you answer correctly and dips when you slip. Weakest skills come first.
      </p>
      <Suspense fallback={<div className="mt-10 h-64 animate-pulse rounded-2xl bg-line/50" />}>
        <ProgressContent />
      </Suspense>
    </>
  );
}

async function ProgressContent() {
  const [{ lessons, objectives }, mistakes] = await Promise.all([getProgress(), getMistakes(8)]);
  const completed = lessons.filter((l) => l.status === "completed");

  if (objectives.length === 0) {
    return (
      <div className="card mt-10 px-6 py-10 text-center">
        <p className="font-display text-xl text-ink">Nothing here yet</p>
        <p className="mt-2 text-muted">Do your first lesson and your progress will show up here.</p>
        <Link href="/learn" className="btn-primary mt-6">
          Go to lessons
        </Link>
      </div>
    );
  }

  return (
    <div className="mt-10 grid gap-8 lg:grid-cols-[2fr_1fr]">
      <section className="card p-6">
        <h2 className="font-display text-xl text-ink">Skills</h2>
        <ul className="mt-5 space-y-5">
          {objectives.map((o) => {
            const percent = Math.round(o.mastery * 100);
            return (
              <li key={o.slug}>
                <div className="flex items-baseline justify-between gap-4">
                  <p className="text-ink">{o.can_do}</p>
                  <span className="shrink-0 text-sm font-semibold text-ink tabular-nums">
                    {percent}%
                  </span>
                </div>
                <div
                  className="mt-2 h-2.5 overflow-hidden rounded-full bg-paper"
                  role="progressbar"
                  aria-valuenow={percent}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={o.can_do}
                >
                  <div
                    className={`h-full rounded-full ${percent >= 70 ? "bg-success" : percent >= 40 ? "bg-accent" : "bg-danger/70"}`}
                    style={{ width: `${Math.max(percent, 3)}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-muted">
                  {SKILL_LABEL[o.skill] ?? o.skill} · {o.evidence_count} answer
                  {o.evidence_count === 1 ? "" : "s"}
                </p>
              </li>
            );
          })}
        </ul>
      </section>

      <div className="space-y-8">
        <section className="card h-fit p-6">
          <h2 className="font-display text-xl text-ink">Lessons</h2>
          <p className="mt-1 text-sm text-muted">
            {completed.length} completed · {lessons.length - completed.length} in progress
          </p>
          <ul className="mt-4 space-y-3">
            {lessons.map((l) => (
              <li key={l.lesson_slug}>
                <Link
                  href={`/lessons/${l.lesson_slug}`}
                  className="flex justify-between gap-3 hover:text-accent"
                >
                  <span className="text-ink">{l.title}</span>
                  <span className="shrink-0 text-sm text-muted tabular-nums">
                    {l.status === "completed" && l.score !== null
                      ? `${Math.round(l.score * 100)}%`
                      : "in progress"}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
        <Mistakes mistakes={mistakes} />
      </div>
    </div>
  );
}

function Mistakes({ mistakes }: { mistakes: Mistake[] }) {
  if (mistakes.length === 0) return null;
  return (
    <section className="card h-fit p-6">
      <h2 className="font-display text-xl text-ink">Mistakes you make most</h2>
      <p className="mt-1 text-sm text-muted">
        From your writing. Your tutor will help you practise these.
      </p>
      <ul className="mt-4 space-y-3">
        {mistakes.map((m) => (
          <li key={`${m.original}-${m.correction}`} className="text-sm">
            <p className="flex flex-wrap items-baseline gap-x-2">
              <span className="text-danger line-through">{m.original}</span>
              <span aria-hidden="true" className="text-muted">
                →
              </span>
              <span className="font-medium text-success">{m.correction}</span>
              {m.count > 1 ? (
                <span className="ml-auto rounded-full bg-danger-soft px-2 py-0.5 text-xs font-medium text-danger">
                  ×{m.count}
                </span>
              ) : null}
            </p>
            <p className="mt-0.5 text-muted">{m.explanation}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
