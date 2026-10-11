"use client";

import { useTransition } from "react";

import { startDeck, stopDeck } from "@/app/(app)/words/actions";

export function DeckButton({ slug, subscribed }: { slug: string; subscribed: boolean }) {
  const [pending, startTransition] = useTransition();
  return subscribed ? (
    <button
      type="button"
      disabled={pending}
      onClick={() => startTransition(() => stopDeck(slug))}
      className="btn-secondary px-4 py-2 text-sm"
    >
      {pending ? "Stopping…" : "Stop new words"}
    </button>
  ) : (
    <button
      type="button"
      disabled={pending}
      onClick={() => startTransition(() => startDeck(slug))}
      className="btn-primary px-4 py-2 text-sm"
    >
      {pending ? "Starting…" : "Study this deck"}
    </button>
  );
}
