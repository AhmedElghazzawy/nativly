"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState, useTransition } from "react";

import { fetchMoreCards, finishSession, rateWord } from "@/app/(app)/review/actions";
import { formatInterval } from "@/lib/format";
import type { QueueCard, RatingName } from "@/lib/types";

const RATINGS: { name: RatingName; label: string; key: string; style: string }[] = [
  {
    name: "again",
    label: "Again",
    key: "1",
    style: "border-danger/40 text-danger hover:bg-danger-soft",
  },
  { name: "hard", label: "Hard", key: "2", style: "border-line text-ink hover:bg-paper" },
  {
    name: "good",
    label: "Good",
    key: "3",
    style: "border-success/40 text-success hover:bg-success-soft",
  },
  {
    name: "easy",
    label: "Easy",
    key: "4",
    style: "border-accent/40 text-accent hover:bg-accent-soft",
  },
];

export function ReviewSession({ initialCards }: { initialCards: QueueCard[] }) {
  const [cards, setCards] = useState(initialCards);
  const [revealed, setRevealed] = useState(false);
  const [reviewed, setReviewed] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const shownAt = useRef(0);

  const card = cards[0];

  useEffect(() => {
    shownAt.current = Date.now();
  }, [card?.word.slug, reviewed]);

  const rate = useCallback(
    (rating: RatingName) => {
      if (!card || pending) return;
      setError(null);
      startTransition(async () => {
        const outcome = await rateWord(card.word.slug, rating, Date.now() - shownAt.current);
        if (!outcome.ok) {
          setError(outcome.error);
          return;
        }
        setReviewed((n) => n + 1);
        setRevealed(false);
        let rest = cards.slice(1);
        if (rest.length === 0) {
          // Words still being learned (e.g. just failed) come back within the same session.
          rest = await fetchMoreCards();
          if (rest.length === 0) await finishSession();
        }
        setCards(rest);
      });
    },
    [card, cards, pending],
  );

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.target instanceof HTMLInputElement || event.metaKey || event.ctrlKey) return;
      if (!revealed && (event.key === " " || event.key === "Enter")) {
        event.preventDefault();
        setRevealed(true);
      } else if (revealed) {
        const match = RATINGS.find((r) => r.key === event.key);
        if (match) rate(match.name);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [revealed, rate]);

  if (!card) {
    return (
      <div className="card mx-auto max-w-xl p-10 text-center">
        <p className="text-sm font-medium text-accent">All done for now</p>
        <h2 className="mt-2 font-display text-3xl text-ink">
          {reviewed > 0
            ? `${reviewed} review${reviewed === 1 ? "" : "s"} done`
            : "Nothing to review"}
        </h2>
        <p className="mt-3 text-muted">
          {reviewed > 0
            ? "Words come back right before you're likely to forget them. See you tomorrow."
            : "Start a word deck to get new words every day."}
        </p>
        <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
          <Link href="/learn" className="btn-primary">
            Back to lessons
          </Link>
          <Link href="/words" className="btn-secondary">
            Browse word decks
          </Link>
        </div>
      </div>
    );
  }

  const { word } = card;
  return (
    <div className="mx-auto max-w-xl">
      <div className="mb-3 flex items-center justify-between text-sm text-muted">
        <span>
          {card.status === "new" ? (
            <span className="rounded-full bg-accent-soft px-2.5 py-0.5 font-medium text-accent-strong">
              New word
            </span>
          ) : (
            "Review"
          )}
        </span>
        <span className="tabular-nums">{cards.length} left</span>
      </div>

      <article className="card p-8 text-center sm:p-10" aria-live="polite">
        <p className="font-display text-5xl text-ink">{word.lemma}</p>
        <p className="mt-2 text-sm text-muted italic">{word.part_of_speech}</p>

        {revealed ? (
          <div className="mt-8 border-t border-line pt-6 text-left">
            <p className="text-lg text-ink">{word.definition}</p>
            <ul className="mt-4 space-y-2">
              {word.examples.map((example) => (
                <li key={example} className="rounded-xl bg-paper px-4 py-2.5 text-ink">
                  {example}
                </li>
              ))}
            </ul>
            {word.notes ? <p className="mt-4 text-sm text-muted">{word.notes}</p> : null}
          </div>
        ) : null}
      </article>

      {error ? (
        <p role="alert" className="mt-4 rounded-xl bg-danger-soft px-4 py-3 text-danger">
          {error}
        </p>
      ) : null}

      <div className="mt-6">
        {revealed ? (
          <div
            className="grid grid-cols-4 gap-2"
            role="group"
            aria-label="How well did you remember?"
          >
            {RATINGS.map((r) => (
              <button
                key={r.name}
                type="button"
                disabled={pending}
                onClick={() => rate(r.name)}
                className={`flex flex-col items-center rounded-xl border bg-card px-2 py-3 font-medium transition disabled:opacity-50 ${r.style}`}
              >
                {r.label}
                <span className="mt-0.5 text-xs font-normal text-muted tabular-nums">
                  {formatInterval(card.intervals[r.name])}
                </span>
              </button>
            ))}
          </div>
        ) : (
          <button type="button" onClick={() => setRevealed(true)} className="btn-primary w-full">
            Show answer
          </button>
        )}
        <p className="mt-3 hidden text-center text-xs text-muted sm:block">
          {revealed ? "Keys 1–4 to rate" : "Space to show the answer"}
        </p>
      </div>
    </div>
  );
}
