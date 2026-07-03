import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ReminderCard } from "./reminder-card";
import type { ReminderCardData } from "./types";

function reminder(overrides: Partial<ReminderCardData> = {}): ReminderCardData {
  return {
    id: 1,
    reminder_type: "car",
    reminder_message: "Get oil changed soon",
    reminder_start_date: "2026-06-01",
    reminder_end_date: null,
    is_completed: false,
    ...overrides,
  };
}

describe("ReminderCard", () => {
  it("shows a complete toggle and category meta for an incomplete reminder", () => {
    render(<ReminderCard reminder={reminder()} />);

    expect(screen.getByText("Get oil changed soon")).toBeInTheDocument();
    expect(screen.getByText(/Car · since Jun 1, 2026/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Mark reminder complete" }),
    ).toBeInTheDocument();
  });

  it("shows a reopen toggle and strikethrough message for a completed reminder", () => {
    render(<ReminderCard reminder={reminder({ is_completed: true })} />);

    expect(screen.getByText("Get oil changed soon")).toHaveClass("line-through");
    expect(
      screen.getByRole("button", { name: "Reopen reminder" }),
    ).toBeInTheDocument();
  });

  it("appends the end date to the meta line when present", () => {
    render(
      <ReminderCard reminder={reminder({ reminder_end_date: "2025-09-08" })} />,
    );

    expect(screen.getByText(/ends Sep 8, 2025/)).toBeInTheDocument();
  });

  it("shows a right-aligned short date instead of meta for the due-soon variant", () => {
    render(
      <ReminderCard
        reminder={reminder({ reminder_start_date: "2026-07-08" })}
        variant="due-soon"
      />,
    );

    expect(screen.getByText("Jul 8")).toBeInTheDocument();
    expect(screen.queryByText(/since/)).not.toBeInTheDocument();
  });
});
