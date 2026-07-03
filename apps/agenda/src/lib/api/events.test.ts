import { describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("./client", () => ({ apiFetch: apiFetchMock }));

import { makeAgendaToday } from "@/test/factories";

import { getUpcomingEvents } from "./events";

describe("getUpcomingEvents", () => {
  it("requests /events/upcoming with the default event window", async () => {
    apiFetchMock.mockResolvedValue(makeAgendaToday());

    const result = await getUpcomingEvents();

    expect(apiFetchMock).toHaveBeenCalledWith("/events/upcoming", {
      query: { hours: 24 },
      cache: "no-store",
    });
    expect(result.window.due_soon_days).toBe(7);
  });

  it("passes through a custom hours window", async () => {
    apiFetchMock.mockResolvedValue(makeAgendaToday());

    await getUpcomingEvents(6);

    expect(apiFetchMock).toHaveBeenCalledWith("/events/upcoming", {
      query: { hours: 6 },
      cache: "no-store",
    });
  });
});
