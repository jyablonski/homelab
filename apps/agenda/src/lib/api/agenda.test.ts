import { describe, expect, it, vi } from "vitest";

const apiFetchMock = vi.hoisted(() => vi.fn());
vi.mock("./client", () => ({ apiFetch: apiFetchMock }));

import { makeAgendaToday } from "@/test/factories";

import { getTodayAgenda } from "./agenda";

describe("getTodayAgenda", () => {
  it("requests /agenda/today with default hours and due-soon window", async () => {
    const payload = makeAgendaToday();
    apiFetchMock.mockResolvedValue(payload);

    const result = await getTodayAgenda();

    expect(apiFetchMock).toHaveBeenCalledWith("/agenda/today", {
      query: { hours: 24, due_soon_days: 7 },
      cache: "no-store",
    });
    expect(result.timezone).toBe("America/Los_Angeles");
  });

  it("passes through custom hours and due-soon days", async () => {
    apiFetchMock.mockResolvedValue(makeAgendaToday());

    await getTodayAgenda({ hours: 6, dueSoonDays: 3 });

    expect(apiFetchMock).toHaveBeenCalledWith("/agenda/today", {
      query: { hours: 6, due_soon_days: 3 },
      cache: "no-store",
    });
  });

  it("throws when the response does not match the expected schema", async () => {
    apiFetchMock.mockResolvedValue({ nonsense: true });

    await expect(getTodayAgenda()).rejects.toThrow();
  });
});
