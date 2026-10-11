/** Compact "time until" labels for review buttons: <1m, 10m, 3h, 4d, 2mo, 1.5y. */
export function formatInterval(seconds: number): string {
  const minute = 60;
  const hour = 60 * minute;
  const day = 24 * hour;
  if (seconds < minute) return "<1m";
  if (seconds < hour) return `${Math.round(seconds / minute)}m`;
  if (seconds < day) return `${Math.round(seconds / hour)}h`;
  if (seconds < 30 * day) return `${Math.round(seconds / day)}d`;
  if (seconds < 365 * day) return `${Math.round(seconds / (30 * day))}mo`;
  return `${(seconds / (365 * day)).toFixed(1).replace(/\.0$/, "")}y`;
}
