import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { getCourse, getCourses, getProgress } from "@/lib/data";
import type { LessonProgress } from "@/lib/types";

export const metadata: Metadata = { title: "Learn" };

export default function LearnPage() {
  return (
    <>
      <h1 className="font-display text-4xl text-ink">Your course</h1>
      <p className="mt-2 text-muted">One short lesson at a time. Explanations first, then practice.</p>
      <Suspense fallback={<OutlineSkeleton />}>
        <Courses />
      </Suspense>
    </>
  );
}

async function Courses() {
  const [courses, progress] = await Promise.all([getCourses(), getProgress()]);
  const details = await Promise.all(courses.map((c) => getCourse(c.slug)));
  const byLesson = new Map(progress.lessons.map((p) => [p.lesson_slug, p]));

  if (details.length === 0) {
    return <p className="mt-10 text-muted">No courses are published yet. Check back soon.</p>;
  }

  return (
    <div className="mt-10 space-y-12">
      {details.map((course) => (
        <section key={course.slug}>
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
      ))}
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
