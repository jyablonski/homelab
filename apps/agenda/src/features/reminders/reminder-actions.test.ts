import { beforeEach, describe, expect, it, vi } from "vitest";

const revalidatePathMock = vi.hoisted(() => vi.fn());
const redirectMock = vi.hoisted(() =>
  vi.fn(() => {
    throw new Error("NEXT_REDIRECT");
  }),
);
const completeReminderMock = vi.hoisted(() => vi.fn());
const createReminderMock = vi.hoisted(() => vi.fn());
const reopenReminderMock = vi.hoisted(() => vi.fn());
const updateReminderMock = vi.hoisted(() => vi.fn());

vi.mock("next/cache", () => ({ revalidatePath: revalidatePathMock }));
vi.mock("next/navigation", () => ({ redirect: redirectMock }));
vi.mock("@/lib/api/reminders", () => ({
  completeReminder: completeReminderMock,
  createReminder: createReminderMock,
  reopenReminder: reopenReminderMock,
  updateReminder: updateReminderMock,
}));

import { ApiError } from "@/lib/api/client";

import {
  completeReminderAction,
  createReminderAction,
  reopenReminderAction,
  updateReminderAction,
} from "./reminder-actions";

function formData(fields: Record<string, string>): FormData {
  const fd = new FormData();
  for (const [key, value] of Object.entries(fields)) {
    fd.set(key, value);
  }
  return fd;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("createReminderAction", () => {
  it("returns a validation error without calling the API when fields are missing", async () => {
    const result = await createReminderAction(
      {},
      formData({ reminder_type: "car" }),
    );

    expect(result.error).toMatch(/fill in/i);
    expect(createReminderMock).not.toHaveBeenCalled();
  });

  it("creates the reminder, revalidates, and redirects on success", async () => {
    createReminderMock.mockResolvedValue({});

    await expect(
      createReminderAction(
        {},
        formData({
          reminder_type: "car",
          reminder_message: "Get oil changed soon",
          reminder_start_date: "2026-06-01",
        }),
      ),
    ).rejects.toThrow("NEXT_REDIRECT");

    expect(createReminderMock).toHaveBeenCalledWith({
      reminder_type: "car",
      reminder_message: "Get oil changed soon",
      reminder_start_date: "2026-06-01",
      reminder_end_date: null,
    });
    expect(revalidatePathMock).toHaveBeenCalledWith("/");
    expect(redirectMock).toHaveBeenCalledWith("/");
  });

  it("returns the API error message instead of throwing", async () => {
    createReminderMock.mockRejectedValue(new ApiError("boom", 500));

    const result = await createReminderAction(
      {},
      formData({
        reminder_type: "car",
        reminder_message: "msg",
        reminder_start_date: "2026-06-01",
      }),
    );

    expect(result.error).toBe("boom");
    expect(redirectMock).not.toHaveBeenCalled();
  });
});

describe("updateReminderAction", () => {
  it("updates the bound reminder id and redirects on success", async () => {
    updateReminderMock.mockResolvedValue({});

    await expect(
      updateReminderAction(
        42,
        {},
        formData({
          reminder_type: "house",
          reminder_message: "Change filters",
          reminder_start_date: "2025-09-01",
        }),
      ),
    ).rejects.toThrow("NEXT_REDIRECT");

    expect(updateReminderMock).toHaveBeenCalledWith(42, {
      reminder_type: "house",
      reminder_message: "Change filters",
      reminder_start_date: "2025-09-01",
      reminder_end_date: null,
    });
  });

  it("returns a fallback message for a non-ApiError failure", async () => {
    updateReminderMock.mockRejectedValue(new Error("boom"));

    const result = await updateReminderAction(
      42,
      {},
      formData({
        reminder_type: "house",
        reminder_message: "Change filters",
        reminder_start_date: "2025-09-01",
      }),
    );

    expect(result.error).toBe("Failed to update reminder.");
  });
});

describe("completeReminderAction / reopenReminderAction", () => {
  it("completes a reminder and revalidates reminder pages", async () => {
    await completeReminderAction(7);

    expect(completeReminderMock).toHaveBeenCalledWith(7);
    expect(revalidatePathMock).toHaveBeenCalledWith("/upcoming");
    expect(revalidatePathMock).toHaveBeenCalledWith("/completed");
  });

  it("reopens a reminder and revalidates reminder pages", async () => {
    await reopenReminderAction(7);

    expect(reopenReminderMock).toHaveBeenCalledWith(7);
    expect(revalidatePathMock).toHaveBeenCalledWith("/");
  });
});
