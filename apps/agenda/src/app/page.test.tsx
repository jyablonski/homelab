import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

const getTodayAgendaMock = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api/agenda", () => ({ getTodayAgenda: getTodayAgendaMock }));

import { makeAgendaReminder, makeAgendaToday } from "@/test/factories";

import TodayPage from "./page";

describe("TodayPage", () => {
  it("renders the weekday header stats and agenda content", async () => {
    getTodayAgendaMock.mockResolvedValue(
      makeAgendaToday({
        reminders: {
          active: [makeAgendaReminder()],
          due_soon: [],
          completed: [],
        },
      }),
    );

    const ui = await TodayPage();
    render(ui);

    expect(screen.getByText(/1 active · 0 due soon · 0 events/)).toBeInTheDocument();
    expect(screen.getByText("Get oil changed soon")).toBeInTheDocument();
  });
});
