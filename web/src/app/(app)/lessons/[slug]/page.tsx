import { notFound } from "next/navigation";
import { Suspense } from "react";

import { LessonPlayer } from "@/components/lesson/lesson-player";
import { ApiError } from "@/lib/api";
import { getLesson } from "@/lib/data";

export default function LessonPage({ params }: PageProps<"/lessons/[slug]">) {
  return (
    <Suspense
      fallback={<div className="mx-auto h-96 max-w-2xl animate-pulse rounded-2xl bg-line/50" />}
    >
      <Lesson params={params} />
    </Suspense>
  );
}

async function Lesson({ params }: Pick<PageProps<"/lessons/[slug]">, "params">) {
  const { slug } = await params;
  const lesson = await getLesson(slug).catch((error: unknown) => {
    if (error instanceof ApiError && error.status === 404) notFound();
    throw error;
  });
  return <LessonPlayer lesson={lesson} />;
}
