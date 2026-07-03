import type { ReminderCardData } from "@/features/reminders/types";
import type { AgendaReminder } from "@/lib/schemas";

export function toReminderCardData(item: AgendaReminder): ReminderCardData {
  return {
    id: item.id,
    reminder_type: item.type,
    reminder_message: item.message,
    reminder_start_date: item.start_date,
    reminder_end_date: item.end_date,
    is_completed: item.is_completed,
  };
}
