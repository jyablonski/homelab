import { cn } from "@/lib/cn";
import { formatRelativeTime, formatTime } from "@/lib/dates";
import type { AgendaEvent, AgendaFreshness } from "@/lib/schemas";

import {
  findFreshnessForSource,
  freshnessTone,
  sourceBadgeClass,
} from "@/features/events/types";
import { StatusPill } from "@/components/status-pill";

const freshnessLabels: Record<AgendaFreshness["status"], string> = {
  fresh: "fresh",
  stale: "stale",
  fetch_failed: "failed",
  placeholder: "placeholder",
};

type EventCardProps = {
  event: AgendaEvent;
  freshness: AgendaFreshness[];
};

export function EventCard({ event, freshness }: EventCardProps) {
  const eventFreshness = findFreshnessForSource(freshness, event.source);
  const isDegraded =
    eventFreshness?.status === "stale" || eventFreshness?.status === "fetch_failed";
  const venue = typeof event.metadata.venue === "string" ? event.metadata.venue : null;

  return (
    <div className="rounded-lg border border-border bg-surface p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "rounded px-1.5 py-0.5 text-[10px] font-semibold tracking-wide uppercase",
              sourceBadgeClass(event.source),
            )}
          >
            {event.league || event.source}
          </span>
          <span className="text-xs text-muted">{formatTime(event.start_at)}</span>
        </div>
        {isDegraded && eventFreshness ? (
          <StatusPill
            label={freshnessLabels[eventFreshness.status]}
            tone={freshnessTone(eventFreshness.status)}
          />
        ) : null}
      </div>

      <p className="mt-2 text-sm font-medium text-foreground">{event.title}</p>
      <p className="mt-0.5 text-xs text-muted">
        {venue ?? event.category}
        {isDegraded && eventFreshness?.last_success_at
          ? ` · last ok ${formatRelativeTime(eventFreshness.last_success_at)}`
          : null}
      </p>
    </div>
  );
}
