import { z } from "zod";

export const reminderCategories = [
  "car",
  "house",
  "health",
  "bill",
  "homelab",
  "general",
] as const;

export type ReminderCategory = (typeof reminderCategories)[number];

export const reminderSchema = z.object({
  id: z.number(),
  reminder_type: z.string(),
  reminder_message: z.string(),
  reminder_start_date: z.string(),
  reminder_end_date: z.string().nullable(),
  is_completed: z.boolean(),
  completed_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type Reminder = z.infer<typeof reminderSchema>;

export const reminderListSchema = z.array(reminderSchema);

export const reminderCreateSchema = z.object({
  reminder_type: z.string().min(1),
  reminder_message: z.string().min(1),
  reminder_start_date: z.string().min(1),
  reminder_end_date: z.string().min(1).nullable().optional(),
});

export type ReminderCreateInput = z.infer<typeof reminderCreateSchema>;

export const reminderUpdateSchema = z.object({
  reminder_type: z.string().min(1).optional(),
  reminder_message: z.string().min(1).optional(),
  reminder_start_date: z.string().min(1).optional(),
  reminder_end_date: z.string().min(1).nullable().optional(),
  is_completed: z.boolean().optional(),
  completed_at: z.string().nullable().optional(),
});

export type ReminderUpdateInput = z.infer<typeof reminderUpdateSchema>;

const agendaWindowSchema = z.object({
  start: z.string(),
  end: z.string(),
  due_soon_days: z.number(),
});

const agendaReminderSchema = z.object({
  id: z.number(),
  type: z.string(),
  message: z.string(),
  start_date: z.string(),
  end_date: z.string().nullable(),
  is_completed: z.boolean(),
});

export type AgendaReminder = z.infer<typeof agendaReminderSchema>;

const agendaReminderGroupsSchema = z.object({
  active: z.array(agendaReminderSchema),
  due_soon: z.array(agendaReminderSchema),
  completed: z.array(agendaReminderSchema),
});

const agendaEventSchema = z.object({
  id: z.string(),
  source: z.string(),
  category: z.string(),
  league: z.string(),
  title: z.string(),
  start_at: z.string(),
  status: z.string(),
  metadata: z.record(z.string(), z.unknown()).default({}),
});

export type AgendaEvent = z.infer<typeof agendaEventSchema>;

const agendaFreshnessSchema = z.object({
  source: z.string(),
  last_success_at: z.string().nullable(),
  status: z.enum(["fresh", "stale", "fetch_failed", "placeholder"]),
  message: z.string().nullable().optional(),
});

export type AgendaFreshness = z.infer<typeof agendaFreshnessSchema>;

export const eventsUpcomingResponseSchema = z.object({
  generated_at: z.string(),
  timezone: z.string(),
  window: agendaWindowSchema,
  events: z.array(agendaEventSchema),
  freshness: z.array(agendaFreshnessSchema),
});

export type EventsUpcomingResponse = z.infer<typeof eventsUpcomingResponseSchema>;

export const agendaTodayResponseSchema = eventsUpcomingResponseSchema.extend({
  reminders: agendaReminderGroupsSchema,
});

export type AgendaTodayResponse = z.infer<typeof agendaTodayResponseSchema>;
