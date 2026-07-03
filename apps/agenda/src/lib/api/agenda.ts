import "server-only";

import { apiFetch } from "@/lib/api/client";
import { config } from "@/lib/config";
import { type AgendaTodayResponse, agendaTodayResponseSchema } from "@/lib/schemas";

export async function getTodayAgenda(
  options: { hours?: number; dueSoonDays?: number } = {},
): Promise<AgendaTodayResponse> {
  const payload = await apiFetch<unknown>("/agenda/today", {
    query: {
      hours: options.hours ?? config.eventWindowHours,
      due_soon_days: options.dueSoonDays ?? config.dueSoonDays,
    },
    cache: "no-store",
  });
  return agendaTodayResponseSchema.parse(payload);
}
