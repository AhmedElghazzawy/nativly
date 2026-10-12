"use client";

import Link from "next/link";
import { useEffect, useRef, useState, useTransition } from "react";

import { answerPlacement, startPlacement } from "@/app/(app)/placement/actions";
import { RememberCourse } from "@/components/remember-course";
import type { PlacementResult, PlacementState } from "@/lib/types";

const SKILL: Record<string, string> = {
  grammar: "Grammar",
  vocab: "Vocabulary",
  reading: "Reading",
  listening: "Listening",
  writing: "Writing",
  speaking: "Speaking",
};
const SCALE = ["A1", "A2", "B1", "B2"] as const;

export function PlacementRunner({ initial }: { initial: PlacementState | null }) {
  const [state, setState] = useState(initial);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [retaking, setRetaking] = useState(false);

  function begin() {
    setError(null);
    startTransition(async () => {
      const outcome = await startPlacement();
      if (outcome.ok) {
        setState(outcome.data);
        setRetaking(false);
      } else setError(outcome.error);
    });
  }

  if (state?.status === "completed" && state.result && !retaking) {
    return <Results result={state.result} onRetake={() => setRetaking(true)} />;
  }
  if (!state || state.status === "completed" || !state.question) {
    return <Intro onStart={begin} pending={pending} error={error} />;
  }
  // Keyed by question: each new question mounts fresh (no stale selection or timer).
  return <Question key={state.question.slug} state={state} onState={setState} />;
}

function Intro(props: { onStart: () => void; pending: boolean; error: string | null }) {
  return (
    <div className="card mx-auto max-w-xl p-8 sm:p-10">
      <h2 className="font-display text-3xl text-ink">Find your level</h2>
      <p className="mt-3 text-muted">
        18 questions in three short sections. It adapts as you go: harder after a right answer,
        easier after a wrong one. About 8 minutes.
      </p>
      <ul className="mt-6 space-y-2 text-ink">
        <li>
          <strong className="font-semibold">Grammar</strong> · 6 questions
        </li>
        <li>
          <strong className="font-semibold">Vocabulary</strong> · 6 questions
        </li>
        <li>
          <strong className="font-semibold">Reading</strong> · 6 short texts
        </li>
      </ul>
      <p className="mt-6 text-sm text-muted">
        If you don&apos;t know, choose your best guess and move on: the test adapts, so a lucky
        guess won&apos;t place you too high.
      </p>
      {props.error ? (
        <p role="alert" className="mt-4 rounded-xl bg-danger-soft px-4 py-3 text-danger">
          {props.error}
        </p>
      ) : null}
      <button
        type="button"
        onClick={props.onStart}
        disabled={props.pending}
        className="btn-primary mt-8 w-full"
      >
        {props.pending ? "Starting…" : "Start the test"}
      </button>
    </div>
  );
}

function Question({
  state,
  onState,
}: {
  state: PlacementState;
  onState: (s: PlacementState) => void;
}) {
  const [choice, setChoice] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const shownAt = useRef(0);
  const question = state.question;

  useEffect(() => {
    shownAt.current = Date.now();
  }, []);

  if (!question) return null;
  const perSkill = state.total / 3;
  const inSkill = (state.answered % perSkill) + 1;

  function submit() {
    if (choice === null || !question) return;
    setError(null);
    startTransition(async () => {
      const outcome = await answerPlacement(
        state.id,
        question.slug,
        choice,
        Date.now() - shownAt.current,
      );
      if (outcome.ok) onState(outcome.data);
      else setError(outcome.error);
    });
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="flex items-center gap-4">
        <div
          className="h-2 flex-1 overflow-hidden rounded-full bg-line/70"
          role="progressbar"
          aria-label="Test progress"
          aria-valuenow={state.answered}
          aria-valuemin={0}
          aria-valuemax={state.total}
        >
          <div
            className="h-full rounded-full bg-accent transition-[width] duration-500"
            style={{ width: `${(state.answered / state.total) * 100}%` }}
          />
        </div>
        <span className="text-sm text-muted tabular-nums">
          {state.answered + 1}/{state.total}
        </span>
      </div>
      <p className="mt-8 text-sm font-medium text-accent">
        {SKILL[question.skill]} · question {inSkill} of {perSkill}
      </p>
      <form
        className="card mt-3 p-6 sm:p-8"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        {question.passage ? (
          <blockquote className="mb-6 rounded-xl border-l-4 border-accent bg-accent-soft px-4 py-3 text-[1.0625rem] leading-relaxed text-ink">
            {question.passage}
          </blockquote>
        ) : null}
        <fieldset disabled={pending}>
          <legend className="mb-6 font-display text-2xl text-ink">{question.prompt}</legend>
          <div className="grid gap-3">
            {question.options.map((option, i) => (
              <label
                key={option}
                className={`flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3.5 text-[1.0625rem] transition ${
                  choice === i
                    ? "border-accent bg-accent-soft ring-2 ring-accent/20"
                    : "border-line bg-card hover:border-accent/50"
                }`}
              >
                <input
                  type="radio"
                  name="choice"
                  checked={choice === i}
                  onChange={() => setChoice(i)}
                  className="sr-only"
                />
                <span className="flex size-7 shrink-0 items-center justify-center rounded-lg border border-current/30 text-sm font-semibold">
                  {String.fromCharCode(65 + i)}
                </span>
                {option}
              </label>
            ))}
          </div>
        </fieldset>
        {error ? (
          <p role="alert" className="mt-4 rounded-xl bg-danger-soft px-4 py-3 text-danger">
            {error}
          </p>
        ) : null}
        <button
          type="submit"
          disabled={choice === null || pending}
          className="btn-primary mt-8 w-full sm:w-auto"
        >
          {pending ? "Saving…" : "Next"}
        </button>
      </form>
    </div>
  );
}

function Results({ result, onRetake }: { result: PlacementResult; onRetake: () => void }) {
  const course = result.recommended_course;
  return (
    <div className="card mx-auto max-w-xl p-8 text-center sm:p-10">
      {course ? <RememberCourse slug={course} /> : null}
      <p className="text-sm font-medium text-accent">Your level</p>
      <p className="mt-2 font-display text-7xl text-ink">{result.overall ?? "—"}</p>
      <p className="mt-2 text-muted">
        Based on your weakest areas, so lessons won&apos;t skip anything.
      </p>

      <ul className="mt-8 space-y-4 text-left">
        {Object.entries(result.skills).map(([skill, r]) => {
          if (!r) return null;
          const position = SCALE.indexOf(r.level as (typeof SCALE)[number]);
          return (
            <li key={skill}>
              <div className="flex items-baseline justify-between">
                <span className="font-medium text-ink">{SKILL[skill] ?? skill}</span>
                <span className="text-sm text-muted">
                  <strong className="text-ink">{r.level}</strong>
                  {r.score > 0 ? ` · ${r.score}% towards the next level` : ""}
                </span>
              </div>
              <div className="mt-2 grid grid-cols-4 gap-1" aria-hidden="true">
                {SCALE.map((level, i) => (
                  <span
                    key={level}
                    className={`h-2 rounded-full ${i <= position ? "bg-accent" : "bg-paper"}`}
                  />
                ))}
              </div>
            </li>
          );
        })}
      </ul>

      <div className="mt-10 flex flex-col justify-center gap-3 sm:flex-row">
        {course ? (
          <Link href={`/learn/${course}`} className="btn-primary">
            Start your course
          </Link>
        ) : null}
        <button type="button" onClick={onRetake} className="btn-secondary">
          Retake the test
        </button>
      </div>
    </div>
  );
}
