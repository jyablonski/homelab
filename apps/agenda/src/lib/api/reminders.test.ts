import { beforeEach, describe, expect, it, vi } from "vitest";

import { makeReminder } from "@/test/factories";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("./client", () => ({ apiFetch: apiFetchMock }));

import {
  completeReminder,
  createReminder,
  getReminder,
  groupReminders,
  listReminders,
  reopenReminder,
  updateReminder,
} from "./reminders";
import { reminderCreateSchema } from "@/lib/schemas";

const NOW = new Date("2026-07-03T09:00:00-07:00");

describe("groupReminders", () => {
  it("puts a reminder starting today into active", () => {
    const reminder = makeReminder({ reminder_start_date: "2026-07-03" });
    const groups = groupReminders([reminder], 7, NOW);
    expect(groups.active).toEqual([reminder]);
  });

  it("puts a past-dated incomplete reminder into active", () => {
    const reminder = makeReminder({ reminder_start_date: "2026-06-01" });
    const groups = groupReminders([reminder], 7, NOW);
    expect(groups.active).toEqual([reminder]);
  });

  it("puts a reminder starting within the due-soon window into dueSoon", () => {
    const reminder = makeReminder({ reminder_start_date: "2026-07-08" });
    const groups = groupReminders([reminder], 7, NOW);
    expect(groups.dueSoon).toEqual([reminder]);
    expect(groups.upcoming).toEqual([]);
  });

  it("puts a reminder starting after the due-soon window into upcoming", () => {
    const reminder = makeReminder({ reminder_start_date: "2026-08-01" });
    const groups = groupReminders([reminder], 7, NOW);
    expect(groups.upcoming).toEqual([reminder]);
    expect(groups.dueSoon).toEqual([]);
  });

  it("puts completed reminders into completed regardless of date", () => {
    const reminder = makeReminder({
      reminder_start_date: "2026-08-01",
      is_completed: true,
    });
    const groups = groupReminders([reminder], 7, NOW);
    expect(groups.completed).toEqual([reminder]);
    expect(groups.upcoming).toEqual([]);
  });
});

describe("reminderCreateSchema", () => {
  it("accepts the oil change example payload", () => {
    const result = reminderCreateSchema.safeParse({
      reminder_type: "car",
      reminder_message: "Oil change completed on June 1, 2025; get it done soon.",
      reminder_start_date: "2026-06-01",
    });
    expect(result.success).toBe(true);
  });

  it("accepts the Keurig water filter example payload with an end date", () => {
    const result = reminderCreateSchema.safeParse({
      reminder_type: "house",
      reminder_message: "Change Keurig water filters.",
      reminder_start_date: "2025-09-01",
      reminder_end_date: "2025-09-08",
    });
    expect(result.success).toBe(true);
  });

  it("rejects a payload missing the reminder message", () => {
    const result = reminderCreateSchema.safeParse({
      reminder_type: "house",
      reminder_message: "",
      reminder_start_date: "2025-09-01",
    });
    expect(result.success).toBe(false);
  });
});

describe("reminder API calls", () => {
  const reminder = makeReminder();

  beforeEach(() => {
    apiFetchMock.mockReset();
  });

  it("listReminders requests the full list with a high limit", async () => {
    apiFetchMock.mockResolvedValue([reminder]);

    const result = await listReminders({ includeCompleted: false });

    expect(apiFetchMock).toHaveBeenCalledWith("/reminders", {
      query: { include_completed: false, limit: 500 },
      cache: "no-store",
    });
    expect(result).toEqual([reminder]);
  });

  it("getReminder fetches a single reminder by id", async () => {
    apiFetchMock.mockResolvedValue(reminder);

    const result = await getReminder(reminder.id);

    expect(apiFetchMock).toHaveBeenCalledWith(`/reminders/${reminder.id}`, {
      cache: "no-store",
    });
    expect(result).toEqual(reminder);
  });

  it("createReminder POSTs the input payload", async () => {
    apiFetchMock.mockResolvedValue(reminder);
    const input = {
      reminder_type: "car",
      reminder_message: "Get oil changed soon",
      reminder_start_date: "2026-06-01",
    };

    await createReminder(input);

    expect(apiFetchMock).toHaveBeenCalledWith("/reminders", {
      method: "POST",
      body: input,
    });
  });

  it("updateReminder PATCHes the changed fields", async () => {
    apiFetchMock.mockResolvedValue(reminder);

    await updateReminder(reminder.id, { is_completed: true });

    expect(apiFetchMock).toHaveBeenCalledWith(`/reminders/${reminder.id}`, {
      method: "PATCH",
      body: { is_completed: true },
    });
  });

  it("completeReminder marks a reminder completed with a timestamp", async () => {
    apiFetchMock.mockResolvedValue({ ...reminder, is_completed: true });

    await completeReminder(reminder.id);

    const [, options] = apiFetchMock.mock.calls[0];
    expect(options.body.is_completed).toBe(true);
    expect(typeof options.body.completed_at).toBe("string");
  });

  it("reopenReminder clears completion state", async () => {
    apiFetchMock.mockResolvedValue({ ...reminder, is_completed: false });

    await reopenReminder(reminder.id);

    expect(apiFetchMock).toHaveBeenCalledWith(`/reminders/${reminder.id}`, {
      method: "PATCH",
      body: { is_completed: false, completed_at: null },
    });
  });
});
