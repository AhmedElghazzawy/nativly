import "server-only";

import { cookies } from "next/headers";

import { apiFetch } from "@/lib/api";
import type {
  CourseDetail,
  CourseSummary,
  DeckDetail,
  DeckSummary,
  LessonDetail,
  Mistake,
  Progress,
  QueueCard,
  ReviewSummary,
} from "@/lib/types";

export const TZ_COOKIE = "nativly_tz";
const IANA = /^[A-Za-z][A-Za-z0-9_+-]*(\/[A-Za-z0-9_+-]+)*$/;

/** The learner's IANA timezone (set by <TimezoneCookie />), so "today" is their today. */
export async function learnerTimezone(): Promise<string> {
  const tz = (await cookies()).get(TZ_COOKIE)?.value;
  return tz && IANA.test(tz) ? tz : "UTC";
}

// Data Access Layer: every read goes through apiFetch, which authenticates as the current
// learner. Pages never call fetch directly.

export function getCourses(): Promise<CourseSummary[]> {
  return apiFetch<CourseSummary[]>("/courses");
}

export function getCourse(slug: string): Promise<CourseDetail> {
  return apiFetch<CourseDetail>(`/courses/${encodeURIComponent(slug)}`);
}

export function getLesson(slug: string): Promise<LessonDetail> {
  return apiFetch<LessonDetail>(`/lessons/${encodeURIComponent(slug)}`);
}

export function getProgress(): Promise<Progress> {
  return apiFetch<Progress>("/me/progress");
}

export function getDecks(): Promise<DeckSummary[]> {
  return apiFetch<DeckSummary[]>("/decks");
}

export function getDeck(slug: string): Promise<DeckDetail> {
  return apiFetch<DeckDetail>(`/decks/${encodeURIComponent(slug)}`);
}

export async function getReviewQueue(limit = 20): Promise<QueueCard[]> {
  const tz = encodeURIComponent(await learnerTimezone());
  return apiFetch<QueueCard[]>(`/review/queue?limit=${limit}&tz=${tz}`);
}

export async function getReviewSummary(): Promise<ReviewSummary> {
  const tz = encodeURIComponent(await learnerTimezone());
  return apiFetch<ReviewSummary>(`/review/summary?tz=${tz}`);
}

export function getMistakes(limit = 10): Promise<Mistake[]> {
  return apiFetch<Mistake[]>(`/me/mistakes?limit=${limit}`);
}
