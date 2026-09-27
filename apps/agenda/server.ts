import { createServer } from "node:http";

import next from "next";

import { observeRequest, writeMetrics } from "./src/server/http-observability.ts";
import { errorFields, logger } from "./src/server/logger.ts";

// Custom server so every request gets a structured access log line with the
// final status and duration, plus a /metrics endpoint; neither is possible
// from inside Next's router. `npm run dev` and `npm start` both use it.
const dev = process.env.NODE_ENV !== "production";
const hostname = "0.0.0.0";
const port = Number(process.env.PORT ?? 3000);

const app = next({ dev, hostname, port });
const handle = app.getRequestHandler();

await app.prepare();

const server = createServer((req, res) => {
  observeRequest(req, res);

  if (req.url === "/metrics") {
    void writeMetrics(res);
    return;
  }

  handle(req, res).catch((error: unknown) => {
    logger.error({ ...errorFields(error), path: req.url }, "unhandled request error");
    res.statusCode = 500;
    res.end("Internal Server Error");
  });
});

// Dev-mode HMR runs over websocket upgrades, which bypass the request handler.
const upgrade = app.getUpgradeHandler();
server.on("upgrade", (req, socket, head) => {
  void upgrade(req, socket, head);
});

server.listen(port, hostname, () => {
  logger.info({ port, dev }, "server listening");
});
