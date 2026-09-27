import { randomUUID } from "node:crypto";
import type { IncomingMessage, ServerResponse } from "node:http";

import { Counter, Histogram, Registry, collectDefaultMetrics } from "prom-client";

// Relative `.ts` import: server.ts loads this file through Node's native type
// stripping, which does not resolve the `@/` alias or extensionless paths.
import { logger } from "./logger.ts";

const REQUEST_ID_HEADER = "x-request-id";

export const registry = new Registry();
collectDefaultMetrics({ register: registry });

// Shared HTTP metric names across every homelab app; Prometheus adds the `app`
// label from the ServiceMonitor, so names carry no service prefix.
const httpRequests = new Counter({
  name: "http_server_requests_total",
  help: "Total HTTP requests handled.",
  labelNames: ["method", "route", "status"] as const,
  registers: [registry],
});

const httpRequestDuration = new Histogram({
  name: "http_server_request_duration_seconds",
  help: "HTTP request duration in seconds.",
  labelNames: ["method", "route"] as const,
  registers: [registry],
});

const ID_SEGMENT = /^(\d+|[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/i;

// The custom server runs outside Next's router, so it cannot see route
// templates. Replace ID-like path segments with `[id]` (Next's own dynamic
// segment syntax) and collapse 404s and build assets to keep metric
// cardinality bounded.
export function routeTemplate(pathname: string, status: number): string {
  if (status === 404) {
    return "unmatched";
  }
  if (pathname.startsWith("/_next/")) {
    return "/_next/*";
  }
  return pathname
    .split("/")
    .map((segment) => (ID_SEGMENT.test(segment) ? "[id]" : segment))
    .join("/");
}

function clientIp(req: IncomingMessage): string | undefined {
  const forwardedFor = req.headers["x-forwarded-for"];
  const first = Array.isArray(forwardedFor) ? forwardedFor[0] : forwardedFor;
  if (first) {
    return first.split(",")[0].trim();
  }
  return req.socket.remoteAddress;
}

// Records one access log line and the shared HTTP metrics once the response
// has been sent.
export function observeRequest(req: IncomingMessage, res: ServerResponse): void {
  const start = process.hrtime.bigint();
  const incomingId = req.headers[REQUEST_ID_HEADER];
  const requestId = (Array.isArray(incomingId) ? incomingId[0] : incomingId) || randomUUID();
  res.setHeader("X-Request-ID", requestId);

  res.once("finish", () => {
    const durationSeconds = Number(process.hrtime.bigint() - start) / 1e9;
    const method = req.method ?? "GET";
    const path = new URL(req.url ?? "/", "http://localhost").pathname;
    const status = res.statusCode;
    const route = routeTemplate(path, status);

    httpRequests.inc({ method, route, status: String(status) });
    httpRequestDuration.observe({ method, route }, durationSeconds);

    const fields = {
      request_id: requestId,
      method,
      route,
      path,
      status,
      duration_ms: Math.round(durationSeconds * 100_000) / 100,
      client_ip: clientIp(req),
    };
    if (status >= 500) {
      logger.error(fields, "request completed");
    } else {
      logger.info(fields, "request completed");
    }
  });
}

export async function writeMetrics(res: ServerResponse): Promise<void> {
  res.setHeader("Content-Type", registry.contentType);
  res.end(await registry.metrics());
}
