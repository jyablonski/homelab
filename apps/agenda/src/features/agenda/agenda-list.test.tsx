import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  makeAgendaEvent,
  makeAgendaFreshness,
  makeAgendaReminder,
  makeAgendaToday,
} from "@/test/factories";

import { AgendaList } from "./agenda-list";

describe("AgendaList", () => {
  it("renders active reminders, events, and the personal calendar", () => {
    const agenda = makeAgendaToday({
      reminders: {
        active: [makeAgendaReminder()],
        due_soon: [],
        completed: [],
      },
      events: [makeAgendaEvent()],
    });

    render(<AgendaList agenda={agenda} />);

    expect(screen.getByText("Get oil changed soon")).toBeInTheDocument();
    expect(
      screen.getByText("Los Angeles Lakers at Golden State Warriors"),
    ).toBeInTheDocument();
    // Dummy personal-calendar data always renders since there is no backend for it yet.
    expect(screen.getByText("Standup")).toBeInTheDocument();
  });

  it("shows empty states and hides the due-soon panel when there is nothing due soon", () => {
    render(<AgendaList agenda={makeAgendaToday()} />);

    expect(screen.getByText("Nothing active today")).toBeInTheDocument();
    expect(screen.getByText("No events in the next 24 hours")).toBeInTheDocument();
    expect(screen.queryByText("Due soon")).not.toBeInTheDocument();
  });

  it("shows a due-soon panel when there are due-soon reminders", () => {
    const agenda = makeAgendaToday({
      reminders: {
        active: [],
        due_soon: [makeAgendaReminder({ message: "Pay electric bill" })],
        completed: [],
      },
    });

    render(<AgendaList agenda={agenda} />);

    expect(screen.getByText("Due soon")).toBeInTheDocument();
    expect(screen.getByText("Pay electric bill")).toBeInTheDocument();
  });

  it("surfaces per-event freshness pills for stale or failed sources only", () => {
    const agenda = makeAgendaToday({
      events: [
        makeAgendaEvent({ id: "nba:1", source: "nba", title: "Lakers game" }),
        makeAgendaEvent({ id: "ufc:1", source: "ufc", title: "UFC 322" }),
        makeAgendaEvent({ id: "cs2:1", source: "cs2", title: "IEM Cologne" }),
      ],
      freshness: [
        makeAgendaFreshness({ source: "nba", status: "stale" }),
        makeAgendaFreshness({ source: "ufc", status: "fetch_failed" }),
        makeAgendaFreshness({ source: "cs2", status: "fresh" }),
      ],
    });

    render(<AgendaList agenda={agenda} />);

    expect(screen.getByText("stale")).toBeInTheDocument();
    expect(screen.getByText("failed")).toBeInTheDocument();
    expect(screen.getAllByText(/last ok/)).toHaveLength(2);
  });
});
