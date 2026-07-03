export type PersonalCalendarEvent = {
  id: string;
  title: string;
  /** 24-hour "HH:mm" wall-clock time; no date/timezone since this is a fixed daily schedule. */
  startTime: string;
  endTime?: string;
};

export function formatClockTime(value: string): string {
  const [hourString, minute] = value.split(":");
  const hour = Number(hourString);
  const period = hour >= 12 ? "PM" : "AM";
  const displayHour = hour % 12 === 0 ? 12 : hour % 12;
  return `${displayHour}:${minute} ${period}`;
}
