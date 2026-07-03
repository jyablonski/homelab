import { describe, expect, it } from "vitest";

import { GET } from "./route";

describe("GET /healthz", () => {
  it("returns an ok status payload", async () => {
    const response = GET();
    const body = await response.json();

    expect(body).toEqual({ status: "ok" });
  });
});
