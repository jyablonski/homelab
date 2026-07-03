import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ReminderList } from "./reminder-list";
import type { ReminderCardData } from "./types";

function reminder(overrides: Partial<ReminderCardData> = {}): ReminderCardData {
  return {
    id: 1,
    reminder_type: "house",
    reminder_message: "Change Keurig water filters",
    reminder_start_date: "2025-09-01",
    reminder_end_date: null,
    is_completed: false,
    ...overrides,
  };
}

describe("ReminderList", () => {
  it("renders an empty state when there are no reminders", () => {
    render(<ReminderList reminders={[]} emptyTitle="Nothing here" />);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
  });

  it("renders one card per reminder", () => {
    render(
      <ReminderList
        reminders={[reminder({ id: 1 }), reminder({ id: 2, reminder_message: "Other" })]}
        emptyTitle="Nothing here"
      />,
    );
    expect(screen.getByText("Change Keurig water filters")).toBeInTheDocument();
    expect(screen.getByText("Other")).toBeInTheDocument();
  });

  it("groups reminders under a date heading when groupByDate is set", () => {
    render(
      <ReminderList
        reminders={[reminder({ reminder_start_date: "2025-09-01" })]}
        emptyTitle="Nothing here"
        groupByDate
      />,
    );
    expect(screen.getByText("Sep 1, 2025")).toBeInTheDocument();
  });
});
