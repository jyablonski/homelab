import "server-only";

import { groupReminders, listReminders } from "@/lib/api/reminders";

export type ReminderCounts = {
  upcoming: number;
  completed: number;
};

/** Powers the sidebar nav badges. Returns null on API failure so the shell can render without them. */
export async function getReminderCounts(): Promise<ReminderCounts | null> {
  try {
    const reminders = await listReminders({ includeCompleted: true });
    const groups = groupReminders(reminders);
    return {
      upcoming: groups.dueSoon.length + groups.upcoming.length,
      completed: groups.completed.length,
    };
  } catch {
    return null;
  }
}
