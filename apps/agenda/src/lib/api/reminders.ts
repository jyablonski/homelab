import "server-only";

import { apiFetch } from "@/lib/api/client";
import { config } from "@/lib/config";
import { dayKey } from "@/lib/dates";
import {
  type Reminder,
  type ReminderCreateInput,
  type ReminderUpdateInput,
  reminderListSchema,
  reminderSchema,
} from "@/lib/schemas";

export async function listReminders(
  options: { includeCompleted?: boolean } = {},
): Promise<Reminder[]> {
  const payload = await apiFetch<unknown>("/reminders", {
    query: {
      include_completed: options.includeCompleted ?? true,
      limit: 500,
    },
    cache: "no-store",
  });
  return reminderListSchema.parse(payload);
}

export async function getReminder(id: number): Promise<Reminder> {
  const payload = await apiFetch<unknown>(`/reminders/${id}`, {
    cache: "no-store",
  });
  return reminderSchema.parse(payload);
}

export async function createReminder(
  input: ReminderCreateInput,
): Promise<Reminder> {
  const payload = await apiFetch<unknown>("/reminders", {
    method: "POST",
    body: input,
  });
  return reminderSchema.parse(payload);
}

export async function updateReminder(
  id: number,
  input: ReminderUpdateInput,
): Promise<Reminder> {
  const payload = await apiFetch<unknown>(`/reminders/${id}`, {
    method: "PATCH",
    body: input,
  });
  return reminderSchema.parse(payload);
}

export function completeReminder(id: number): Promise<Reminder> {
  return updateReminder(id, {
    is_completed: true,
    completed_at: new Date().toISOString(),
  });
}

export function reopenReminder(id: number): Promise<Reminder> {
  return updateReminder(id, { is_completed: false, completed_at: null });
}

export type ReminderGroups = {
  active: Reminder[];
  dueSoon: Reminder[];
  upcoming: Reminder[];
  completed: Reminder[];
};

/**
 * Mirrors the visibility rules in `notes/ideas/frontend-app.md`: active/due-soon/
 * completed match the FastAPI `/agenda/today` grouping; upcoming covers everything
 * further out, since there is no dedicated `/reminders?status=` endpoint yet.
 */
export function groupReminders(
  reminders: Reminder[],
  dueSoonDays = config.dueSoonDays,
  now = new Date(),
): ReminderGroups {
  const today = dayKey(now);
  const dueSoonEnd = dayKey(
    new Date(now.getTime() + dueSoonDays * 24 * 60 * 60 * 1000),
  );

  const groups: ReminderGroups = {
    active: [],
    dueSoon: [],
    upcoming: [],
    completed: [],
  };

  for (const reminder of reminders) {
    if (reminder.is_completed) {
      groups.completed.push(reminder);
      continue;
    }

    if (reminder.reminder_start_date <= today) {
      groups.active.push(reminder);
    } else if (reminder.reminder_start_date <= dueSoonEnd) {
      groups.dueSoon.push(reminder);
    } else {
      groups.upcoming.push(reminder);
    }
  }

  return groups;
}
