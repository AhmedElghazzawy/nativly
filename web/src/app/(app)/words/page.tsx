import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";

import { DeckButton } from "@/components/review/deck-button";
import { getDecks } from "@/lib/data";

export const metadata: Metadata = { title: "Words" };

export default function WordsPage() {
  return (
    <>
      <h1 className="font-display text-4xl text-ink">Word decks</h1>
      <p className="mt-2 text-muted">
        Study a deck and its words join your daily review, a few new ones each day.
      </p>
      <Suspense fallback={<div className="mt-10 h-48 animate-pulse rounded-2xl bg-line/50" />}>
        <Decks />
      </Suspense>
    </>
  );
}

async function Decks() {
  const decks = await getDecks();
  if (decks.length === 0) {
    return <p className="mt-10 text-muted">No word decks are published yet.</p>;
  }
  return (
    <ul className="mt-10 grid gap-4 sm:grid-cols-2">
      {decks.map((deck) => {
        const percent = deck.total ? Math.round((deck.studied / deck.total) * 100) : 0;
        return (
          <li key={deck.slug} className="card flex flex-col p-6">
            <div className="flex items-center gap-2">
              <span className="rounded-md bg-ink px-2 py-0.5 text-xs font-semibold text-white">
                {deck.cefr_level}
              </span>
              {deck.subscribed ? (
                <span className="text-xs font-medium text-accent">Studying</span>
              ) : null}
            </div>
            <Link href={`/words/${deck.slug}`} className="mt-3 font-display text-xl text-ink hover:text-accent">
              {deck.title}
            </Link>
            <p className="mt-1 flex-1 text-sm text-muted">{deck.description}</p>
            <div className="mt-5 h-2 overflow-hidden rounded-full bg-paper" aria-hidden="true">
              <div className="h-full rounded-full bg-accent" style={{ width: `${percent}%` }} />
            </div>
            <div className="mt-2 flex items-center justify-between gap-3">
              <span className="text-sm text-muted tabular-nums">
                {deck.studied} of {deck.total} words started
              </span>
              <DeckButton slug={deck.slug} subscribed={deck.subscribed} />
            </div>
          </li>
        );
      })}
    </ul>
  );
}
