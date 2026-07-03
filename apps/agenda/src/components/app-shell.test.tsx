import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const usePathnameMock = vi.hoisted(() => vi.fn(() => "/"));
vi.mock("next/navigation", () => ({ usePathname: usePathnameMock }));

const getReminderCountsMock = vi.hoisted(() => vi.fn());
vi.mock("@/features/reminders/reminder-counts", () => ({
  getReminderCounts: getReminderCountsMock,
}));

import { AppShell } from "./app-shell";

describe("AppShell", () => {
  it("renders nav links and counts when the API call succeeds", async () => {
    getReminderCountsMock.mockResolvedValue({ upcoming: 8, completed: 24 });

    const ui = await AppShell({ children: <p>Page content</p> });
    render(ui);

    expect(screen.getByText("Agenda")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Today/ })).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("24")).toBeInTheDocument();
    expect(screen.getByText("Page content")).toBeInTheDocument();
  });

  it("still renders when the reminder counts API call fails", async () => {
    getReminderCountsMock.mockResolvedValue(null);

    const ui = await AppShell({ children: <p>Page content</p> });
    render(ui);

    expect(screen.getByRole("link", { name: /Upcoming/ })).toBeInTheDocument();
    expect(screen.getByText("Page content")).toBeInTheDocument();
  });
});
