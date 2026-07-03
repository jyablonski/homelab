import "server-only";

function requireEnv(name: string, fallback?: string): string {
  const value = process.env[name] ?? fallback;
  if (value === undefined) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

export const config = {
  apiBaseUrl: requireEnv(
    "AGENDA_API_BASE_URL",
    "http://api.apps.svc.cluster.local:8000",
  ).replace(/\/$/, ""),
  apiKey: process.env.AGENDA_API_KEY ?? "",
  timezone: "America/Los_Angeles",
  dueSoonDays: 7,
  eventWindowHours: 24,
};
