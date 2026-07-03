import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const listRemindersMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/reminders", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api/reminders")>();
  return { ...actual, listReminders: listRemindersMock };
});

import { makeReminder } from "@/test/factories";

import CompletedPage from "./page";

describe("CompletedPage", () => {
  it("shows only completed reminders, most recently completed first", async () => {
    listRemindersMock.mockResolvedValue([
      makeReminder({
        id: 1,
        reminder_message: "Older",
        is_completed: true,
        completed_at: "2026-01-01T00:00:00Z",
      }),
      makeReminder({ id: 2, reminder_message: "Not completed", is_completed: false }),
      makeReminder({
        id: 3,
        reminder_message: "Newer",
        is_completed: true,
        completed_at: "2026-06-01T00:00:00Z",
      }),
    ]);

    const ui = await CompletedPage();
    render(ui);

    expect(screen.queryByText("Not completed")).not.toBeInTheDocument();
    const items = screen.getAllByText(/Older|Newer/);
    expect(items.map((el) => el.textContent)).toEqual(["Newer", "Older"]);
  });

  it("renders the empty state when there are no completed reminders", async () => {
    listRemindersMock.mockResolvedValue([]);

    const ui = await CompletedPage();
    render(ui);

    expect(screen.getByText("No completed reminders yet")).toBeInTheDocument();
  });
});
