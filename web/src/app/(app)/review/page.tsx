import type { Metadata } from "next";
import { Suspense } from "react";

import { ReviewSession } from "@/components/review/review-session";
import { getReviewQueue, getReviewSummary } from "@/lib/data";

export const metadata: Metadata = { title: "Review" };

export default function ReviewPage() {
  return (
    <>
      <h1 className="font-display text-4xl text-ink">Daily review</h1>
      <p className="mt-2 text-muted">
        Each word returns right before you&apos;d forget it. Be honest with your ratings.
      </p>
      <Suspense fallback={<div className="mx-auto mt-10 h-80 max-w-xl animate-pulse rounded-2xl bg-line/50" />}>
        <Session />
      </Suspense>
    </>
  );
}

async function Session() {
  const [cards, summary] = await Promise.all([getReviewQueue(), getReviewSummary()]);
  return (
    <>
      <dl className="mx-auto mt-8 mb-6 grid max-w-xl grid-cols-3 gap-3 text-center">
        <Stat label="Day streak" value={summary.streak_days} />
        <Stat label="Reviewed today" value={summary.reviewed_today} />
        <Stat label="Words studied" value={summary.total_cards} hint={`${summary.mature_cards} known`} />
      </dl>
      <ReviewSession initialCards={cards} />
    </>
  );
}

function Stat({ label, value, hint }: { label: string; value: number; hint?: string }) {
  return (
    <div className="card px-3 py-3">
      <dt className="text-xs text-muted">{label}</dt>
      <dd className="font-display text-2xl text-ink tabular-nums">
        {value}
        {hint ? <span className="ml-1 font-sans text-xs text-muted">{hint}</span> : null}
      </dd>
    </div>
  );
}
