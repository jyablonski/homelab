import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const listRemindersMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/reminders", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/reminders")>();
  return { ...actual, listReminders: listRemindersMock };
});

import { makeReminder } from "@/test/factories";

import UpcomingPage from "./page";

function daysFromNow(days: number): string {
  const date = new Date(Date.now() + days * 24 * 60 * 60 * 1000);
  return date.toISOString().slice(0, 10);
}

describe("UpcomingPage", () => {
  it("splits reminders into due-soon and later sections", async () => {
    listRemindersMock.mockResolvedValue([
      makeReminder({
        id: 1,
        reminder_message: "Pay bill",
        reminder_start_date: daysFromNow(3),
      }),
      makeReminder({
        id: 2,
        reminder_message: "Far out",
        reminder_start_date: daysFromNow(60),
      }),
    ]);

    const ui = await UpcomingPage();
    render(ui);

    expect(screen.getByRole("heading", { name: "Upcoming" })).toBeInTheDocument();
    expect(screen.getByText("Pay bill")).toBeInTheDocument();
    expect(screen.getByText("Far out")).toBeInTheDocument();
  });

  it("renders empty states when there are no reminders", async () => {
    listRemindersMock.mockResolvedValue([]);

    const ui = await UpcomingPage();
    render(ui);

    expect(screen.getByText("Nothing due in the next week")).toBeInTheDocument();
    expect(screen.getByText("No reminders further out")).toBeInTheDocument();
  });
});
