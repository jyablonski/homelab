import { MoreHorizontal } from "lucide-react";
import Link from "next/link";

import { cn } from "@/lib/cn";
import { formatDate, formatShortDate } from "@/lib/dates";

import {
  completeReminderAction,
  reopenReminderAction,
} from "@/features/reminders/reminder-actions";
import {
  reminderCategoryDotClass,
  reminderCategoryLabel,
  type ReminderCardData,
} from "@/features/reminders/types";
import { StatusToggleButton } from "@/features/reminders/status-toggle-button";

type ReminderCardProps = {
  reminder: ReminderCardData;
  /** "due-soon" shows a right-aligned date instead of the category/edit meta row. */
  variant?: "default" | "due-soon";
};

export function ReminderCard({ reminder, variant = "default" }: ReminderCardProps) {
  const toggleAction = reminder.is_completed
    ? reopenReminderAction.bind(null, reminder.id)
    : completeReminderAction.bind(null, reminder.id);

  return (
    <div className="group flex items-center gap-3 rounded-md px-2 py-2 transition-colors hover:bg-muted-background">
      <form action={toggleAction}>
        <StatusToggleButton isCompleted={reminder.is_completed} />
      </form>

      <span
        className={cn(
          "h-2 w-2 shrink-0 rounded-full",
          reminderCategoryDotClass(reminder.reminder_type),
        )}
      />

      <div className="min-w-0 flex-1">
        <p
          className={cn(
            "truncate text-sm text-foreground",
            reminder.is_completed && "text-muted line-through",
          )}
        >
          {reminder.reminder_message}
        </p>
        {variant === "default" ? (
          <p className="truncate text-xs text-muted">
            {reminderCategoryLabel(reminder.reminder_type)} · since{" "}
            {formatDate(reminder.reminder_start_date)}
            {reminder.reminder_end_date
              ? ` · ends ${formatDate(reminder.reminder_end_date)}`
              : null}
          </p>
        ) : null}
      </div>

      {variant === "due-soon" ? (
        <span className="shrink-0 text-xs text-muted">
          {formatShortDate(reminder.reminder_start_date)}
        </span>
      ) : (
        <Link
          href={`/reminders/${reminder.id}/edit`}
          aria-label="Edit reminder"
          title="Edit reminder"
          className="shrink-0 rounded-md p-1 text-muted opacity-0 transition-opacity hover:text-foreground group-hover:opacity-100"
        >
          <MoreHorizontal className="h-4 w-4" />
        </Link>
      )}
    </div>
  );
}
