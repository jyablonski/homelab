import pino from "pino";

// Field names follow the shared log schema in notes/services/monitoring.md so
// `| json` queries look the same for every app. `service` matches the Loki
// `app` label and the Helm release name.
export const logger = pino({
  base: { service: "agenda" },
  level: process.env.AGENDA_LOG_LEVEL ?? "info",
  timestamp: pino.stdTimeFunctions.isoTime,
  formatters: {
    level: (label) => ({ level: label }),
  },
});

export function errorFields(error: unknown): { error: string; exception?: string } {
  if (error instanceof Error) {
    return { error: `${error.name}: ${error.message}`, exception: error.stack };
  }
  return { error: String(error) };
}
