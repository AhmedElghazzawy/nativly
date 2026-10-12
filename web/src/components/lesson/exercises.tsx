"use client";

import { useState } from "react";

import { joinTokens, normalize, splitCloze } from "@/lib/text";
import type {
  AttemptResult,
  ClozeExercise,
  ExerciseResponse,
  McqExercise,
  ReorderExercise,
} from "@/lib/types";

type ExerciseProps<E> = {
  exercise: E;
  result: AttemptResult | null;
  submitting: boolean;
  onSubmit: (response: ExerciseResponse) => void;
};

function CheckButton({ disabled, submitting }: { disabled: boolean; submitting: boolean }) {
  return (
    <button
      type="submit"
      disabled={disabled || submitting}
      className="btn-primary mt-8 w-full sm:w-auto"
    >
      {submitting ? "Checking…" : "Check answer"}
    </button>
  );
}

export function McqView({ exercise, result, submitting, onSubmit }: ExerciseProps<McqExercise>) {
  const [choice, setChoice] = useState<number | null>(null);
  const correct = typeof result?.correct_answer === "number" ? result.correct_answer : null;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (choice !== null) onSubmit({ type: "mcq", choice });
      }}
    >
      <fieldset disabled={Boolean(result) || submitting} className="grid gap-3">
        <legend className="sr-only">{exercise.prompt}</legend>
        {exercise.options.map((option, i) => {
          const state =
            correct === null
              ? choice === i
                ? "border-accent bg-accent-soft ring-2 ring-accent/20"
                : "border-line bg-card hover:border-accent/50"
              : i === correct
                ? "border-success bg-success-soft text-success"
                : i === choice
                  ? "border-danger bg-danger-soft text-danger"
                  : "border-line bg-card opacity-60";
          return (
            <label
              key={option}
              className={`flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3.5 text-[1.0625rem] transition has-[:disabled]:cursor-default ${state}`}
            >
              <input
                type="radio"
                name="choice"
                value={i}
                checked={choice === i}
                onChange={() => setChoice(i)}
                className="sr-only"
              />
              <span className="flex size-7 shrink-0 items-center justify-center rounded-lg border border-current/30 text-sm font-semibold">
                {String.fromCharCode(65 + i)}
              </span>
              {option}
            </label>
          );
        })}
      </fieldset>
      {!result ? <CheckButton disabled={choice === null} submitting={submitting} /> : null}
    </form>
  );
}

export function ClozeView({
  exercise,
  result,
  submitting,
  onSubmit,
}: ExerciseProps<ClozeExercise>) {
  const parts = splitCloze(exercise.text);
  const [blanks, setBlanks] = useState<string[]>(() => Array(exercise.blanks).fill(""));
  const expected = Array.isArray(result?.correct_answer) ? result.correct_answer : null;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({ type: "cloze", blanks });
      }}
    >
      <p className="text-xl leading-[2.6] text-ink">
        {parts.map((part, i) => (
          <span key={i}>
            {part}
            {i < exercise.blanks ? (
              <input
                aria-label={`Blank ${i + 1}`}
                value={blanks[i]}
                disabled={Boolean(result) || submitting}
                autoComplete="off"
                autoCapitalize="off"
                spellCheck={false}
                onChange={(e) =>
                  setBlanks((prev) => prev.map((v, j) => (j === i ? e.target.value : v)))
                }
                size={Math.max(6, blanks[i].length + 1)}
                className={`mx-1 inline-block rounded-lg border-b-2 bg-paper px-2 py-0.5 text-center font-medium outline-none focus:border-accent ${
                  expected === null
                    ? "border-line"
                    : // Display hint only; the server already decided the score.
                      normalize(blanks[i]) === normalize(expected[i])
                      ? "border-success bg-success-soft text-success"
                      : "border-danger bg-danger-soft text-danger"
                }`}
              />
            ) : null}
          </span>
        ))}
      </p>
      {!result ? (
        <CheckButton disabled={blanks.some((b) => !b.trim())} submitting={submitting} />
      ) : null}
    </form>
  );
}

export function ReorderView({
  exercise,
  result,
  submitting,
  onSubmit,
}: ExerciseProps<ReorderExercise>) {
  // Track token *indices* so repeated words ("the", "the") stay distinct.
  const [picked, setPicked] = useState<number[]>([]);
  const locked = Boolean(result) || submitting;
  const sentence = picked.map((i) => exercise.tokens[i]);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit({ type: "reorder", sequence: sentence });
      }}
    >
      <div
        className={`flex min-h-16 flex-wrap items-center gap-2 rounded-xl border-2 border-dashed px-3 py-3 ${
          result
            ? result.is_correct
              ? "border-success bg-success-soft"
              : "border-danger bg-danger-soft"
            : "border-line"
        }`}
        aria-label="Your sentence"
      >
        {picked.length === 0 ? (
          <span className="px-1 text-muted">Tap the words below in the right order.</span>
        ) : null}
        {picked.map((tokenIndex, position) => (
          <button
            key={tokenIndex}
            type="button"
            disabled={locked}
            onClick={() => setPicked((prev) => prev.filter((_, p) => p !== position))}
            className="rounded-lg border border-accent/40 bg-card px-3 py-1.5 font-medium text-ink shadow-xs"
          >
            {exercise.tokens[tokenIndex]}
          </button>
        ))}
      </div>

      <div className="mt-5 flex flex-wrap gap-2" aria-label="Word bank">
        {exercise.tokens.map((token, i) =>
          picked.includes(i) ? (
            <span
              key={i}
              className="rounded-lg border border-dashed border-line px-3 py-1.5 text-transparent select-none"
            >
              {token}
            </span>
          ) : (
            <button
              key={i}
              type="button"
              disabled={locked}
              onClick={() => setPicked((prev) => [...prev, i])}
              className="rounded-lg border border-line bg-card px-3 py-1.5 font-medium text-ink shadow-xs transition hover:border-accent"
            >
              {token}
            </button>
          ),
        )}
      </div>
      {result && !result.is_correct && Array.isArray(result.correct_answer) ? (
        <p className="mt-4 text-sm text-muted">
          You wrote: <span className="text-danger line-through">{joinTokens(sentence)}</span>
        </p>
      ) : null}
      {!result ? (
        <CheckButton disabled={picked.length !== exercise.tokens.length} submitting={submitting} />
      ) : null}
    </form>
  );
}
