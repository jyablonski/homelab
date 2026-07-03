import { config } from "@/lib/config";

const dateTimeDateFormatter = new Intl.DateTimeFormat("en-US", {
  timeZone: config.timezone,
  month: "short",
  day: "numeric",
  year: "numeric",
});

const timeFormatter = new Intl.DateTimeFormat("en-US", {
  timeZone: config.timezone,
  hour: "numeric",
  minute: "2-digit",
});

// Plain `YYYY-MM-DD` values (reminder start/end dates) have no time-of-day, so
// format them in UTC: converting to America/Los_Angeles first would shift the
// UTC-midnight instant back to the previous calendar day for part of the year.
const dateOnlyFormatter = new Intl.DateTimeFormat("en-US", {
  timeZone: "UTC",
  month: "short",
  day: "numeric",
  year: "numeric",
});

const shortDateOnlyFormatter = new Intl.DateTimeFormat("en-US", {
  timeZone: "UTC",
  month: "short",
  day: "numeric",
});

const weekdayDateFormatter = new Intl.DateTimeFormat("en-US", {
  timeZone: config.timezone,
  weekday: "long",
  month: "long",
  day: "numeric",
});

const dayKeyFormatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: config.timezone,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/** Formats a plain `YYYY-MM-DD` reminder date, e.g. "Jun 1, 2026". */
export function formatDate(value: string): string {
  return dateOnlyFormatter.format(new Date(`${value}T00:00:00Z`));
}

/** Formats a plain `YYYY-MM-DD` reminder date without a year, e.g. "Jun 1". */
export function formatShortDate(value: string): string {
  return shortDateOnlyFormatter.format(new Date(`${value}T00:00:00Z`));
}

/** Formats a datetime as e.g. "Friday, July 3", for the Today page header. */
export function formatWeekdayDate(value: string | Date = new Date()): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return weekdayDateFormatter.format(date);
}

/** Formats a past ISO datetime relative to now, e.g. "21h ago", "3d ago". */
export function formatRelativeTime(value: string, now = new Date()): string {
  const diffMs = now.getTime() - new Date(value).getTime();
  const minutes = Math.round(diffMs / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  return `${days}d ago`;
}

/** Formats a full ISO datetime (e.g. an event `start_at`) in LA-local time. */
export function formatTime(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return timeFormatter.format(date);
}

export function formatDateTime(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return `${dateTimeDateFormatter.format(date)}, ${formatTime(date)}`;
}

/** LA-local calendar day as `YYYY-MM-DD`, for grouping items by date regardless of server timezone. */
export function dayKey(value: string | Date): string {
  const date = typeof value === "string" ? new Date(value) : value;
  return dayKeyFormatter.format(date);
}
