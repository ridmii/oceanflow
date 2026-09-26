// src/lib/format.ts
// Date/time formatting helpers. Kept separate so they can be unit-tested.

/**
 * Given a simulation start date string and a frame offset,
 * return a human-readable UTC timestamp string.
 */
export function frameToDateString(
  startDate: string,
  frameIndex: number,
  timeStepHours: number,
): string {
  const ms = new Date(startDate).getTime() + frameIndex * timeStepHours * 3_600_000;
  const d = new Date(ms);
  const pad = (n: number, w = 2) => n.toString().padStart(w, '0');
  return (
    `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ` +
    `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`
  );
}

/** Format a number with fixed decimal places for display. */
export function fmtNum(value: number, decimals = 1): string {
  return value.toFixed(decimals);
}

/** Format bytes to human-readable string. */
export function fmtBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
