"use client";

import { useEffect } from "react";

/** Remembers the learner's chosen course, so /learn reopens it next time. */
export function RememberCourse({ slug }: { slug: string }) {
  useEffect(() => {
    document.cookie = `nativly_course=${encodeURIComponent(slug)}; path=/; max-age=31536000; samesite=lax`;
  }, [slug]);
  return null;
}
