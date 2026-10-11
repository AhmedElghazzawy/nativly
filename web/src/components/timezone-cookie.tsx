"use client";

import { useEffect } from "react";

/** Tells the server the learner's timezone, so daily limits and streaks follow their clock. */
export function TimezoneCookie() {
  useEffect(() => {
    const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
    if (tz && !document.cookie.includes(`nativly_tz=${encodeURIComponent(tz)}`)) {
      document.cookie = `nativly_tz=${encodeURIComponent(tz)}; path=/; max-age=31536000; samesite=lax`;
    }
  }, []);
  return null;
}
