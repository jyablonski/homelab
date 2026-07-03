import "server-only";

import { apiFetch } from "@/lib/api/client";
import { config } from "@/lib/config";
import {
  type EventsUpcomingResponse,
  eventsUpcomingResponseSchema,
} from "@/lib/schemas";

export async function getUpcomingEvents(
  hours: number = config.eventWindowHours,
): Promise<EventsUpcomingResponse> {
  const payload = await apiFetch<unknown>("/events/upcoming", {
    query: { hours },
    cache: "no-store",
  });
  return eventsUpcomingResponseSchema.parse(payload);
}
