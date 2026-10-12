"use server";

import { revalidatePath } from "next/cache";

import { ApiError, apiFetch } from "@/lib/api";
import type { PlacementState } from "@/lib/types";

export type ActionResult<T> = { ok: true; data: T } | { ok: false; error: string };

async function call(path: string, body?: unknown): Promise<ActionResult<PlacementState>> {
  try {
    const data = await apiFetch<PlacementState>(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (data.status === "completed") revalidatePath("/learn", "layout");
    return { ok: true, data };
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, error: error.detail };
    throw error;
  }
}

export async function startPlacement(): Promise<ActionResult<PlacementState>> {
  return call("/placement/sessions");
}

export async function answerPlacement(
  sessionId: string,
  itemSlug: string,
  choice: number,
  durationMs: number,
): Promise<ActionResult<PlacementState>> {
  return call(`/placement/sessions/${encodeURIComponent(sessionId)}/answers`, {
    item_slug: itemSlug,
    choice,
    duration_ms: Math.min(Math.max(Math.round(durationMs), 0), 3_600_000),
  });
}
