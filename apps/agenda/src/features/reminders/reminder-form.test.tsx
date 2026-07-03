import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const createReminderActionMock = vi.hoisted(() => vi.fn());
const updateReminderActionMock = vi.hoisted(() => vi.fn());
const completeReminderActionMock = vi.hoisted(() => vi.fn());
const reopenReminderActionMock = vi.hoisted(() => vi.fn());

vi.mock("./reminder-actions", () => ({
  createReminderAction: createReminderActionMock,
  updateReminderAction: updateReminderActionMock,
  completeReminderAction: completeReminderActionMock,
  reopenReminderAction: reopenReminderActionMock,
}));

import { makeReminder } from "@/test/factories";

import { ReminderForm } from "./reminder-form";

describe("ReminderForm", () => {
  it("renders create-mode copy and defaults with no reminder prop", () => {
    render(<ReminderForm />);

    expect(screen.getByRole("heading", { name: "New reminder" })).toBeInTheDocument();
    expect(
      screen.getByText(/Record what happened, then choose/),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Car" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByRole("button", { name: "General" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Save reminder" })).toBeInTheDocument();
    expect(screen.queryByText("Status:")).not.toBeInTheDocument();
  });

  it("renders edit-mode copy, prefilled fields, and a complete toggle", () => {
    const reminder = makeReminder({
      reminder_type: "house",
      reminder_end_date: "2025-09-08",
      is_completed: false,
    });

    render(<ReminderForm reminder={reminder} />);

    expect(screen.getByRole("heading", { name: "Edit reminder" })).toBeInTheDocument();
    expect(
      screen.getByText(/Update the message or reschedule/),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "House" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByRole("button", { name: "Save changes" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mark complete" })).toBeInTheDocument();
  });

  it("shows Reopen for an already-completed reminder", () => {
    const reminder = makeReminder({ is_completed: true });
    render(<ReminderForm reminder={reminder} />);

    expect(screen.getByRole("button", { name: "Reopen" })).toBeInTheDocument();
  });
});
