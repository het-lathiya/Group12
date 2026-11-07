/** A date-only string "2026-11-14" as "Sat 14 Nov" (guide §17), read in UTC so no zone shifts it. */
export function formatDayDate(isoDate: string): string {
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day)).toLocaleDateString("en-GB", {
    weekday: "short",
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  });
}
