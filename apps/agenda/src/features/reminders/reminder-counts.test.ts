import { describe, expect, it, vi } from "vitest";

import { makeReminder } from "@/test/factories";

const listRemindersMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/reminders", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/reminders")>();
  return { ...actual, listReminders: listRemindersMock };
});

import { getReminderCounts } from "./reminder-counts";

describe("getReminderCounts", () => {
  it("sums due-soon and upcoming into the upcoming count", async () => {
    listRemindersMock.mockResolvedValue([
      makeReminder({ id: 1, reminder_start_date: "2099-01-01" }),
      makeReminder({ id: 2, reminder_start_date: "2099-02-01" }),
      makeReminder({ id: 3, is_completed: true }),
    ]);

    const counts = await getReminderCounts();

    expect(counts).toEqual({ upcoming: 2, completed: 1 });
  });

  it("returns null when the reminders API call fails", async () => {
    listRemindersMock.mockRejectedValue(new Error("network down"));

    const counts = await getReminderCounts();

    expect(counts).toBeNull();
  });
});
