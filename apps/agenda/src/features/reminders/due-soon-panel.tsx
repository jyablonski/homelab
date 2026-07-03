import { ReminderList } from "@/features/reminders/reminder-list";
import type { ReminderCardData } from "@/features/reminders/types";

export function DueSoonPanel({ reminders }: { reminders: ReminderCardData[] }) {
  if (reminders.length === 0) {
    return null;
  }

  return (
    <div className="rounded-lg border border-warning-border bg-warning-background/40 p-2">
      <div className="flex items-center justify-between px-2 pb-1 pt-1">
        <h3 className="text-xs font-semibold tracking-wide text-warning uppercase">
          Due soon
        </h3>
        <span className="text-xs text-muted">next 7 days</span>
      </div>
      <ReminderList reminders={reminders} emptyTitle="" variant="due-soon" />
    </div>
  );
}
