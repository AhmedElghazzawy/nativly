"use client";

import Link from "next/link";
import { useEffect, useRef, useState, useTransition } from "react";

import { completeLesson, submitAttempt } from "@/app/(app)/lessons/[slug]/actions";
import { ClozeView, McqView, ReorderView } from "@/components/lesson/exercises";
import { Markdown } from "@/components/lesson/markdown";
import { joinTokens, splitCloze } from "@/lib/text";
import type { AttemptResult, Exercise, ExerciseResponse, LessonDetail, LessonProgress } from "@/lib/types";

export function LessonPlayer({ lesson }: { lesson: LessonDetail }) {
  const [index, setIndex] = useState(0);
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [finished, setFinished] = useState<LessonProgress | null>(null);
  const [pending, startTransition] = useTransition();
  const shownAt = useRef(0);

  // Time each step from when it appears; sent with attempts as duration_ms.
  useEffect(() => {
    shownAt.current = Date.now();
  }, [index]);

  const step = lesson.steps[index];
  const isLast = index === lesson.steps.length - 1;
  const exercise = step.exercise ?? null;
  const canContinue = !exercise || result !== null;

  function next() {
    setError(null);
    if (!isLast) {
      setIndex(index + 1);
      setResult(null);
      return;
    }
    startTransition(async () => {
      const outcome = await completeLesson(lesson.slug);
      if (outcome.ok) setFinished(outcome.data);
      else setError(outcome.error);
    });
  }

  function submit(response: ExerciseResponse) {
    if (!exercise) return;
    setError(null);
    startTransition(async () => {
      const outcome = await submitAttempt(
        exercise.slug,
        lesson.slug,
        response,
        Date.now() - shownAt.current,
      );
      if (outcome.ok) setResult(outcome.data);
      else setError(outcome.error);
    });
  }

  if (finished) return <LessonComplete lesson={lesson} progress={finished} />;

  return (
    <div className="mx-auto max-w-2xl">
      <div className="flex items-center gap-4">
        <Link href={`/learn/${lesson.course_slug}`} aria-label="Back to course" className="text-2xl leading-none text-muted hover:text-ink">
          ×
        </Link>
        <div
          className="h-2 flex-1 overflow-hidden rounded-full bg-line/70"
          role="progressbar"
          aria-label="Lesson progress"
          aria-valuenow={index + (canContinue ? 1 : 0)}
          aria-valuemin={0}
          aria-valuemax={lesson.steps.length}
        >
          <div
            className="h-full rounded-full bg-accent transition-[width] duration-500"
            style={{ width: `${((index + (canContinue ? 1 : 0)) / lesson.steps.length) * 100}%` }}
          />
        </div>
        <span className="text-sm text-muted tabular-nums">
          {index + 1}/{lesson.steps.length}
        </span>
      </div>

      <p className="mt-8 text-sm font-medium text-accent">{lesson.title}</p>

      <article key={index} className="card mt-3 p-6 sm:p-8">
        {exercise ? (
          <>
            <h2 className="mb-6 font-display text-2xl text-ink">{exercise.prompt}</h2>
            <ExerciseView exercise={exercise} result={result} submitting={pending} onSubmit={submit} />
          </>
        ) : (
          <>
            {step.title ? <h2 className="mb-5 font-display text-3xl text-ink">{step.title}</h2> : null}
            <Markdown>{step.body ?? ""}</Markdown>
          </>
        )}
      </article>

      {result && exercise ? <Feedback result={result} exercise={exercise} /> : null}
      {error ? (
        <p role="alert" className="mt-4 rounded-xl bg-danger-soft px-4 py-3 text-danger">
          {error}
        </p>
      ) : null}

      {canContinue ? (
        <div className="mt-6 flex justify-end">
          <button type="button" onClick={next} disabled={pending} className="btn-primary min-w-40" autoFocus>
            {pending ? "Saving…" : isLast ? "Finish lesson" : "Continue"}
          </button>
        </div>
      ) : null}
    </div>
  );
}

function ExerciseView(props: {
  exercise: Exercise;
  result: AttemptResult | null;
  submitting: boolean;
  onSubmit: (response: ExerciseResponse) => void;
}) {
  const { exercise, ...rest } = props;
  switch (exercise.type) {
    case "mcq":
      return <McqView exercise={exercise} {...rest} />;
    case "cloze":
      return <ClozeView exercise={exercise} {...rest} />;
    case "reorder":
      return <ReorderView exercise={exercise} {...rest} />;
  }
}

function correctAnswerText(exercise: Exercise, answer: AttemptResult["correct_answer"]): string {
  if (exercise.type === "mcq" && typeof answer === "number") return exercise.options[answer];
  if (exercise.type === "reorder" && Array.isArray(answer)) return joinTokens(answer);
  if (exercise.type === "cloze" && Array.isArray(answer)) {
    const parts = splitCloze(exercise.text);
    return parts.map((part, i) => part + (answer[i] ?? "")).join("");
  }
  return "";
}

function Feedback({ result, exercise }: { result: AttemptResult; exercise: Exercise }) {
  const partial = !result.is_correct && result.score > 0;
  return (
    <div
      role="status"
      className={`mt-4 rounded-2xl border p-5 ${
        result.is_correct ? "border-success/30 bg-success-soft" : "border-danger/30 bg-danger-soft"
      }`}
    >
      <p className={`font-display text-xl ${result.is_correct ? "text-success" : "text-danger"}`}>
        {result.is_correct ? "Correct!" : partial ? "Almost there" : "Not quite"}
      </p>
      {!result.is_correct ? (
        <p className="mt-2 text-ink">
          <span className="text-muted">Correct answer: </span>
          <strong>{correctAnswerText(exercise, result.correct_answer)}</strong>
        </p>
      ) : null}
      <p className="mt-2 leading-relaxed text-ink">{result.explanation}</p>
    </div>
  );
}

function LessonComplete({ lesson, progress }: { lesson: LessonDetail; progress: LessonProgress }) {
  const percent = Math.round((progress.score ?? 0) * 100);
  const message =
    percent === 100 ? "Perfect lesson." : percent >= 70 ? "Nicely done." : "Good effort. Review the explanations and try again soon.";
  return (
    <div className="card mx-auto max-w-xl p-8 text-center sm:p-10">
      <p className="text-sm font-medium text-accent">Lesson complete</p>
      <h1 className="mt-2 font-display text-3xl text-ink">{lesson.title}</h1>
      <p className="mt-6 font-display text-6xl text-ink tabular-nums">{percent}%</p>
      <p className="mt-3 text-muted">{message}</p>
      <ul className="mt-6 space-y-1 text-left text-sm text-muted">
        {lesson.objectives.map((o) => (
          <li key={o.slug}>✓ {o.can_do}</li>
        ))}
      </ul>
      <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
        <Link href={`/learn/${lesson.course_slug}`} className="btn-primary">
          Back to course
        </Link>
        <Link href="/progress" className="btn-secondary">
          See my progress
        </Link>
      </div>
    </div>
  );
}
