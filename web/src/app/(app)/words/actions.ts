"use server";

import { revalidatePath } from "next/cache";

import { apiFetch } from "@/lib/api";

async function setStudying(slug: string, studying: boolean): Promise<void> {
  await apiFetch(`/decks/${encodeURIComponent(slug)}/subscription`, {
    method: studying ? "PUT" : "DELETE",
  });
  revalidatePath("/words");
  revalidatePath(`/words/${slug}`);
  revalidatePath("/learn", "layout");
}

export async function startDeck(slug: string): Promise<void> {
  await setStudying(slug, true);
}

export async function stopDeck(slug: string): Promise<void> {
  await setStudying(slug, false);
}
