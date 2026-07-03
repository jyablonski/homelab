import { ColumnHeader } from "@/components/column-header";
import { EmptyState } from "@/components/empty-state";
import { CalendarClock } from "lucide-react";

import { formatClockTime, type PersonalCalendarEvent } from "@/features/calendar/types";

export function CalendarColumn({ events }: { events: PersonalCalendarEvent[] }) {
  return (
    <div className="flex flex-col gap-4">
      <ColumnHeader label="Personal calendar" dotClassName="bg-emerald-400" />

      {events.length === 0 ? (
        <EmptyState icon={CalendarClock} title="Nothing on your calendar today" />
      ) : (
        <div className="flex flex-col gap-0.5">
          {events.map((event) => (
            <div
              key={event.id}
              className="flex items-center gap-3 rounded-md px-2 py-2 transition-colors hover:bg-muted-background"
            >
              <span className="w-32 shrink-0 text-xs tabular-nums text-muted">
                {formatClockTime(event.startTime)}
                {event.endTime ? ` – ${formatClockTime(event.endTime)}` : null}
              </span>
              <span className="truncate text-sm text-foreground">{event.title}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
