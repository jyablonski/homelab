// @vitest-environment node
import { EventEmitter } from "node:events";
import type { IncomingMessage, ServerResponse } from "node:http";

import { afterEach, describe, expect, it, vi } from "vitest";

import { logger } from "./logger";
import { observeRequest, registry, routeTemplate, writeMetrics } from "./http-observability";

function fakeExchange(url: string, headers: Record<string, string> = {}) {
  const req = {
    url,
    method: "GET",
    headers,
    socket: { remoteAddress: "10.0.0.1" },
  } as unknown as IncomingMessage;
  const res = Object.assign(new EventEmitter(), {
    statusCode: 200,
    headers: {} as Record<string, string>,
    body: "",
    setHeader(name: string, value: string) {
      this.headers[name.toLowerCase()] = value;
    },
    end(body: string) {
      this.body = body;
    },
  });
  return { req, res: res as unknown as ServerResponse & typeof res };
}

describe("routeTemplate", () => {
  it.each([
    ["/", 200, "/"],
    ["/upcoming", 200, "/upcoming"],
    ["/reminders/42/edit", 200, "/reminders/[id]/edit"],
    ["/reminders/0b7c8d52-3f1e-4a4f-9a51-5c2f0a0e9f11/edit", 200, "/reminders/[id]/edit"],
    ["/_next/static/chunks/app.js", 200, "/_next/*"],
    ["/wp-admin", 404, "unmatched"],
  ])("maps %s (%i) to %s", (path, status, expected) => {
    expect(routeTemplate(path, status)).toBe(expected);
  });
});

describe("observeRequest", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("logs one access line and counts the request once the response finishes", async () => {
    const info = vi.spyOn(logger, "info").mockImplementation(() => undefined);
    const { req, res } = fakeExchange("/reminders/7/edit?tab=1", { "x-request-id": "test-request" });

    observeRequest(req, res);
    res.emit("finish");

    expect(res.headers["x-request-id"]).toBe("test-request");
    expect(info).toHaveBeenCalledWith(
      expect.objectContaining({
        request_id: "test-request",
        method: "GET",
        route: "/reminders/[id]/edit",
        path: "/reminders/7/edit",
        status: 200,
        client_ip: "10.0.0.1",
      }),
      "request completed",
    );
    expect(await registry.metrics()).toContain(
      'http_server_requests_total{method="GET",route="/reminders/[id]/edit",status="200"} 1',
    );
  });

  it("logs 5xx responses at error level", () => {
    const error = vi.spyOn(logger, "error").mockImplementation(() => undefined);
    const { req, res } = fakeExchange("/");
    res.statusCode = 503;

    observeRequest(req, res);
    res.emit("finish");

    expect(error).toHaveBeenCalledWith(expect.objectContaining({ status: 503 }), "request completed");
  });
});

describe("writeMetrics", () => {
  it("serves the registry in Prometheus text format", async () => {
    const { res } = fakeExchange("/metrics");

    await writeMetrics(res);

    expect(res.headers["content-type"]).toContain("text/plain");
    expect(res.body).toContain("http_server_request_duration_seconds");
  });
});
