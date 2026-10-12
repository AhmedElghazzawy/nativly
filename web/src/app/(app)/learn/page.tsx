import type { Metadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";
import { Suspense } from "react";

import { getCourses } from "@/lib/data";

export const metadata: Metadata = { title: "Choose your level" };

const LEVEL_HINT: Record<string, string> = {
  A1: "You're new to English or know a few words.",
  A2: "You can handle simple, everyday conversations.",
  B1: "You get by in most situations and want more confidence.",
  B2: "You speak fluently on familiar topics.",
  C1: "You use English flexibly for work and study.",
  C2: "You understand virtually everything.",
};

export default function LearnIndex() {
  return (
    <Suspense fallback={<div className="h-64 animate-pulse rounded-2xl bg-line/50" />}>
      <LevelPicker />
    </Suspense>
  );
}

async function LevelPicker() {
  const [courses, jar] = await Promise.all([getCourses(), cookies()]);
  const remembered = jar.get("nativly_course")?.value;
  if (remembered && courses.some((c) => c.slug === remembered)) {
    redirect(`/learn/${remembered}`);
  }
  return (
    <>
      <h1 className="font-display text-4xl text-ink">Choose your level</h1>
      <p className="mt-2 max-w-2xl text-muted">
        Pick the level that sounds most like you. You can switch at any time, and a placement test
        is coming soon.
      </p>
      <ul className="mt-10 grid gap-4 sm:grid-cols-3">
        {courses.map((course) => (
          <li key={course.slug}>
            <Link
              href={`/learn/${course.slug}`}
              className="card flex h-full flex-col p-6 transition hover:border-accent hover:shadow-sm"
            >
              <span className="w-fit rounded-md bg-ink px-2 py-0.5 text-sm font-semibold text-white">
                {course.cefr_level}
              </span>
              <span className="mt-4 font-display text-xl text-ink">{course.title}</span>
              <span className="mt-2 text-sm text-muted">{LEVEL_HINT[course.cefr_level]}</span>
              <span className="mt-4 flex-1 text-sm text-ink">{course.description}</span>
              <span className="mt-6 text-sm font-medium text-accent">Start here →</span>
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}
