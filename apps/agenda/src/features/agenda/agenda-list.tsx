import type { AgendaTodayResponse } from "@/lib/schemas";

import { getPersonalCalendarEvents } from "@/features/calendar/data";
import { CalendarColumn } from "@/features/calendar/calendar-column";
import { EventsColumn } from "@/features/events/events-column";
import { RemindersColumn } from "@/features/agenda/reminders-column";
import { toReminderCardData } from "@/features/agenda/types";

export function AgendaList({ agenda }: { agenda: AgendaTodayResponse }) {
  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
      <CalendarColumn events={getPersonalCalendarEvents()} />

      <RemindersColumn
        active={agenda.reminders.active.map(toReminderCardData)}
        dueSoon={agenda.reminders.due_soon.map(toReminderCardData)}
      />

      <EventsColumn events={agenda.events} freshness={agenda.freshness} />
    </div>
  );
}
