import { CalendarDays } from "lucide-react";

import { ColumnHeader } from "@/components/column-header";
import { EmptyState } from "@/components/empty-state";
import type { AgendaEvent, AgendaFreshness } from "@/lib/schemas";

import { EventCard } from "@/features/events/event-card";

function freshnessSummary(freshness: AgendaFreshness[]): string | null {
  const fresh = freshness.filter((entry) => entry.status === "fresh").length;
  const failed = freshness.filter((entry) => entry.status === "fetch_failed").length;
  const stale = freshness.filter((entry) => entry.status === "stale").length;

  const parts = [
    fresh > 0 ? `${fresh} fresh` : null,
    stale > 0 ? `${stale} stale` : null,
    failed > 0 ? `${failed} failed` : null,
  ].filter(Boolean);

  return parts.length > 0 ? parts.join(" · ") : null;
}

type EventsColumnProps = {
  events: AgendaEvent[];
  freshness: AgendaFreshness[];
};

export function EventsColumn({ events, freshness }: EventsColumnProps) {
  return (
    <div className="flex flex-col gap-4">
      <ColumnHeader
        label="Upcoming events"
        dotClassName="bg-accent"
        trailing={freshnessSummary(freshness)}
      />

      <div>
        <h3 className="mb-2 px-2 text-xs font-semibold tracking-wide text-muted uppercase">
          Next 24 hours
        </h3>
        {events.length === 0 ? (
          <EmptyState icon={CalendarDays} title="No events in the next 24 hours" />
        ) : (
          <div className="flex flex-col gap-3">
            {events.map((event) => (
              <EventCard key={event.id} event={event} freshness={freshness} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
