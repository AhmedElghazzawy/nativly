import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { RememberCourse } from "@/components/remember-course";
import { ApiError } from "@/lib/api";
import { getCourse, getCourses, getProgress, getReviewSummary } from "@/lib/data";
import type { LessonProgress, ReviewSummary } from "@/lib/types";

export const metadata: Metadata = { title: "Learn" };

export default function LearnPage({ params }: PageProps<"/learn/[course]">) {
  return (
    <>
      <h1 className="font-display text-4xl text-ink">Your course</h1>
      <p className="mt-2 text-muted">One short lesson at a time. Explanations first, then practice.</p>
      <Suspense fallback={<OutlineSkeleton />}>
        <Courses params={params} />
      </Suspense>
    </>
  );
}

async function Courses({ params }: Pick<PageProps<"/learn/[course]">, "params">) {
  const { course: slug } = await params;
  const [courses, progress, review, course] = await Promise.all([
    getCourses(),
    getProgress(),
    getReviewSummary(),
    getCourse(slug).catch((error: unknown) => {
      if (error instanceof ApiError && error.status === 404) notFound();
      throw error;
    }),
  ]);
  const byLesson = new Map(progress.lessons.map((p) => [p.lesson_slug, p]));

  return (
    <div className="mt-8 space-y-10">
      <RememberCourse slug={course.slug} />
      <nav aria-label="Level" className="flex gap-2">
        {courses.map((c) => (
          <Link
            key={c.slug}
            href={`/learn/${c.slug}`}
            aria-current={c.slug === course.slug ? "page" : undefined}
            className={`rounded-lg border px-3.5 py-1.5 text-sm font-semibold transition ${
              c.slug === course.slug
                ? "border-ink bg-ink text-white"
                : "border-line bg-card text-muted hover:border-accent hover:text-accent"
            }`}
          >
            {c.cefr_level}
          </Link>
        ))}
      </nav>
      <TodayBanner review={review} />
      <section>
        <div className="flex items-baseline gap-3">
          <span className="rounded-md bg-ink px-2 py-0.5 text-sm font-semibold text-white">
            {course.cefr_level}
          </span>
          <h2 className="font-display text-2xl text-ink">{course.title}</h2>
        </div>
        <p className="mt-1 text-muted">{course.description}</p>

        {course.units.map((unit) => (
          <div key={unit.slug} className="card mt-6 overflow-hidden">
            <div className="border-b border-line px-5 py-4">
              <p className="text-xs font-semibold tracking-wide text-accent uppercase">
                Unit {unit.position}
              </p>
              <h3 className="font-display text-xl text-ink">{unit.title}</h3>
              <p className="text-sm text-muted">{unit.description}</p>
            </div>
            <ol>
              {unit.lessons.map((lesson) => (
                <li key={lesson.slug} className="border-b border-line last:border-0">
                  <Link
                    href={`/lessons/${lesson.slug}`}
                    prefetch={true}
                    className="flex items-center gap-4 px-5 py-4 transition hover:bg-paper"
                  >
                    <LessonBadge position={lesson.position} progress={byLesson.get(lesson.slug)} />
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-ink">{lesson.title}</p>
                      <p className="truncate text-sm text-muted">{lesson.summary}</p>
                    </div>
                    <span className="shrink-0 text-sm text-muted">
                      {lesson.estimated_minutes} min
                    </span>
                  </Link>
                </li>
              ))}
            </ol>
          </div>
        ))}
      </section>
    </div>
  );
}

function LessonBadge({ position, progress }: { position: number; progress?: LessonProgress }) {
  if (progress?.status === "completed") {
    return (
      <span
        aria-label="Completed"
        className="flex size-9 shrink-0 items-center justify-center rounded-full bg-success text-white"
      >
        ✓
      </span>
    );
  }
  return (
    <span
      className={`flex size-9 shrink-0 items-center justify-center rounded-full border text-sm font-semibold ${
        progress ? "border-accent text-accent" : "border-line text-muted"
      }`}
    >
      {position}
    </span>
  );
}

function OutlineSkeleton() {
  return (
    <div className="mt-10 animate-pulse space-y-4" aria-busy="true" aria-label="Loading course">
      <div className="h-8 w-64 rounded-lg bg-line/70" />
      <div className="h-56 rounded-2xl bg-line/50" />
    </div>
  );
}

function TodayBanner({ review }: { review: ReviewSummary }) {
  const toDo = review.due_now + review.new_available_today;
  if (review.total_cards === 0 && review.new_available_today === 0) {
    return (
      <Link
        href="/words"
        className="card flex items-center justify-between gap-4 border-accent/30 bg-accent-soft px-5 py-4 transition hover:border-accent"
      >
        <span>
          <span className="block font-medium text-accent-strong">Learn the words for this unit</span>
          <span className="text-sm text-muted">A few new words a day, reviewed right before you forget them.</span>
        </span>
        <span aria-hidden="true" className="text-accent">→</span>
      </Link>
    );
  }
  return (
    <Link
      href="/review"
      className="card flex items-center justify-between gap-4 px-5 py-4 transition hover:border-accent"
    >
      <span>
        <span className="block font-medium text-ink">
          {toDo > 0 ? `${toDo} word${toDo === 1 ? "" : "s"} to review today` : "Review done for today"}
        </span>
        <span className="text-sm text-muted">
          {review.streak_days > 0 ? `${review.streak_days}-day streak · ` : ""}
          {review.mature_cards} of {review.total_cards} words known
        </span>
      </span>
      {toDo > 0 ? <span className="btn-primary px-4 py-2 text-sm">Start review</span> : null}
    </Link>
  );
}
