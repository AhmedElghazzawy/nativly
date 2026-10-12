import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { DeckButton } from "@/components/review/deck-button";
import { ApiError } from "@/lib/api";
import { getDeck } from "@/lib/data";
import type { DeckWord } from "@/lib/types";

const STATUS: Record<DeckWord["status"], { label: string; style: string }> = {
  new: { label: "New", style: "bg-paper text-muted" },
  learning: { label: "Learning", style: "bg-accent-soft text-accent-strong" },
  young: { label: "Reviewing", style: "bg-success-soft text-success" },
  mature: { label: "Known", style: "bg-success text-white" },
};

export default function DeckPage({ params }: PageProps<"/words/[slug]">) {
  return (
    <Suspense fallback={<div className="h-96 animate-pulse rounded-2xl bg-line/50" />}>
      <Deck params={params} />
    </Suspense>
  );
}

async function Deck({ params }: Pick<PageProps<"/words/[slug]">, "params">) {
  const { slug } = await params;
  const deck = await getDeck(slug).catch((error: unknown) => {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  });
  return (
    <>
      <Link href="/words" className="text-sm text-muted hover:text-ink">
        ← All decks
      </Link>
      <div className="mt-4 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="font-display text-4xl text-ink">{deck.title}</h1>
          <p className="mt-2 max-w-2xl text-muted">{deck.description}</p>
        </div>
        <DeckButton slug={deck.slug} subscribed={deck.subscribed} />
      </div>
      <ul className="card mt-8 divide-y divide-line">
        {deck.words.map((w) => (
          <li key={w.slug} className="flex items-start gap-4 px-5 py-4">
            <div className="min-w-0 flex-1">
              <p className="font-medium text-ink">
                {w.lemma}{" "}
                <span className="text-sm font-normal text-muted italic">{w.part_of_speech}</span>
              </p>
              <p className="text-sm text-muted">{w.definition}</p>
              {w.notes ? <p className="mt-1 text-xs text-muted">{w.notes}</p> : null}
            </div>
            <span
              className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS[w.status].style}`}
            >
              {STATUS[w.status].label}
            </span>
          </li>
        ))}
      </ul>
    </>
  );
}
