"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import { getReviewQueue } from "@/lib/data";
import type { QueueCard, RatingName, ReviewResult } from "@/lib/types";

export type ActionResult<T> = { ok: true; data: T } | { ok: false; error: string };

export async function rateWord(
  wordSlug: string,
  rating: RatingName,
  durationMs: number,
): Promise<ActionResult<ReviewResult>> {
  try {
    const data = await apiFetch<ReviewResult>(`/review/${encodeURIComponent(wordSlug)}`, {
      method: "POST",
      body: JSON.stringify({
        rating,
        duration_ms: Math.min(Math.max(Math.round(durationMs), 0), 3_600_000),
      }),
    });
    return { ok: true, data };
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, error: error.detail };
    throw error;
  }
}

/** Called when the local queue runs out: words failed minutes ago may be due again. */
export async function fetchMoreCards(): Promise<QueueCard[]> {
  return getReviewQueue();
}

/** Stats on other pages (streak, due counts) change after a session. */
export async function finishSession(): Promise<void> {
  revalidatePath("/learn", "layout");
  revalidatePath("/words");
}
