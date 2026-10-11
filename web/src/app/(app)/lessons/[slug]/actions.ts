"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import type { AttemptResult, ExerciseResponse, LessonProgress } from "@/lib/types";

export type ActionResult<T> = { ok: true; data: T } | { ok: false; error: string };

// Each action authenticates on its own via apiFetch (the proxy alone isn't an auth boundary).

export async function submitAttempt(
  exerciseSlug: string,
  lessonSlug: string,
  response: ExerciseResponse,
  durationMs: number,
): Promise<ActionResult<AttemptResult>> {
  try {
    const data = await apiFetch<AttemptResult>(
      `/exercises/${encodeURIComponent(exerciseSlug)}/attempts`,
      {
        method: "POST",
        body: JSON.stringify({
          response,
          lesson_slug: lessonSlug,
          duration_ms: Math.min(Math.max(Math.round(durationMs), 0), 3_600_000),
        }),
      },
    );
    return { ok: true, data };
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, error: error.detail };
    throw error; // includes Next's redirect() to /login, which must propagate
  }
}

export async function completeLesson(lessonSlug: string): Promise<ActionResult<LessonProgress>> {
  try {
    const data = await apiFetch<LessonProgress>(
      `/lessons/${encodeURIComponent(lessonSlug)}/complete`,
      { method: "POST" },
    );
    revalidatePath("/learn");
    revalidatePath("/progress");
    return { ok: true, data };
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, error: error.detail };
    throw error;
  }
}
