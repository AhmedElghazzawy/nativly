"use client";

import { useState, useTransition } from "react";

import { submitWriting } from "@/app/(app)/lessons/[slug]/actions";
import { countWords, diffWords } from "@/lib/diff";
import type { WritingFeedback, WritingTask } from "@/lib/types";

const CATEGORY: Record<string, string> = {
  grammar: "Grammar",
  vocabulary: "Vocabulary",
  spelling: "Spelling",
  punctuation: "Punctuation",
  word_order: "Word order",
  style: "Style",
};

type Props = {
  task: WritingTask;
  /** Called once the learner has feedback (or chose to continue without it). */
  onDone: () => void;
};

export function WritingView({ task, onDone }: Props) {
  const [text, setText] = useState("");
  const [feedback, setFeedback] = useState<WritingFeedback | null>(null);
  const [submitted, setSubmitted] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();

  const words = countWords(text);
  const tooShort = words < task.min_words;
  const tooLong = words > task.max_words;

  function submit() {
    setError(null);
    startTransition(async () => {
      const outcome = await submitWriting(task.slug, text);
      if (outcome.ok) {
        setFeedback(outcome.data.feedback);
        setSubmitted(outcome.data.text);
        onDone();
      } else {
        setError(outcome.error);
      }
    });
  }

  if (feedback) return <Feedback feedback={feedback} original={submitted} />;

  return (
    <div>
      {task.guidance.length > 0 ? (
        <ul className="mb-5 space-y-1.5 text-muted">
          {task.guidance.map((g) => (
            <li key={g} className="flex gap-2">
              <span aria-hidden="true" className="text-accent">
                ✓
              </span>
              {g}
            </li>
          ))}
        </ul>
      ) : null}
      <label htmlFor="writing" className="sr-only">
        Your text
      </label>
      <textarea
        id="writing"
        value={text}
        onChange={(e) => setText(e.target.value)}
        disabled={pending}
        rows={8}
        spellCheck={false}
        placeholder="Start writing here…"
        className="field resize-y text-[1.0625rem] leading-relaxed"
      />
      <div className="mt-2 flex items-center justify-between text-sm">
        <span className={tooLong ? "text-danger" : tooShort ? "text-muted" : "text-success"}>
          {words} / {task.min_words}–{task.max_words} words
        </span>
        <span className="text-xs text-muted">
          Spell-check is off: let your teacher see your real spelling.
        </span>
      </div>

      {error ? (
        <div role="alert" className="mt-4 rounded-xl bg-danger-soft px-4 py-3 text-danger">
          <p>{error}</p>
          <button type="button" onClick={onDone} className="mt-2 text-sm font-medium underline">
            Continue without feedback
          </button>
        </div>
      ) : null}

      <button
        type="button"
        onClick={submit}
        disabled={tooShort || tooLong || pending}
        className="btn-primary mt-6 w-full sm:w-auto"
      >
        {pending ? "Your teacher is reading…" : "Get feedback"}
      </button>
    </div>
  );
}

function Feedback({ feedback, original }: { feedback: WritingFeedback; original: string }) {
  const parts = diffWords(original, feedback.corrected_text);
  const scores = [
    ["Task", feedback.scores.task],
    ["Grammar", feedback.scores.grammar],
    ["Vocabulary", feedback.scores.vocabulary],
    ["Organisation", feedback.scores.organisation],
  ] as const;

  return (
    <div className="space-y-6" role="status">
      <div className="flex flex-wrap items-center gap-3">
        <span className="rounded-md bg-ink px-2.5 py-1 text-sm font-semibold text-white">
          {feedback.cefr_estimate}
        </span>
        <span className="text-muted">Your writing shows this level.</span>
      </div>

      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {scores.map(([label, score]) => (
          <div key={label} className="rounded-xl bg-paper px-3 py-2.5">
            <dt className="text-xs text-muted">{label}</dt>
            <dd className="mt-1 flex gap-1" aria-label={`${score} out of 5`}>
              {[1, 2, 3, 4, 5].map((n) => (
                <span
                  key={n}
                  className={`h-1.5 flex-1 rounded-full ${n <= score ? "bg-accent" : "bg-line"}`}
                />
              ))}
            </dd>
          </div>
        ))}
      </dl>

      <section>
        <h3 className="font-display text-lg text-ink">Corrected text</h3>
        <p className="mt-2 rounded-xl border border-line bg-card px-4 py-3 text-[1.0625rem] leading-relaxed text-ink">
          {parts.map((part, i) =>
            part.type === "same" ? (
              <span key={i}>{part.text} </span>
            ) : part.type === "removed" ? (
              <del key={i} className="text-danger decoration-danger/70">
                {part.text}{" "}
              </del>
            ) : (
              <ins
                key={i}
                className="rounded bg-success-soft px-0.5 font-medium text-success no-underline"
              >
                {part.text}{" "}
              </ins>
            ),
          )}
        </p>
      </section>

      {feedback.errors.length > 0 ? (
        <section>
          <h3 className="font-display text-lg text-ink">
            {feedback.errors.length} thing{feedback.errors.length === 1 ? "" : "s"} to fix
          </h3>
          <ul className="mt-2 space-y-2">
            {feedback.errors.map((e, i) => (
              <li key={`${e.original}-${i}`} className="rounded-xl border border-line px-4 py-3">
                <p className="flex flex-wrap items-baseline gap-x-2">
                  <span className="text-danger line-through">{e.original}</span>
                  <span aria-hidden="true" className="text-muted">
                    →
                  </span>
                  <span className="font-medium text-success">{e.correction}</span>
                  <span className="ml-auto rounded-full bg-paper px-2 py-0.5 text-xs text-muted">
                    {CATEGORY[e.category] ?? e.category}
                  </span>
                </p>
                <p className="mt-1 text-sm text-ink">{e.explanation}</p>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <p className="rounded-xl bg-success-soft px-4 py-3 text-success">
          No mistakes found. Excellent!
        </p>
      )}

      <section className="grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl bg-success-soft px-4 py-3">
          <h3 className="text-sm font-semibold text-success">What you did well</h3>
          <ul className="mt-1 list-disc space-y-1 pl-4 text-sm text-ink">
            {feedback.strengths.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
        <div className="rounded-xl bg-accent-soft px-4 py-3">
          <h3 className="text-sm font-semibold text-accent-strong">Next time</h3>
          <p className="mt-1 text-sm text-ink">{feedback.next_step}</p>
        </div>
      </section>
    </div>
  );
}
