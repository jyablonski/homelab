import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const getReminderMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/reminders", () => ({ getReminder: getReminderMock }));

const notFoundMock = vi.hoisted(() =>
  vi.fn(() => {
    throw new Error("NEXT_NOT_FOUND");
  }),
);
vi.mock("next/navigation", () => ({ notFound: notFoundMock }));

import { ApiError } from "@/lib/api/client";
import { makeReminder } from "@/test/factories";

import EditReminderPage from "./page";

describe("EditReminderPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the reminder form when the reminder is found", async () => {
    getReminderMock.mockResolvedValue(makeReminder({ reminder_message: "Get oil changed" }));

    const ui = await EditReminderPage({ params: Promise.resolve({ id: "1" }) });
    render(ui);

    expect(screen.getByRole("heading", { name: "Edit reminder" })).toBeInTheDocument();
    expect(screen.getByDisplayValue("Get oil changed")).toBeInTheDocument();
  });

  it("calls notFound for a non-numeric id without calling the API", async () => {
    await expect(
      EditReminderPage({ params: Promise.resolve({ id: "not-a-number" }) }),
    ).rejects.toThrow("NEXT_NOT_FOUND");

    expect(getReminderMock).not.toHaveBeenCalled();
  });

  it("calls notFound when the API returns a 404", async () => {
    getReminderMock.mockRejectedValue(new ApiError("reminder not found", 404));

    await expect(
      EditReminderPage({ params: Promise.resolve({ id: "999" }) }),
    ).rejects.toThrow("NEXT_NOT_FOUND");
  });

  it("re-throws non-404 API errors", async () => {
    getReminderMock.mockRejectedValue(new ApiError("server error", 500));

    await expect(
      EditReminderPage({ params: Promise.resolve({ id: "1" }) }),
    ).rejects.toMatchObject({ status: 500 });
    expect(notFoundMock).not.toHaveBeenCalled();
  });
});
