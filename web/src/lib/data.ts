import "server-only";

import { apiFetch } from "@/lib/api";
import type { CourseDetail, CourseSummary, LessonDetail, Progress } from "@/lib/types";

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
