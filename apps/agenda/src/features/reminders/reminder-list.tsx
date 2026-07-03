import { CalendarX2 } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { formatDate } from "@/lib/dates";

import { ReminderCard } from "@/features/reminders/reminder-card";
import type { ReminderCardData } from "@/features/reminders/types";

type ReminderListProps = {
  reminders: ReminderCardData[];
  emptyTitle: string;
  emptyDescription?: string;
  groupByDate?: boolean;
  variant?: "default" | "due-soon";
};

function groupByStartDate(
  reminders: ReminderCardData[],
): [string, ReminderCardData[]][] {
  const groups = new Map<string, ReminderCardData[]>();
  for (const reminder of reminders) {
    const key = reminder.reminder_start_date;
    const existing = groups.get(key);
    if (existing) {
      existing.push(reminder);
    } else {
      groups.set(key, [reminder]);
    }
  }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
}

export function ReminderList({
  reminders,
  emptyTitle,
  emptyDescription,
  groupByDate = false,
  variant = "default",
}: ReminderListProps) {
  if (reminders.length === 0) {
    return (
      <EmptyState
        icon={CalendarX2}
        title={emptyTitle}
        description={emptyDescription}
      />
    );
  }

  if (!groupByDate) {
    return (
      <div className="flex flex-col gap-0.5">
        {reminders.map((reminder) => (
          <ReminderCard key={reminder.id} reminder={reminder} variant={variant} />
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {groupByStartDate(reminders).map(([date, group]) => (
        <div key={date} className="flex flex-col gap-0.5">
          <h3 className="px-2 pb-1 text-xs font-medium uppercase tracking-wide text-muted">
            {formatDate(date)}
          </h3>
          {group.map((reminder) => (
            <ReminderCard key={reminder.id} reminder={reminder} variant={variant} />
          ))}
        </div>
      ))}
    </div>
  );
}
