import { describe, expect, it } from "vitest";

import {
  dayKey,
  formatDate,
  formatRelativeTime,
  formatShortDate,
  formatWeekdayDate,
} from "./dates";

describe("dayKey", () => {
  it("returns the LA-local calendar day for a UTC instant", () => {
    // 2026-07-04T02:00:00Z is still 2026-07-03 evening in America/Los_Angeles.
    expect(dayKey(new Date("2026-07-04T02:00:00Z"))).toBe("2026-07-03");
  });
});

describe("formatDate", () => {
  it("formats a plain date string without shifting days", () => {
    expect(formatDate("2026-06-01")).toBe("Jun 1, 2026");
  });
});

describe("formatShortDate", () => {
  it("formats a plain date string without a year", () => {
    expect(formatShortDate("2026-07-05")).toBe("Jul 5");
  });
});

describe("formatWeekdayDate", () => {
  it("formats an LA-local weekday and date", () => {
    expect(formatWeekdayDate(new Date("2026-07-03T16:00:00-07:00"))).toBe(
      "Friday, July 3",
    );
  });
});

describe("formatRelativeTime", () => {
  const now = new Date("2026-07-03T09:00:00-07:00");

  it("formats minutes ago", () => {
    expect(formatRelativeTime("2026-07-03T08:50:00-07:00", now)).toBe("10m ago");
  });

  it("formats hours ago", () => {
    expect(formatRelativeTime("2026-07-02T12:00:00-07:00", now)).toBe("21h ago");
  });

  it("formats days ago", () => {
    expect(formatRelativeTime("2026-06-28T09:00:00-07:00", now)).toBe("5d ago");
  });
});
