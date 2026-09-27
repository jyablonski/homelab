import type { Instrumentation } from "next";

// Next calls this for every server-side render, route handler, and server
// action error, so failures land in Loki as one JSON line with the route
// template instead of Next's multi-line console output.
export const onRequestError: Instrumentation.onRequestError = async (error, request, context) => {
  // pino needs Node APIs; this app has no edge routes, but guard anyway.
  if (process.env.NEXT_RUNTIME !== "nodejs") {
    return;
  }
  const { errorFields, logger } = await import("@/server/logger");
  logger.error(
    {
      ...errorFields(error),
      method: request.method,
      path: request.path,
      route: context.routePath,
      route_type: context.routeType,
    },
    "request error",
  );
};
