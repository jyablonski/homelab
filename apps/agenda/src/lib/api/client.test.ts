import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/config", () => ({
  config: {
    apiBaseUrl: "http://test.local:8000",
    apiKey: "secret-key",
    timezone: "America/Los_Angeles",
    dueSoonDays: 7,
    eventWindowHours: 24,
  },
}));

import { apiFetch, ApiError } from "./client";

describe("apiFetch", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    fetchMock.mockReset();
    vi.unstubAllGlobals();
  });

  it("builds the /v1-prefixed URL with query params and the API key header", async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );

    const result = await apiFetch<{ ok: boolean }>("/agenda/today", {
      query: { hours: 24, due_soon_days: 7, skip: undefined },
    });

    expect(result).toEqual({ ok: true });
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(
      "http://test.local:8000/v1/agenda/today?hours=24&due_soon_days=7",
    );
    expect(init.headers["X-Homelab-Api-Key"]).toBe("secret-key");
  });

  it("sends a JSON body for mutating requests", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ id: 1 }), { status: 201 }));

    await apiFetch("/reminders", {
      method: "POST",
      body: { reminder_type: "car" },
    });

    const [, init] = fetchMock.mock.calls[0];
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ reminder_type: "car" }));
  });

  it("returns undefined for a 204 response", async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));

    const result = await apiFetch("/reminders/1");

    expect(result).toBeUndefined();
  });

  it("throws an ApiError with the response body on a non-ok response", async () => {
    fetchMock.mockResolvedValue(new Response("reminder not found", { status: 404 }));

    await expect(apiFetch("/reminders/999")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      message: "reminder not found",
    });
  });

  it("throws a status-0 ApiError when the network request fails", async () => {
    fetchMock.mockRejectedValue(new Error("network down"));

    await expect(apiFetch("/agenda/today")).rejects.toMatchObject({
      name: "ApiError",
      status: 0,
    });
  });
});

describe("ApiError", () => {
  it("carries the status and message", () => {
    const error = new ApiError("boom", 500);
    expect(error.message).toBe("boom");
    expect(error.status).toBe(500);
    expect(error.name).toBe("ApiError");
  });
});
